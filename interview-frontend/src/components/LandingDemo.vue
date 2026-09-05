<template>
  <div class="ld-wrap">
    <!-- ① 首页 · 面试准备 -->
    <section ref="homeEl" class="demo-block big">
      <div class="db-head"><span class="no">①</span><h3>首页 · 面试准备</h3>
        <button class="mini-replay" @click="replayHome">↻ 重播</button></div>
      <div class="mock home">
        <div class="mock-head">
          <i class="wd r"></i><i class="wd y"></i><i class="wd g"></i>
          <span class="url">工作台 · 面试准备</span>
        </div>
        <div class="home-title">今天，练一场面试</div>
        <div class="home-cols">
          <!-- 左：简历（与真实首页一致） -->
          <div class="col resume-panel">
            <span class="zone-h">简历（可选）</span>
            <div class="resume-zone" :class="{ on: rDone }" v-show="rShow">
              <template v-if="!rDone">
                <span class="scan"><i class="spinner"></i>正在解析简历：技能栈 · 项目经历…</span>
              </template>
              <template v-else>
                <span class="file-ok">✓ {{ resumeFile }}</span>
                <span class="up-done">已生成候选人画像</span>
              </template>
            </div>
            <div class="drop-hint">点击选择 / 拖入简历<br />支持 PDF · Word · TXT · Markdown，选中后自动上传解析</div>
          </div>
          <!-- 右：面试配置 -->
          <div class="col cfg-panel">
            <span class="zone-h">面试配置</span>
            <div class="jobfield" :class="{ 'focus-job': hStep === 0 }">
              <div class="jobline">
                <span v-if="jobTyped" class="job">{{ jobTyped }}<i class="caret"></i></span>
                <span v-else class="ph">目标岗位，例如 Python 后端工程师</span>
              </div>
            </div>
            <div class="cfg-toolbar">
              <div v-for="c in cfgItems" :key="c.key" class="sel-item" :class="{ lit: cfgLit[c.key], on: cfgOn[c.key] }">
                <span class="cname">{{ c.name }}</span>
                <span class="srow"><b>{{ c.val }}</b><i class="chev">▾</i></span>
              </div>
            </div>
          </div>
        </div>
        <div class="home-foot">
          <p class="hint">准备好后开始，途中可随时语音回答、开启表情分析<br /><span class="quota-note">免费面试剩余 3 场 · 会员不限场次</span></p>
          <button class="go-btn" :class="{ pulse: hStep === 3 }" :disabled="hStep < 3">
            <span v-if="hStep < 3" class="dim">开始面试</span>
            <span v-else>开始面试 →</span>
          </button>
        </div>
      </div>
    </section>

    <!-- ② 面试对话（流式 · 语音 · 视频表情） -->
    <section ref="chatEl" class="demo-block big">
      <div class="db-head"><span class="no">②</span><h3>面试对话 · 流式回答 + 语音 + 表情视频</h3>
        <button class="mini-replay" @click="replayChat">↻ 重播对话</button></div>

      <div class="chat-grid">
        <!-- 对话窗 -->
        <div class="mock chat-panel">
          <div class="mock-head chat-head">
            <span class="ai-ava">AI</span>
            <span class="who">技术面 · Python 后端工程师</span>
          </div>
          <div class="chat-body" ref="chatBody">
            <div v-for="(m, i) in msgs" :key="i" class="bub-row" :class="m.role">
              <span v-if="m.role === 'ai'" class="ai-ava sm">AI</span>
              <div class="bubble">
                {{ m.text }}
                <span v-if="m.role === 'me' && i === msgs.length - 1 && talking" class="mic-dot">●</span>
                <span v-if="m.role === 'ai' && i === msgs.length - 1 && streaming" class="caret"></span>
              </div>
            </div>
          </div>
          <!-- 底部状态：语音波形 -->
          <div class="voice-bar" v-if="voiceState !== 'idle'">
            <template v-if="voiceState === 'speak'">
              <span class="mic-ico">🎤 语音回答中 · 说完成停顿自动发送</span>
            </template>
            <template v-else>
              <span class="mic-ico">🔊 AI 朗读中</span>
            </template>
            <span class="waves"><i v-for="n in 14" :key="n" :style="{ animationDelay: (n * 0.09) + 's' }"></i></span>
          </div>
          <!-- 输入条（与真实面试页一致） -->
          <div class="ctrl">
            <button class="mic-btn">🎤 语音回答</button>
            <span class="ctrl-input">输入你的回答，Enter 发送</span>
            <button class="send-btn">发送</button>
          </div>
        </div>

        <!-- 模拟视频：表情识别 -->
        <div class="mock video-panel">
          <div class="mock-head">
            <i class="wd g"></i>
            <span class="who">面试画面 · 表情识别</span>
            <span class="rec">● REC</span>
          </div>
          <div class="video-body">
            <div class="face-avatar">
              <svg viewBox="0 0 120 120" width="176" height="176" aria-hidden="true">
                <path d="M 16 70 Q 16 6 60 6 Q 104 6 104 70 L 104 48 C 104 14 16 14 16 48 Z" fill="#4b3b2f" />
                <circle cx="60" cy="64" r="40" fill="#ffd9a0" />
                <circle cx="47" cy="58" r="3.4" fill="#2b2b2b" />
                <circle cx="73" cy="58" r="3.4" fill="#2b2b2b" />
                <path :d="mouthPath" fill="none" stroke="#a34a3a" stroke-width="3.5" stroke-linecap="round" />
              </svg>
              <span class="name-tag">候选人 · 本人视角</span>
            </div>
            <div class="emotion-chip" :class="emotionKey">
              <span>表情</span>
              <b>{{ emotionText }}</b>
            </div>
            <p class="video-note">画面仅本地推理 · 不上传 · 模拟演示</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ③ 面试报告模拟 -->
    <section ref="reportEl" class="demo-block big">
      <div class="db-head"><span class="no">③</span><h3>面试报告 · 多维复盘</h3>
        <button class="mini-replay" @click="replayReport">↻ 重播报告</button></div>
      <div class="mock report-mock">
        <div class="rep-top">
          <div>
            <p class="rep-title">面试评分报告</p>
            <p class="rep-job">Python 后端工程师 · 技术面</p>
          </div>
          <div class="score-pill"><b>86</b><span>分</span></div>
        </div>
        <div class="rep-grid">
          <div class="bars-col">
            <div v-for="dim in dims" :key="dim.name" class="dim">
              <span class="dname">{{ dim.name }}</span>
              <span class="dtrack"><i :style="{ width: dimVal(dim.idx) }"></i></span>
              <span class="dval">{{ Math.round(dim.width * 100) }}</span>
            </div>
          </div>
          <div class="match-col">
            <p class="m-title">岗位匹配</p>
            <p class="m-big">92%</p>
            <p class="m-note">技术栈与 JD 高度匹配</p>
            <div class="exp-btns"><span class="btn-mini">DOCX</span><span class="btn-mini">PDF</span></div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

