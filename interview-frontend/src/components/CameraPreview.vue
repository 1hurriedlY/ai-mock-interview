<template>
  <!-- 摄像头预览 + 表情实时徽标（面试对话窗右侧侧栏） -->
  <div class="camera-preview">
    <div v-if="modelErr" class="err-banner">{{ modelErr }}</div>

    <div v-if="opened" class="cam-box">
      <!-- 摄像头预览 -->
      <video ref="videoEl" autoplay muted playsinline class="video" />
      <div class="cam-side">
        <div class="expr-badge" :class="{ happy }">
          <span class="dot"></span>
          <span>{{ current || '…' }}</span>
        </div>
        <button v-if="!expr.started.value" class="ghost" :disabled="!expr.cameraReady.value" @click="expr.start()">
          开始表情跟踪
        </button>
        <button v-else class="ghost" @click="expr.stop()">暂停跟踪</button>
        <button class="ghost danger" @click="close">关闭摄像头</button>
      </div>
    </div>

    <!-- 摄像头未开：给开关 -->
    <div v-else class="cam-closed">
      <button class="ghost" :disabled="opening" @click="openCamera">
        {{ opening ? '启动中…' : '📷 打开摄像头（表情分析）' }}
      </button>
      <p class="hint">可选。识别你的表情在报告中生成「表情时间轴 + 点评」，画面仅本地处理不上传。</p>
    </div>
  </div>
</template>

<script setup>
import { nextTick, ref } from 'vue'
import { useExpression } from '../composables/useExpression'

const expr = useExpression()
// 顶层解构 ref：模板中自动解包，实时徽标才能拿到当前表情
const { current, happy } = expr

const opened = ref(false)
const opening = ref(false)
const modelErr = ref('')
const videoEl = ref(null)

// 打开摄像头：加载模型 → 拉流 → 绑定预览
async function openCamera() {
  if (opening.value) return
  opening.value = true
  modelErr.value = ''
  const ok = await expr.init()
  if (ok) {
    opened.value = true
    modelErr.value = ''
  } else {
    modelErr.value = expr.error.value || '摄像头启动失败'
  }
  opening.value = false
  // 视频元素已渲染后绑定流
  await nextTick()
  if (opened.value && videoEl.value) expr.attachVideo(videoEl.value)
}

function close() {
  opened.value = false
  expr.stop()
  // 摄像头流关闭由 InterviewView 统一 dispose（本组件不重复 stop，避免误停共享流）
  expr.attachVideo(null)
}

defineExpose({ close })
</script>

<style scoped>
.camera-preview { width: 100%; }
.err-banner { background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; font-size: 12px; padding: 8px 10px; border-radius: 8px; margin-bottom: 10px; }
.cam-box { display: flex; gap: 12px; align-items: flex-start; }
.video { width: 180px; border-radius: 10px; background: #0f172a; transform: scaleX(-1); /* 镜像：与人自视一致 */ object-fit: cover; aspect-ratio: 4/3; }
.cam-side { display: flex; flex-direction: column; gap: 8px; align-items: flex-start; flex: 1; min-width: 0; }
.expr-badge {
  display: inline-flex; align-items: center; gap: 6px; font-size: 13px;
  padding: 4px 10px; border-radius: 12px; background: #f3f4f6; color: var(--text-secondary);
}
.expr-badge .dot { width: 8px; height: 8px; border-radius: 50%; background: #9ca3af; }
.expr-badge.happy { background: #dcfce7; color: #15803d; }
.expr-badge.happy .dot { background: #22c55e; }
.expr-badge:not(.happy) .dot { animation: pulse 1.6s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
.ghost { border: 1px solid var(--border); background: #fff; color: var(--text); font-size: 12px; padding: 5px 10px; border-radius: 8px; cursor: pointer; font-family: inherit; }
.ghost:disabled { opacity: 0.5; cursor: not-allowed; }
.ghost.danger { color: #dc2626; border-color: #fecaca; }
.cam-closed { display: flex; flex-direction: column; gap: 8px; }
.ghost { width: fit-content; }
.hint { font-size: 12px; color: var(--text-secondary); }
</style>
