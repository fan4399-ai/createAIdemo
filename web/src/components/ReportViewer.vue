<script setup lang="ts">
import { computed, ref } from 'vue'
import MarkdownIt from 'markdown-it'

const props = defineProps<{ markdown: string; generating?: boolean }>()

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true,
})
// 禁止 javascript: / data: 等危险协议的链接，降低 XSS 风险
md.validateLink = (url: string) => !/^\s*(javascript|data):/i.test(url)

const html = computed(() => (props.markdown ? md.render(props.markdown) : ''))

const copied = ref(false)
async function copyReport() {
  if (!props.markdown) return
  try {
    await navigator.clipboard.writeText(props.markdown)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    /* 剪贴板不可用时静默失败 */
  }
}
</script>

<template>
  <div class="report-card">
    <!-- 生成中：骨架屏 -->
    <div v-if="!markdown && generating" class="report-skeleton">
      <div class="skeleton-line w70"></div>
      <div class="skeleton-line w90"></div>
      <div class="skeleton-line w55"></div>
      <div class="skeleton-line w80"></div>
      <div class="skeleton-line w65"></div>
      <div class="skeleton-line w85"></div>
      <div class="skeleton-line w45"></div>
      <div class="skeleton-line w75"></div>
      <p class="skeleton-hint">正在生成报告，请稍候…</p>
    </div>

    <!-- 未生成：空态提示 -->
    <div v-else-if="!markdown" class="report-empty">
      <div class="empty-icon">📄</div>
      <p class="empty-title">报告将在此处渲染展示</p>
      <p class="empty-hint">点击「开始生成报告」后，最终 Markdown 报告会实时出现在这里。</p>
    </div>

    <!-- 已生成：报告正文 + 复制按钮 -->
    <div v-else class="report-scroll">
      <div class="report-toolbar">
        <button class="copy-btn" :class="{ done: copied }" @click="copyReport">
          {{ copied ? '✓ 已复制' : '复制全文' }}
        </button>
      </div>
      <article class="markdown-body" v-html="html"></article>
    </div>
  </div>
</template>