// 三个区块的根元素 + 是否已触发播放
const homeEl = ref(null)
const chatEl = ref(null)
const reportEl = ref(null)
const started = { home: false, chat: false, report: false }
let ioRef = null

function startEmotions() {
  if (emotionTimer) return
  emotionTimer = setInterval(() => {
    emotionIdx.value = (emotionIdx.value + 1) % emotions.length
  }, 3600)
}

const JOB = 'Python 后端工程师'
const cfgItems = [
  { key: 'd', name: '难度', val: '中等' },
  { key: 'e', name: '学历', val: '本科' },
  { key: 'r', name: '面试官', val: '技术面' },
]

const CHAT_SCRIPT = [
  { role: 'ai', text: '你好，我是本次模拟面试的技术面试官。请先做个自我介绍，重点讲讲你负责过的系统与难点。' },
  { role: 'me', text: '我主要负责订单交易系统，日单量峰值约 200 万。做过读写分离和缓存重构，接口耗时从 420ms 降到 90ms。' },
  { role: 'ai', text: '很好。说说那轮缓存重构：你当时怎么评估缓存一致性，又是如何兜底 DB 击穿的？' },
]

// ---------- ① 首页 ----------
const hStep = ref(0)
const jobTyped = ref('')
const cfgLit = ref({ d: false, e: false, r: false })
const cfgOn = ref({ d: false, e: false, r: false })
const rShow = ref(false)   // 简历卡出现
const rDone = ref(false)   // 简历解析完成
const resumeFile = ref('我的简历-2026.pdf')
let homeTimer = null
let chipTimer = null
let resumeTimer = null

