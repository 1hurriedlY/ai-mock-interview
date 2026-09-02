<template>
  <div class="voice-control">
    <template v-if="asrSupported || ttsSupported">
      <!-- ASR：麦克风按钮 + 聆听状态（用原生 title 避免按钮禁用遮挡） -->
      <button
        v-if="asrSupported"
        class="v-btn mic"
        :class="{ active: listening }"
        :disabled="disabled || listening"
        :title="listening ? '正在聆听…' : '点击用语音回答（说完成停顿自动发送）'"
        @click="startVoice"
      >
        <span v-if="listening" class="dots"><i></i><i></i><i></i></span>
        <template v-else>🎤 语音回答</template>
      </button>

      <!-- TTS：播报最近一条 AI 回复 -->
      <button
        v-if="ttsSupported"
        class="v-btn tts"
        :disabled="disabled || !latestAssistant"
        :title="speaking ? '停止朗读' : '朗读面试官问题'"
        @click="toggleSpeak"
      >
        {{ speaking ? '⏹ 停止' : '🔊 朗读' }}
      </button>

      <!-- 自动朗读开关 -->
      <label v-if="ttsSupported" class="auto" title="AI 回复后自动朗读">
        <input type="checkbox" v-model="autoSpeak" />
        <span>自动朗读</span>
      </label>
    </template>
    <span v-else class="unsupported">当前浏览器不支持语音，请使用 Chrome / Edge（本机麦克风）</span>
  </div>
</template>

<script setup>
import { useVoice } from '../composables/useVoice'

const props = defineProps({
  disabled: { type: Boolean, default: false },        // 输入区禁用（流式/已结束）时语音一并禁用
  latestAssistant: { type: String, default: '' },     // 最近一条 AI 回复（朗读按钮目标）
})

const emit = defineEmits([
  'interim',   // 识别中间文本（边听边填充输入框）
  'result',    // 识别自然结束 → 全文自动发送
  'draft',     // 手动停 / 未识别到有效句 → 保留文本待编辑
  'speak',     // 需要朗读的新文本（parent 会在 push 到消息列表后调 voice.speak）
])

const voice = useVoice()
const { listening, speaking, autoSpeak, asrSupported, ttsSupported } = voice

function startVoice() {
  if (listening.value) {
    voice.stopListen()
    return
  }
  const handle = voice.listen({
    onInterim: (t) => emit('interim', t),
    onResult: (t) => emit('result', t),
    onDraft: (t) => emit('draft', t),
  })
  if (!handle.started) {
    voice.listen({}) // reset
    // eslint-disable-next-line no-undef
    alert('无法启动麦克风，请检查浏览器麦克风权限')
  }
}

function toggleSpeak() {
  if (speaking.value) voice.cancelSpeak()
  else if (props.latestAssistant) voice.speak(props.latestAssistant)
}

function onAutoSpeakChange() {
  voice.toggleAutoSpeak()
}
</script>

<style scoped>
.voice-control { display: inline-flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
.v-btn {
  border: 1px solid var(--border); border-radius: 20px; padding: 6px 14px;
  font-size: 13px; cursor: pointer; background: #fff; color: var(--text); font-family: inherit;
  display: inline-flex; align-items: center; gap: 6px; min-height: 32px;
}
.v-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.v-btn.mic.active { background: #fee2e2; border-color: #ef4444; color: #dc2626; }
.dots { display: inline-flex; gap: 3px; align-items: center; height: 8px; }
.dots i {
  width: 4px; height: 4px; border-radius: 50%; background: #dc2626;
  animation: hop 1s ease-in-out infinite;
}
.dots i:nth-child(2) { animation-delay: 0.15s; }
.dots i:nth-child(3) { animation-delay: 0.3s; }
@keyframes hop { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }
.v-btn.tts:hover { background: #eff6ff; border-color: var(--primary); }
.auto { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; color: var(--text-secondary); cursor: pointer; user-select: none; }
.unsupported { font-size: 12px; color: var(--text-secondary); }
</style>
