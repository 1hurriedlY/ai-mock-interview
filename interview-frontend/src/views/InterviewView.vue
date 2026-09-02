<template>
  <div class="interview-view">
    <div class="topbar">
      <h1>模拟面试进行中</h1>
      <div class="top-right">
        <span class="stage-badge">当前阶段：{{ stageName }}</span>
        <button class="ghost" @click="confirmEnd">结束面试</button>
      </div>
    </div>

    <div v-if="!sessionId" class="empty card">
      <p>没有进行中的面试，回到首页开始一场吧。</p>
      <router-link class="primary-link" to="/home">去首页</router-link>
    </div>

    <template v-else>
      <div class="chat-layout">
        <!-- 对话主区 -->
        <div class="chat-main">
          <!-- 对话窗 -->
          <div ref="chatBox" class="chat-box card">
            <div
              v-for="(m, i) in messages"
              :key="i"
              class="msg"
              :class="m.role === 'user' ? 'right' : 'left'"
            >
              <div class="bubble">{{ m.content }}</div>
            </div>
            <!-- 打字机光标 -->
            <div v-if="typingText" class="msg left">
              <div class="bubble typing">{{ typingText }}<span class="cursor">▍</span></div>
            </div>
          </div>

          <p v-if="error" class="error">{{ error }}</p>

          <p v-if="loading" class="hint">正在加载面试进度…</p>

          <!-- 语音控制条 -->
          <VoiceControl
            :disabled="allDone"
            :latest-assistant="latestAssistant"
            @interim="draft = $event"
            @result="send($event)"
            @draft="draft = $event"
          />

          <!-- 输入区 -->
          <div class="input-bar">
            <input
              v-model.trim="draft"
              :placeholder="listening ? '正在聆听，说完成停顿自动发送…' : '输入你的回答，Enter 发送'"
              :disabled="allDone"
              @keyup.enter="send()"
            />
            <button class="primary" :disabled="!draft || allDone" @click="send()">
              {{ allDone && !ended ? '思考中…' : '发送' }}
            </button>
          </div>
          <p v-if="ended" class="hint">面试已结束，正在生成报告…</p>
        </div>

        <!-- 摄像头 + 表情实时侧栏 -->
        <aside class="cam-sidebar">
          <CameraPreview v-show="exprVisible" />
          <div v-if="exprCurrent" class="expr-now">
            <span class="now-label">当前表情</span>
            <strong :class="{ 'is-happy': exprHappy }">{{ exprCurrent }}</strong>
          </div>
        </aside>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { historyApi, interviewApi } from '../api'
import { useStreamChat } from '../composables/useStreamChat'
import { useTypewriter } from '../composables/useTypewriter'
import { useVoice } from '../composables/useVoice'
import { useExpression } from '../composables/useExpression'
import VoiceControl from '../components/VoiceControl.vue'
import CameraPreview from '../components/CameraPreview.vue'

const route = useRoute()
const router = useRouter()

const STAGE_NAMES = {
  opening: '开场自我介绍',
  basic: '基础题',
  deep: '深度题',
  stress: '压力/场景题',
  closing: '收尾反问',
}

const sessionId = ref(route.params.id ? Number(route.params.id) : null)
const messages = ref([])
const draft = ref('')
const stage = ref('opening')
const ended = ref(false)
const error = ref('')
const loadingEnd = ref(false)
const loading = ref(false)
const latestAssistant = ref('') // 最近一条 AI 回复（供朗读按钮/自动朗读）

const chatBox = ref(null)
const typewriter = useTypewriter()
const typingText = typewriter.text // 打字机当前文本（供模板渲染打字光标气泡）
const chat = useStreamChat(sessionId.value)
const voice = useVoice()
const expr = useExpression()

const { listening } = voice
// 顶层解构 ref：模板中自动解包（expr.current 是套在普通对象里的 ref，直接访问不会解包）
const { current: exprCurrent, happy: exprHappy } = expr
const exprVisible = ref(true) // 摄像头侧栏默认显示（原写死 false 且无处置 true，导致面板永远隐藏）

const stageName = computed(() => STAGE_NAMES[stage.value] || stage.value)
const allDone = computed(() => chat.streaming.value || ended.value)

// 流式事件 → 打字机 + 消息列表
chat.onMessage({
  delta: (d) => typewriter.appendDelta(d),
  done: (payload) => {
    typewriter.finish()
    pushAssistant(payload.reply)
    stage.value = payload.stage || stage.value
    // 回复完整后：自动朗读（若开启）优先于语音聆听自动发送
    if (voice.autoSpeak.value && voice.ttsSupported.value) {
      voice.speak(payload.reply)
    }
    if (payload.finished) {
      ended.value = true
      finishInterview()
    }
    typewriter.reset()
  },
})

function pushAssistant(content) {
  messages.value.push({ role: 'assistant', content })
  latestAssistant.value = content
  scrollBottom()
}
function pushUser(content) {
  messages.value.push({ role: 'user', content })
  scrollBottom()
}