function resetHome() {
  hStep.value = 0
  jobTyped.value = ''
  cfgLit.value = { d: false, e: false, r: false }
  cfgOn.value = { d: false, e: false, r: false }
  rShow.value = false
  rDone.value = false
}
function replayHome() {
  stopHome()
  resetHome()
  playHome()
}
function stopHome() {
  clearTimeout(homeTimer)
  clearTimeout(chipTimer)
  clearTimeout(resumeTimer)
  homeTimer = chipTimer = resumeTimer = null
}
function playHome() {
  // 阶段0：岗位逐字输入
  let i = 0
  homeTimer = setInterval(() => {
    i++
    jobTyped.value = JOB.slice(0, i)
    if (i >= JOB.length) {
      clearInterval(homeTimer)
      homeTimer = null
      // 阶段1：简历上传 → 解析 → 画像
      resumeTimer = setTimeout(() => {
        hStep.value = 1
        rShow.value = true
        resumeTimer = setTimeout(() => {
          rDone.value = true
          // 阶段2：难度/学历/面试官逐个点亮
          hStep.value = 2
          lightChips()
        }, 2400)
      }, 650)
    }
  }, 140)
}
function lightChips() {
  const keys = ['d', 'e', 'r']
  const light = (k) => {
    if (k >= keys.length) {
      hStep.value = 3 // 阶段3：可点击开始（脉冲）
      return
    }
    cfgLit.value[keys[k]] = true
    chipTimer = setTimeout(() => {
      cfgOn.value[keys[k]] = true
      light(k + 1)
    }, 720)
  }
  light(0)
}

// ---------- ② 对话（流式 + 语音 + 视频） ----------
const msgs = ref([])
const streaming = ref(false)
const talking = ref(false)
const voiceState = ref('idle') // idle / speak / aiSpeak
const chatBody = ref(null)
let streamTimer = null
let chatTimer = null
let emotionTimer = null

const emotions = [
  { key: 'happy', text: '开心 96%' },
  { key: 'focus', text: '专注 88%' },
  { key: 'think', text: '思考 79%' },
  { key: 'calm', text: '自然 91%' },
]
const emotionIdx = ref(0)
const emotionKey = computed(() => emotions[emotionIdx.value].key)
const emotionText = computed(() => emotions[emotionIdx.value].text)
// 嘴型：随说话/朗读动
const mouthPath = ref('M 46 84 Q 60 94 74 84')
let mouthTimer = null

function scrollDown() {
  requestAnimationFrame(() => {
    if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
  })
}

function resetChat() {
  clearTimeout(chatTimer)
  clearTimeout(streamTimer)
  clearInterval(mouthTimer)
  msgs.value = []
  streaming.value = false
  talking.value = false
  voiceState.value = 'idle'
}
function replayChat() {
  resetChat()
  playChat()
}
function playChat() {
  const run = (idx) => {
    if (idx >= CHAT_SCRIPT.length) {
      chatTimer = setTimeout(() => { resetChat(); playChat() }, 7000) // 播完稍候重播
      return
    }
    const m = CHAT_SCRIPT[idx]
    if (m.role === 'ai') {
      // AI 流式输出：模拟朗读中
      const aiMsg = { role: 'ai', text: '' }
      msgs.value.push(aiMsg)
      streaming.value = true
      voiceState.value = 'aiSpeak'
      mouthOpen(true)
      let ci = 0
      streamTimer = setInterval(() => {
        ci += 2
        aiMsg.text = m.text.slice(0, ci)
        scrollDown()
        if (ci >= m.text.length) {
          clearInterval(streamTimer)
          streamTimer = null
          streaming.value = false
          voiceState.value = 'idle'
          mouthOpen(false)
          chatTimer = setTimeout(() => run(idx + 1), 2400)
        }
      }, 78)
    } else {
      // 语音作答：麦克风状态 + 波形
      msgs.value.push({ role: 'me', text: m.text })
      voiceState.value = 'speak'
      talking.value = true
      mouthOpen(true)
      chatTimer = setTimeout(() => {
        talking.value = false
        voiceState.value = 'idle'
        mouthOpen(false)
        chatTimer = setTimeout(() => run(idx + 1), 1500)
      }, 3600)
    }
  }
  run(0)
}

function mouthOpen(open) {
  clearInterval(mouthTimer)
  if (!open) {
    mouthPath.value = 'M 46 84 Q 60 94 74 84'
    return
  }
  mouthTimer = setInterval(() => {
    mouthPath.value = mouthPath.value.includes('Q 60 94') ? 'M 46 82 Q 60 100 74 82' : 'M 46 84 Q 60 94 74 84'
  }, 240)
}

