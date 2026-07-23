<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
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
const infoMsg = ref('') // 中性提示（如取消生成），与错误提示区分

// 用户偏好表单（可输入，预填默认画像）；仅本次生成生效
const prefs = reactive({
  name: '',
  career: '',
  expected_salary: '',
  interest: '',
  location: '',
})
const showPrefs = ref(false)

// 用户头像首字（取姓名首字符，大写）
const avatarInitial = computed(() => {
  const name = profile.value?.name || ''
  return name.trim().charAt(0).toUpperCase() || '?'
})

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
    // 预填偏好表单：以默认画像为初始值，用户可修改
    if (profile.value) {
      prefs.name = profile.value.name || ''
      prefs.career = profile.value.career || ''
      prefs.expected_salary = profile.value.expected_salary || ''
      prefs.interest = profile.value.interest || ''
      prefs.location = profile.value.location || ''
    }
  } catch {
    connected.value = false
  }
})

// 将偏好表单拼装为与 knowledge/user_preference.txt 同格式的文本；全空则返回 undefined
function buildPreference(): string | undefined {
  const lines: string[] = []
  if (prefs.name.trim()) lines.push(`用户姓名：${prefs.name.trim()}`)
  if (prefs.career.trim()) lines.push(`用户职业：${prefs.career.trim()}`)
  if (prefs.expected_salary.trim()) lines.push(`用户期望薪资：${prefs.expected_salary.trim()}`)
  if (prefs.interest.trim()) lines.push(`用户兴趣：${prefs.interest.trim()}`)
  if (prefs.location.trim()) lines.push(`用户所在地：${prefs.location.trim()}`)
  return lines.length ? lines.join('\n') : undefined
}

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
    infoMsg.value = e.message || '已取消生成'
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
  infoMsg.value = '已取消生成'
  finish()
}

async function start() {
  if (generating.value) return
  generating.value = true
  errorMsg.value = ''
  infoMsg.value = ''
  reportMarkdown.value = ''
  logs.value = []
  sessionId.value = ''
  reconnectAttempts = 0
  stages.forEach((s) => (s.status = 'pending'))
  try {
    const sid = await startGeneration(topic.value.trim() || undefined, buildPreference())
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
        <span class="brand-name">AI Agent 行业报告生成助手</span>
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
          <span class="hero-badge">✦ 多智能体协作 · 实时检索增强</span>
          <h1>一键生成你的 AI Agent 行业报告</h1>
        <p class="subtitle">
          基于多智能体（研究员 / 撰稿人 / 编辑）协作，结合实时检索，产出严谨可溯源的行业分析。
        </p>
        <div class="topic-row">
          <input
            v-model="topic"
            class="topic-input"
            type="text"
            maxlength="500"
            :disabled="generating"
            placeholder="输入行业主题，如：人工智能医疗、新能源汽车…"
            @keyup.enter="start"
          />
        </div>

        <div class="prefs-row">
          <button
            class="prefs-toggle"
            :class="{ active: showPrefs }"
            :disabled="generating"
            @click="showPrefs = !showPrefs"
          >
            <span class="caret">{{ showPrefs ? '▾' : '▸' }}</span>
            自定义生成偏好（可选）
          </button>
          <transition name="fade">
            <div v-if="showPrefs" class="prefs-panel">
              <div class="prefs-grid">
                <label class="pref-field">
                  <span>姓名</span>
                  <input v-model="prefs.name" maxlength="40" placeholder="如：张三" :disabled="generating" />
                </label>
                <label class="pref-field">
                  <span>职业</span>
                  <input v-model="prefs.career" maxlength="60" placeholder="如：后端工程师" :disabled="generating" />
                </label>
                <label class="pref-field">
                  <span>期望薪资</span>
                  <input v-model="prefs.expected_salary" maxlength="40" placeholder="如：25k-35k" :disabled="generating" />
                </label>
                <label class="pref-field">
                  <span>兴趣</span>
                  <input v-model="prefs.interest" maxlength="80" placeholder="如：AI 编程" :disabled="generating" />
                </label>
                <label class="pref-field">
                  <span>所在地</span>
                  <input v-model="prefs.location" maxlength="40" placeholder="如：上海" :disabled="generating" />
                </label>
              </div>
              <p class="prefs-hint">留空字段将沿用默认画像（knowledge/user_preference.txt），仅本次生成生效。</p>
            </div>
          </transition>
        </div>
      </div>

        <div class="profile-card" v-if="profile">
          <div class="avatar">{{ avatarInitial }}</div>
          <div class="chips">
            <span class="chip"><b>姓名</b>{{ profile.name || '—' }}</span>
            <span class="chip"><b>地区</b>{{ profile.location || '—' }}</span>
            <span class="chip"><b>兴趣</b>{{ profile.interest || '—' }}</span>
            <span class="chip"><b>期望薪资</b>{{ profile.expected_salary || '—' }}</span>
          </div>
        </div>

        <button v-if="!generating" class="btn-generate" @click="start">
          开始生成报告
        </button>
        <button v-else class="btn-generate stop" @click="stop">
          <span class="btn-ring"></span>
          停止生成
        </button>

        <p class="err" v-if="errorMsg">⚠ {{ errorMsg }}</p>
        <p class="info" v-if="infoMsg">ℹ {{ infoMsg }}</p>
      </section>

      <!-- 主体：进度 + 报告 -->
      <section class="layout">
        <ProgressPanel :stages="stages" :logs="logs" :generating="generating" :error="errorMsg" />
        <div class="report-wrap">
          <ExportDrawer :markdown="reportMarkdown" :session="sessionId" :topic="topic" :disabled="!reportMarkdown" />
          <ReportViewer :markdown="reportMarkdown" :generating="generating" />
        </div>
      </section>
    </main>

    <footer class="footer">
      <span>AI Agent 行业报告生成助手 · 由 CrewAI + FastAPI + Vue 3 驱动</span>
    </footer>
  </div>
</template>

<style scoped>
.prefs-row {
  margin: 14px auto 0;
  max-width: 560px;
  text-align: left;
}
.prefs-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  font-family: inherit;
  font-size: 13px;
  padding: 4px 2px;
  transition: color 0.15s ease;
}
.prefs-toggle:hover:not(:disabled),
.prefs-toggle.active {
  color: var(--primary-3);
}
.prefs-toggle:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.prefs-toggle .caret {
  font-size: 11px;
}
.prefs-panel {
  margin-top: 10px;
  padding: 16px;
  background: rgba(2, 6, 23, 0.4);
  border: 1px solid var(--glass-border);
  border-radius: 14px;
}
.prefs-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.pref-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--text-muted);
}
.pref-field input {
  width: 100%;
  padding: 10px 12px;
  font-family: inherit;
  font-size: 14px;
  color: var(--text);
  background: rgba(2, 6, 23, 0.5);
  border: 1px solid var(--glass-border);
  border-radius: 10px;
  outline: none;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}
.pref-field input::placeholder {
  color: rgba(148, 163, 184, 0.6);
}
.pref-field input:focus {
  border-color: rgba(99, 102, 241, 0.7);
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.18);
}
.pref-field input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.prefs-hint {
  margin-top: 12px;
  font-size: 12px;
  color: rgba(148, 163, 184, 0.75);
  line-height: 1.6;
}
@media (max-width: 640px) {
  .prefs-grid {
    grid-template-columns: 1fr;
  }
}
</style>
