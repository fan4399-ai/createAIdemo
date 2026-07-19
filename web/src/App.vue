<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import {
  getProfile,
  startGeneration,
  cancelGeneration,
  connectStream,
  type Profile,
  type StreamEvent,
} from './api'
import ProgressPanel from './components/ProgressPanel.vue'
import ReportViewer from './components/ReportViewer.vue'
import ExportDrawer from './components/ExportDrawer.vue'

const profile = ref<Profile | null>(null)
const generating = ref(false)
const reportMarkdown = ref('')
const errorMsg = ref('')
const sessionId = ref('')
const topic = ref('')
const connected = ref(false)

const logs = ref<{ id: number; text: string; stage?: string }[]>([])
const stages = reactive([
  { key: 'research', label: '研究', status: 'pending' },
  { key: 'writing', label: '撰写', status: 'pending' },
  { key: 'editing', label: '编辑', status: 'pending' },
])

let es: EventSource | null = null
let logId = 0
let reconnectAttempts = 0
const MAX_RECONNECT = 5

onMounted(async () => {
  try {
    profile.value = await getProfile()
    connected.value = true
  } catch {
    connected.value = false
  }
})

function setStage(key: string, status: 'running' | 'done' | 'pending') {
  const s = stages.find((x) => x.key === key)
  if (s) s.status = status
}

function onEvent(e: StreamEvent) {
  if (e.type === 'connected') {
    connected.value = true
    reconnectAttempts = 0
    return
  }
  if (e.type === 'stage' && e.stage) {
    setStage(e.stage, e.status === 'done' ? 'done' : 'running')
  } else if (e.type === 'log') {
    logs.value.push({ id: ++logId, text: e.message || '', stage: e.stage })
    // 限制日志长度，避免内存无限增长
    if (logs.value.length > 200) logs.value.shift()
  } else if (e.type === 'done') {
    reportMarkdown.value = e.markdown || ''
    finish()
  } else if (e.type === 'cancelled') {
    errorMsg.value = e.message || '已取消生成'
    finish()
  } else if (e.type === 'error') {
    errorMsg.value = e.message || '生成出错'
    finish()
  }
}

function onErr() {
  if (!generating.value) return
  // 生成仍在进行：尝试带退避的自动重连，避免网络抖动丢失报告
  es?.close()
  es = null
  if (reconnectAttempts < MAX_RECONNECT) {
    reconnectAttempts++
    const delay = Math.min(1000 * 2 ** reconnectAttempts, 10000)
    setTimeout(() => {
      if (generating.value && sessionId.value) {
        es = connectStream(sessionId.value, onEvent, onErr)
      }
    }, delay)
  } else {
    errorMsg.value = errorMsg.value || '与服务器连接中断，已停止重试'
    finish()
  }
}

function finish() {
  generating.value = false
  es?.close()
  es = null
}

async function stop() {
  if (!generating.value || !sessionId.value) return
  try {
    await cancelGeneration(sessionId.value)
  } catch {
    /* 即使后端调用失败，也按已取消处理 */
  }
  // 乐观更新：立即给出反馈；后端真正中断后可能再发一次 cancelled，幂等无害
  errorMsg.value = '已取消生成'
  finish()
}

async function start() {
  if (generating.value) return
  generating.value = true
  errorMsg.value = ''
  reportMarkdown.value = ''
  logs.value = []
  sessionId.value = ''
  reconnectAttempts = 0
  stages.forEach((s) => (s.status = 'pending'))
  try {
    const sid = await startGeneration(topic.value.trim() || undefined)
    sessionId.value = sid
    es = connectStream(sid, onEvent, onErr)
  } catch (e: any) {
    errorMsg.value = '启动失败：' + (e?.message || e)
    generating.value = false
  }
}
</script>

<template>
  <div class="app-shell">
    <!-- 背景光晕 -->
    <div class="bg-glow glow-1"></div>
    <div class="bg-glow glow-2"></div>
    <div class="bg-glow glow-3"></div>

    <!-- 顶部导航 -->
    <header class="navbar glass">
      <div class="brand">
        <div class="logo-mark">AI</div>
        <span class="brand-name">AI Agent 行业报告生成器</span>
      </div>
      <div class="conn" :class="{ on: connected }">
        <span class="dot"></span>
        <span>{{ connected ? '后端已连接' : '后端未连接' }}</span>
      </div>
    </header>

    <main class="container">
      <!-- 控制区 Hero -->
      <section class="hero glass">
        <div class="hero-text">
          <h1>一键生成你的 AI Agent 行业报告</h1>
        <p class="subtitle">
          基于多智能体（研究员 / 撰稿人 / 编辑）协作，结合实时检索，产出严谨可溯源的行业分析。
        </p>
        <div class="topic-row">
          <input
            v-model="topic"
            class="topic-input"
            type="text"
            :disabled="generating"
            placeholder="输入行业主题，如：人工智能医疗、新能源汽车…"
            @keyup.enter="start"
          />
        </div>
      </div>

        <div class="profile-chip" v-if="profile">
          <span class="chip"><b>姓名</b>{{ profile.name || '—' }}</span>
          <span class="chip"><b>地区</b>{{ profile.location || '—' }}</span>
          <span class="chip"><b>兴趣</b>{{ profile.interest || '—' }}</span>
          <span class="chip"><b>期望薪资</b>{{ profile.expected_salary || '—' }}</span>
        </div>

        <button v-if="!generating" class="btn-generate" @click="start">
          开始生成报告
        </button>
        <button v-else class="btn-generate stop" @click="stop">
          <span class="btn-ring"></span>
          停止生成
        </button>

        <p class="err" v-if="errorMsg">⚠ {{ errorMsg }}</p>
      </section>

      <!-- 主体：进度 + 报告 -->
      <section class="layout">
        <ProgressPanel :stages="stages" :logs="logs" :generating="generating" :error="errorMsg" />
        <div class="report-wrap">
          <ExportDrawer :markdown="reportMarkdown" :session="sessionId" :topic="topic" :disabled="!reportMarkdown" />
          <ReportViewer :markdown="reportMarkdown" />
        </div>
      </section>
    </main>

    <footer class="footer">
      <span>AI Agent 行业报告生成器 · 由 CrewAI + FastAPI + Vue 3 驱动</span>
    </footer>
  </div>
</template>