async function send(text) {
  // 防御：text 应为字符串（语音识别结果）；若误传 DOM 事件对象则忽略，改用输入框草稿
  const raw = typeof text === 'string' && text.trim() ? text : draft.value
  const content = (raw || '').trim()
  if (!content || chat.streaming.value || ended.value) return
  draft.value = ''
  pushUser(content)
  typewriter.reset()
  try {
    await chat.send(content)
  } catch (e) {
    error.value = e.message || '发送失败'
  }
  scrollBottom()
}

async function finishInterview() {
  loadingEnd.value = true
  try {
    // 带上本场表情时间轴（本地识别汇总，未开摄像头则空数组）
    const data = await interviewApi.end(sessionId.value, expr.sequence.value)
    // 报告生成后跳转报告页（报告页按 session_id 加载详情）
    if (data.report_id) {
      router.replace({ name: 'report', params: { id: data.session_id } })
    }
  } catch (e) {
    error.value = e.response?.data?.detail || '生成报告失败，请到历史页重试'
    loadingEnd.value = false
  }
}

async function confirmEnd() {
  if (!window.confirm('确定结束面试并生成评分报告吗？')) return
  ended.value = true
  await finishInterview()
}

function scrollBottom() {
  nextTick(() => {
    if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
  })
}

watch(() => typewriter.text.value, scrollBottom)

// 进入已有会话：拉取历史消息（开场白/此前问答）恢复现场
async function loadHistory() {
  if (!sessionId.value) return
  loading.value = true
  try {
    const detail = await historyApi.detail(sessionId.value)
    messages.value = (detail.messages || [])
      .filter((m) => m.role === 'user' || m.role === 'assistant')
      .map((m) => ({ role: m.role, content: m.content }))
    if (detail.status === 'completed') ended.value = true
    // 用服务端题卡阶段恢复现场（未结束时才有）；无卡则留在 opening
    if (detail.stage) stage.value = detail.stage
    // 末条 AI 消息作为朗读对象
    for (let i = messages.value.length - 1; i >= 0; i--) {
      if (messages.value[i].role === 'assistant') {
        latestAssistant.value = messages.value[i].content
        break
      }
    }
    scrollBottom()
  } catch (e) {
    error.value = e.response?.data?.detail || '加载面试进度失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadHistory)

onBeforeUnmount(() => {
  // 离开页面前若已结束但未跳转，仍尝试生成报告（异步 fire-and-forget）
  if (ended.value && !loadingEnd.value) {
    interviewApi.end(sessionId.value, expr.sequence.value).catch(() => {})
  }
  // 释放摄像头（停止采样 + 关闭流 + 释放麦克风灯）
  expr.dispose()
})
</script>

<style scoped>
.interview-view { max-width: 860px; margin: 0 auto; padding: 24px 16px 40px; }
.topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
.topbar h1 { font-size: 20px; color: var(--primary); }
.top-right { display: flex; align-items: center; gap: 12px; }
.stage-badge {
  background: #e0e7ff; color: #3730a3; font-size: 12px;
  padding: 4px 12px; border-radius: 12px;
}
.ghost {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 6px 14px; border-radius: 8px; cursor: pointer; font-size: 13px;
}
.card {
  background: var(--card); border: 1px solid var(--border); border-radius: 12px;
}
.chat-box { padding: 16px; height: 50vh; min-height: 320px; overflow-y: auto; }
.chat-layout { display: flex; gap: 16px; align-items: flex-start; }
.chat-main { flex: 1; min-width: 0; }
.cam-sidebar { width: 224px; flex-shrink: 0; display: flex; flex-direction: column; gap: 10px; }
.expr-now {
  background: var(--card); border: 1px solid var(--border); border-radius: 12px;
  padding: 10px 12px; display: flex; align-items: center; justify-content: space-between;
}
.expr-now .now-label { font-size: 12px; color: var(--text-secondary); }
.expr-now strong { font-size: 15px; color: var(--text); }
.expr-now strong.is-happy { color: #059669; }
@media (max-width: 900px) { .chat-layout { flex-direction: column; } .cam-sidebar { width: 100%; order: -1; } }
.msg { display: flex; margin-bottom: 12px; }
.msg.left { justify-content: flex-start; }
.msg.right { justify-content: flex-end; }
.bubble {
  max-width: 78%; padding: 10px 14px; border-radius: 12px; line-height: 1.7; white-space: pre-wrap;
}
.msg.left .bubble { background: #f1f3f5; color: var(--text); border-top-left-radius: 4px; }
.msg.right .bubble { background: var(--primary); color: #fff; border-top-right-radius: 4px; }
.typing { color: #555; }
.cursor { animation: blink 0.8s step-end infinite; }
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
.error { color: #dc2626; margin: 8px 0; }
.input-bar { display: flex; gap: 10px; margin-top: 14px; }
.input-bar input {
  flex: 1; padding: 12px 14px; border: 1px solid var(--border); border-radius: 10px; font-size: 14px;
}
.input-bar input:focus { outline: none; border-color: var(--primary); }
.input-bar .primary {
  background: var(--primary); color: #fff; border: none; padding: 0 22px;
  border-radius: 10px; cursor: pointer; font-size: 14px;
}
.input-bar .primary:disabled { opacity: 0.5; cursor: not-allowed; }
.hint { color: var(--text-secondary); font-size: 13px; margin-top: 8px; }
</style>