// ---------- ③ 报告 ----------
const dims = [
  { name: '专业技能', idx: 0, width: 0.92 },
  { name: '沟通表达', idx: 1, width: 0.8 },
  { name: '逻辑思维', idx: 2, width: 0.86 },
  { name: '项目经验', idx: 3, width: 0.74 },
  { name: '岗位匹配', idx: 4, width: 0.88 },
]
const shown = ref(0)
let reportTimer = null
const dimVal = (idx) => (idx < shown.value ? dims[idx].width * 100 + '%' : '0%')

function replayReport() {
  clearTimeout(reportTimer)
  shown.value = 0
  playReport()
}
function playReport() {
  reportTimer = setInterval(() => {
    if (shown.value < dims.length) shown.value++
    else clearInterval(reportTimer)
  }, 980)
}

onMounted(() => {
  // 滚动到对应区块才开始播放对应演示
  const targets = [
    { el: homeEl.value, key: 'home', start: playHome },
    { el: chatEl.value, key: 'chat', start: () => { playChat(); startEmotions() } },
    { el: reportEl.value, key: 'report', start: playReport },
  ]
  if (!('IntersectionObserver' in window)) {
    targets.forEach((t) => t.start())
    return
  }
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((en) => {
        const t = targets.find((x) => x.el === en.target)
        if (!t || !en.isIntersecting || started[t.key]) return
        started[t.key] = true
        t.start()
      })
      if (Object.values(started).every(Boolean)) io.disconnect()
    },
    { threshold: 0.35 }
  )
  targets.forEach((t) => t.el && io.observe(t.el))
  ioRef = io
})
onBeforeUnmount(() => {
  stopHome()
  resetChat()
  clearTimeout(reportTimer)
  clearInterval(emotionTimer)
  ioRef?.disconnect()
})
</script>

<style scoped>
.ld-wrap { display: flex; flex-direction: column; gap: 92px; max-width: 1160px; margin: 0 auto; }
.demo-block { position: relative; }
.db-head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
.db-head .no { font-size: 17px; font-weight: 800; color: var(--ink); }
.db-head h3 { font-size: 18px; font-weight: 740; color: var(--ink); margin: 0; }

