<script setup lang="ts">
import { computed, ref } from 'vue'
import { exportWord, exportMarkdown } from '../api'

const props = defineProps<{
  markdown: string
  session: string
  disabled: boolean
}>()

const open = ref(false)
const busy = ref(false)
const flash = ref('')

// 按行拆分 Markdown，用于终端风格滚动窗口
const previewLines = computed(() => {
  const md = props.markdown || ''
  if (!md.trim()) return []
  return md.split('\n').filter((l) => l.trim() !== '')
})

async function doExport(kind: 'word' | 'md') {
  if (props.disabled || busy.value || !props.markdown) return
  busy.value = true
  try {
    if (kind === 'word') {
      await exportWord(props.markdown, 'AI-Agent行业报告')
      flash.value = 'Word 已导出，开始下载 ✓'
    } else {
      await exportMarkdown(props.session || '', 'AI-Agent行业报告')
      flash.value = 'Markdown 已导出，开始下载 ✓'
    }
  } catch {
    flash.value = '导出失败，请重试'
  } finally {
    busy.value = false
    setTimeout(() => (flash.value = ''), 2400)
  }
}

function close() {
  open.value = false
}
</script>

<template>
  <div class="export-zone">
    <button class="btn-export" :disabled="disabled" @click="open = true">
      导出报告
    </button>

    <teleport to="body">
      <!-- 遮罩 -->
      <transition name="mask-fade">
        <div v-if="open" class="drawer-mask" @click="close"></div>
      </transition>

      <!-- 右侧滑出抽屉 -->
      <transition name="drawer-slide">
        <aside v-if="open" class="drawer glass" role="dialog" aria-label="导出报告">
          <header class="drawer-head">
            <div class="drawer-title">
              <span class="drawer-ico">⤓</span>
              <h3>导出报告</h3>
            </div>
            <button class="drawer-close" aria-label="关闭" @click="close">×</button>
          </header>

          <p class="drawer-desc">将当前生成的报告保存到本地，选择你需要的格式。</p>

          <div class="export-opts">
            <button class="opt" :disabled="disabled || busy" @click="doExport('word')">
              <span class="opt-badge docx">DOCX</span>
              <span class="opt-main">
                <b>Word 文档</b>
                <small>适合打印、投递与正式归档</small>
              </span>
            </button>

            <button class="opt" :disabled="disabled || busy" @click="doExport('md')">
              <span class="opt-badge md">MD</span>
              <span class="opt-main">
                <b>Markdown</b>
                <small>便于二次编辑与版本管理</small>
              </span>
            </button>
          </div>

          <div class="preview-log" v-if="markdown">
            <div class="preview-label">报告预览</div>
            <div ref="logScroll" class="log-scroll">
              <span v-for="(line, i) in previewLines" :key="i" class="log-line">{{ line }}</span>
              <span v-if="!previewLines.length" class="log-empty">暂无内容</span>
            </div>
          </div>

          <transition name="fade">
            <p v-if="flash" class="drawer-flash" :class="{ err: flash.includes('失败') }">
              {{ flash }}
            </p>
          </transition>
        </aside>
      </transition>
    </teleport>
  </div>
</template>
