<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'

const props = defineProps<{ markdown: string }>()

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  breaks: true,
})

const html = computed(() => (props.markdown ? md.render(props.markdown) : ''))
</script>

<template>
  <div class="report-card">
    <div v-if="!markdown" class="report-empty">
      <div class="empty-icon">📄</div>
      <p class="empty-title">报告将在此处渲染展示</p>
      <p class="empty-hint">点击「开始生成报告」后，最终 Markdown 报告会实时出现在这里。</p>
    </div>
    <div v-else class="report-scroll">
      <article class="markdown-body" v-html="html"></article>
    </div>
  </div>
</template>