.mock {
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.9);
  border-radius: 18px;
  box-shadow: var(--shadow-md);
  overflow: hidden;
  position: relative;
}
.mock-head { display: flex; align-items: center; gap: 10px; padding: 12px 18px; border-bottom: 1px solid var(--border-soft); }
.wd { width: 10px; height: 10px; border-radius: 50%; }
.wd.r { background: #fca5a5; } .wd.y { background: #fcd34d; } .wd.g { background: #86efac; }
.url { font-size: 13px; color: var(--text-muted); margin-left: 8px; }
.mini-replay {
  margin-left: auto;
  border: 1px solid var(--border); background: var(--card); color: var(--text-secondary);
  font-size: 12px; border-radius: var(--radius-chip); padding: 4px 12px; cursor: pointer;
  transition: var(--transition);
}
.mini-replay:hover { color: var(--ink); border-color: var(--ink); }

/* ① 真实双栏首页演示 */
.home { padding-bottom: 2px; }
.home-title { font-size: 19px; font-weight: 800; color: var(--ink); padding: 14px 18px 0; }
.home-cols { display: grid; grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.35fr); gap: 14px; padding: 12px 18px; }
.col { border: 1px solid var(--border-soft); background: var(--card); border-radius: 16px; padding: 12px 14px; display: flex; flex-direction: column; gap: 10px; }
.zone-h { font-size: 12.5px; font-weight: 750; color: var(--text-secondary); letter-spacing: 0.02em; }
.drop-hint { flex: 1; display: flex; align-items: center; justify-content: center; text-align: center; color: var(--text-muted); font-size: 12.5px; line-height: 1.8; border: 1.5px dashed var(--border); border-radius: 12px; min-height: 92px; }
.jobfield { border: 1.5px solid var(--border); border-radius: 12px; background: var(--bg-soft); padding: 9px 14px; min-height: 48px; display: flex; align-items: center; transition: border-color 0.3s; }
.jobfield.focus-job { border-color: var(--ink); background: #fff; box-shadow: 0 0 0 3px rgba(15, 17, 21, 0.06); }
.jobline { flex: 1; }
.job { font-size: 17px; font-weight: 700; color: var(--ink); }
.ph { font-size: 14px; color: var(--text-muted); }
.caret { display: inline-block; width: 2px; height: 18px; background: var(--ink); margin-left: 2px; vertical-align: -2px; animation: blink 0.7s steps(1) infinite; }
@keyframes blink { 50% { opacity: 0; } }
.cfg-toolbar { display: grid; grid-template-columns: repeat(3, 1fr); border: 1px solid var(--border-soft); border-radius: 13px; overflow: hidden; background: var(--card); }
.sel-item { display: flex; flex-direction: column; gap: 3px; padding: 9px 14px; opacity: 0.4; transition: all 0.4s; }
.sel-item + .sel-item { border-left: 1px solid var(--border-soft); }
.sel-item.lit { opacity: 1; }
.sel-item.on { background: var(--ink-soft); }
.sel-item .cname { font-size: 11px; color: var(--text-muted); font-weight: 650; }
.sel-item .srow { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.sel-item b { font-size: 14px; font-weight: 750; color: var(--ink); }
.sel-item .chev { font-size: 10px; color: var(--text-muted); font-style: normal; }
.sel-item.on .chev { color: var(--ink); }
.home-foot { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 4px 18px 16px; flex-wrap: wrap; }
.hint { margin: 0; font-size: 13px; color: var(--text-secondary); line-height: 1.7; }
.quota-note { font-size: 12px; color: var(--text-muted); }
.go-btn { border: none; background: var(--ink); color: #fff; font-size: 16px; font-weight: 700; padding: 12px 30px; border-radius: var(--radius-chip); }
.go-btn .dim { opacity: 0.55; }
.go-btn.pulse { animation: pulse 1.1s ease-in-out infinite; box-shadow: 0 6px 18px rgba(15, 17, 21, 0.28); }
@keyframes pulse { 50% { transform: scale(1.05); box-shadow: 0 10px 26px rgba(15, 17, 21, 0.35); } }

/* 简历（可选）上传演示 */
.resume-zone {
  border: 1.5px dashed var(--border);
  border-radius: 12px;
  padding: 12px 14px;
  background: var(--bg-soft);
  display: flex;
  align-items: center;
  gap: 10px;
  transition: border-color 0.3s, background 0.3s;
}
.resume-zone.on { border-color: var(--success-text); border-style: solid; background: var(--success-soft); }
.scan { display: inline-flex; align-items: center; gap: 9px; font-size: 13.5px; color: var(--text-secondary); }
.spinner {
  width: 15px; height: 15px; border-radius: 50%;
  border: 2px solid var(--border); border-top-color: var(--ink);
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.file-ok { font-size: 14px; font-weight: 700; color: var(--success-text); }
.up-done { font-size: 12px; color: var(--text-muted); }

/* ② chat grid */
.chat-grid { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(240px, 1fr); gap: 14px; }
.chat-head { background: var(--ink-soft); }
.ai-ava { width: 28px; height: 28px; border-radius: 9px; background: var(--ink); color: #fff; font-size: 12px; font-weight: 750; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; }
.ai-ava.sm { width: 24px; height: 24px; font-size: 10px; border-radius: 8px; }
.who { font-size: 14.5px; font-weight: 650; color: var(--ink); }
.chat-panel { display: flex; flex-direction: column; }
.chat-body { height: 340px; overflow-y: auto; padding: 18px; display: flex; flex-direction: column; gap: 14px; }
.bub-row { display: flex; gap: 10px; align-items: flex-start; }
.bub-row.me { justify-content: flex-end; }
.bubble {
  max-width: 82%; padding: 12px 16px; border-radius: 15px; font-size: 14.5px; line-height: 1.75;
  background: var(--bg-soft); color: var(--text); animation: rise 0.35s var(--ease);
}
.bub-row.me .bubble { background: var(--ink); color: #fff; border-bottom-right-radius: 4px; }
.bub-row.ai .bubble { border-bottom-left-radius: 4px; }
@keyframes rise { from { opacity: 0; transform: translateY(8px); } }
.mic-dot { color: #f87171; font-size: 10px; margin-left: 4px; animation: blink 0.8s steps(1) infinite; }
.voice-bar {
  display: flex; align-items: center; gap: 10px; padding: 8px 14px;
  border-top: 1px solid var(--border-soft); min-height: 38px;
}
.mic-ico { font-size: 12.5px; font-weight: 650; color: var(--ink); }
.waves { display: flex; align-items: center; gap: 3px; height: 20px; }
.waves i { width: 3px; height: 6px; border-radius: 2px; background: var(--ink); opacity: 0.75; animation: wv 0.9s ease-in-out infinite; }
@keyframes wv { 0%, 100% { transform: scaleY(1); } 50% { transform: scaleY(2.6); } }
.ctrl { display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-top: 1px solid var(--border-soft); background: #fff; }
.mic-btn, .send-btn { border: none; border-radius: var(--radius-chip); font-size: 12.5px; font-weight: 700; cursor: default; padding: 7px 12px; }
.mic-btn { background: var(--ink-soft); color: var(--ink); }
.send-btn { background: var(--ink); color: #fff; }
.ctrl-input { flex: 1; height: 30px; line-height: 30px; border-radius: 999px; background: var(--bg-soft); border: 1px solid var(--border); padding: 0 14px; font-size: 12.5px; color: var(--text-muted); overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }

/* 视频窗 */
.rec { margin-left: auto; font-size: 11px; font-weight: 750; color: #ef4444; }
.rec::before { content: ''; display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #ef4444; margin-right: 5px; animation: blink 1s steps(1) infinite; }
.video-panel { display: flex; flex-direction: column; }
.video-body { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 20px 16px; background: linear-gradient(180deg, #eef1f7, #f8fafc); }
.face-avatar { position: relative; width: 176px; height: 196px; }
.face-avatar svg { position: relative; z-index: 2; }
.name-tag {
  position: absolute; left: 50%; bottom: 0; transform: translateX(-50%);
  font-size: 12px; color: #fff; background: rgba(15, 17, 21, 0.72); padding: 3px 12px; border-radius: 999px; white-space: nowrap;
}
.emotion-chip {
  border-radius: 999px; padding: 7px 18px; font-size: 14px; font-weight: 700;
  background: #fff; border: 1px solid var(--border); color: var(--ink);
}
.emotion-chip b { margin-left: 6px; }
.emotion-chip.happy b { color: #f59e0b; } .emotion-chip.focus b { color: #10b981; }
.emotion-chip.think b { color: #8b5cf6; } .emotion-chip.calm b { color: #0ea5e9; }
.video-note { font-size: 12.5px; color: var(--text-muted); margin: 0; }

/* ③ 报告 */
.report-mock { padding: 20px 24px; }
.rep-top { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.rep-title { font-size: 19px; font-weight: 780; color: var(--ink); margin: 0; }
.rep-job { font-size: 13.5px; color: var(--text-muted); margin: 3px 0 0; }
.score-pill { display: flex; align-items: baseline; gap: 5px; background: var(--ink); color: #fff; border-radius: 16px; padding: 10px 22px; }
.score-pill b { font-size: 34px; font-weight: 800; }
.score-pill span { font-size: 14px; opacity: 0.85; }
.rep-grid { display: grid; grid-template-columns: 1.5fr 1fr; gap: 26px; margin-top: 18px; }
.bars-col { display: flex; flex-direction: column; gap: 12px; }
.dim { display: grid; grid-template-columns: 76px 1fr 34px; align-items: center; gap: 10px; }
.dname { font-size: 14px; color: var(--text-secondary); }
.dtrack { height: 12px; border-radius: 999px; background: var(--bg-soft); overflow: hidden; }
.dtrack i { display: block; height: 100%; border-radius: 999px; background: var(--ink); transition: width 0.7s var(--ease); }
.dval { font-size: 14px; font-weight: 750; color: var(--ink); text-align: right; }
.match-col { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 5px; border-left: 1px dashed var(--border-soft); padding-left: 20px; }
.m-title { font-size: 13px; color: var(--text-muted); margin: 0; }
.m-big { font-size: 42px; font-weight: 800; color: var(--ink); margin: 0; }
.m-note { font-size: 13px; color: var(--text-secondary); margin: 0; }
.exp-btns { display: flex; gap: 10px; margin-top: 10px; }
.btn-mini { font-size: 13px; font-weight: 700; padding: 6px 16px; border-radius: 999px; background: var(--ink-soft); color: var(--ink); }

@media (max-width: 760px) {
  .home-cols { grid-template-columns: 1fr; }
  .chat-grid { grid-template-columns: 1fr; }
  .rep-grid { grid-template-columns: 1fr; }
  .match-col { border-left: none; border-top: 1px dashed var(--border-soft); padding: 12px 0 0; }
}
</style>
