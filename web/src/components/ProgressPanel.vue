<script setup lang="ts">
defineProps<{
  stages: { key: string; label: string; status: string }[]
  logs: { id: number; text: string; stage?: string }[]
  generating: boolean
  error: string
}>()

const statusText: Record<string, string> = {
  pending: '等待中',
  running: '进行中',
  done: '已完成',
}
</script>

<template>
  <div class="progress-card glass">
    <h2 class="section-title">
      <span class="title-bar"></span>实时进度
    </h2>

    <ul class="timeline">
      <li v-for="s in stages" :key="s.key" :class="['tl-item', s.status]">
        <span class="tl-dot"></span>
        <span class="tl-label">{{ s.label }}</span>
        <span class="tl-status">{{ statusText[s.status] || s.status }}</span>
      </li>
    </ul>

    <div class="log-box">
      <div v-if="logs.length === 0 && !generating" class="log-empty">
        暂无日志，点击「开始生成报告」后此处实时滚动输出。
      </div>
      <div
        v-for="l in logs"
        :key="l.id"
        class="log-line"
        :class="l.stage ? 'stage-' + l.stage : ''"
      >
        <span class="log-caret">›</span>{{ l.text }}
      </div>
      <div v-if="generating" class="log-line typing">
        <span class="log-caret">›</span>智能体协同工作中<span class="dots"><i>.</i><i>.</i><i>.</i></span>
      </div>
      <div v-if="error" class="log-line err">⚠ {{ error }}</div>
    </div>
  </div>
</template>
