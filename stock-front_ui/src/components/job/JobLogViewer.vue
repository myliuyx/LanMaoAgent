<script setup lang="ts">
/**
 * JobLogViewer — 任务日志查看器
 * 支持滚动加载更多、自动滚动到底部、关键词高亮
 */
import { ref, nextTick } from 'vue'
import { ElScrollbar } from 'element-plus'

const props = withDefaults(
  defineProps<{
    logs: string[]
    loading?: boolean
    done?: boolean
    total?: number
  }>(),
  {
    loading: false,
    done: false,
    total: 0,
  }
)

const emit = defineEmits<{
  'load-more': []
}>()

const scrollbarRef = ref<InstanceType<typeof ElScrollbar>>()

/** 滚动到底部（追加新日志时调用） */
function scrollToBottom(smooth = false) {
  nextTick(() => {
    if (!scrollbarRef.value) return
    const wrap = scrollbarRef.value.$el.querySelector('.el-scrollbar__wrap') as HTMLElement
    if (!wrap) return
    wrap.scrollTo({ top: wrap.scrollHeight, behavior: smooth ? 'smooth' : 'auto' })
  })
}

defineExpose({ scrollToBottom })

/** ERROR/WARN/INFO 行高亮 */
function getLineClass(line: string): string {
  const l = line.trim()
  if (l.startsWith('ERROR') || l.startsWith('error') || l.startsWith('[ERROR]')) return 'log-error'
  if (l.startsWith('WARN') || l.startsWith('warn') || l.startsWith('[WARN]') || l.startsWith('WARNING')) return 'log-warn'
  if (l.startsWith('INFO') || l.startsWith('info') || l.startsWith('[INFO]')) return 'log-info'
  if (l.startsWith('DEBUG') || l.startsWith('debug')) return 'log-debug'
  return ''
}

function onScroll({ scrollTop, scrollHeight, clientHeight }: any) {
  // 滚动到距离底部 50px 时，触发加载更多
  if (scrollHeight - scrollTop - clientHeight < 80 && !props.done && !props.loading) {
    emit('load-more')
  }
}
</script>

<template>
  <div class="log-viewer">
    <div class="log-header">
      <span class="log-count">
        {{ logs.length }} 条{{ total > logs.length ? ` / ${total}` : '' }}
      </span>
      <span v-if="done" class="log-done">已加载全部</span>
    </div>

    <el-scrollbar ref="scrollbarRef" height="100%" @scroll="onScroll">
      <pre class="log-content"><code
        v-for="(line, i) in logs"
        :key="i"
        :class="['log-line', getLineClass(line)]"
      >{{ line }}</code><code v-if="loading" class="log-loading">加载中...</code></pre>
    </el-scrollbar>
  </div>
</template>

<style scoped>
.log-viewer {
  display: flex;
  flex-direction: column;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 12px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  font-size: 12px;
  color: #909399;
}

.log-count {
  font-family: system-ui, sans-serif;
}

.log-done {
  color: #c0c4cc;
}

.log-content {
  margin: 0;
  padding: 12px;
  background: #1e1e1e;
  color: #d4d4d4;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-all;
  min-height: 100px;
}

.log-line {
  display: block;
}

.log-loading {
  display: block;
  color: #909399;
  font-style: italic;
}

/* 高亮 */
.log-error {
  color: #f48771;
  font-weight: 600;
}

.log-warn {
  color: #cca700;
}

.log-info {
  color: #75beff;
}

.log-debug {
  color: #909399;
}
</style>
