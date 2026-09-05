<template>
  <div class="report-view" :class="{ 'is-gen': isGenerating && !report }">
    <div v-if="error && !report && !isGenerating" class="card empty">
      <p class="error">{{ error }}</p>
      <router-link class="primary-link" to="/history">回历史页</router-link>
    </div>

    <!-- 报告后台生成中：骨架 + 自动轮询 -->
    <div v-else-if="!report && isGenerating" class="card gen">
      <div class="gen-dots"><i></i><i></i><i></i></div>
      <h2>正在生成你的评分报告</h2>
      <p class="gen-sub">
        AI 正在分析你的作答并逐项评分… 生成后本页会自动展示，也可稍后从「面试历史」进入查看。
      </p>
      <p v-if="error" class="error gen-err">{{ error }}</p>
    </div>

    <template v-if="report">
      <div class="report-header">
        <h1>{{ reportTitle }}</h1>
        <div class="actions">
          <button class="btn-docx" @click="doExport('docx')">导出 DOCX</button>
          <button class="btn-pdf" @click="doExport('pdf')">导出 PDF</button>
          <router-link class="ghost-link" :to="{ name: 'history' }">历史</router-link>
        </div>
      </div>
      <p v-if="exportMsg" class="export-msg">{{ exportMsg }}</p>

      <!-- 综合得分 + 总评 -->
      <section class="card score-card">
        <div class="score-num" :class="scoreClass">{{ report.overall_score }}<span>/100</span></div>
        <div class="score-right">
          <h3>综合评估</h3>
          <p class="summary">{{ report.summary }}</p>
        </div>
      </section>

      <!-- 雷达图 -->
      <section class="card" v-if="hasDim">
        <h2>五维能力</h2>
        <ScoreRadar :dimensions="report.dimensions" :height="320" />
      </section>

      <!-- 匹配分析 -->
      <section class="card" v-if="report.match_analysis && report.match_analysis.reason">
        <h2>岗位匹配度：<span class="level">{{ report.match_analysis.match_level || '—' }}</span></h2>
        <p class="reason">{{ report.match_analysis.reason }}</p>
      </section>

      <!-- 面试优点与不足 -->
      <section class="card" v-if="hasProsCons">
        <h2>面试优点与不足</h2>
        <div class="two-col">
          <div>
            <h3 class="good">✓ 优点</h3>
            <ul v-if="report.match_analysis?.strengths?.length">
              <li v-for="(s, i) in report.match_analysis.strengths" :key="i">{{ s }}</li>
            </ul>
            <p v-else class="reason">本次面试未识别到明显突出点。</p>
          </div>
          <div>
            <h3 class="warn">△ 不足</h3>
            <ul v-if="report.match_analysis?.gaps?.length">
              <li v-for="(g, i) in report.match_analysis.gaps" :key="i">{{ g }}</li>
            </ul>
            <p v-else class="reason">本次面试暂未发现明显不足。</p>
          </div>
        </div>
      </section>

      <!-- 建议 -->
      <section class="card" v-if="report.suggestions?.length">
        <h2>改进建议</h2>
        <ol class="suggestions">
          <li v-for="(s, i) in report.suggestions" :key="i">{{ s }}</li>
        </ol>
      </section>

      <!-- 表情分析 -->
      <section class="card" v-if="exprData.has">
        <h2>表情表现分析</h2>
        <ExpressionChart :sequence="exprData.sequence" :comment="report.expression_analysis?.comment || ''" />
        <p v-if="!report.expression_analysis?.comment && !report.expression_analysis?.highlights?.length" class="reason">
          表情时间轴展示面试全程情绪起伏；开启摄像头并跟踪表情后，报告会结合时间轴生成点评。
        </p>
        <ul v-if="report.expression_analysis?.highlights?.length" class="plain-list">
          <li v-for="(h, i) in report.expression_analysis.highlights" :key="i">· {{ h }}</li>
        </ul>
      </section>

      <!-- 面试逐题复盘（可折叠） -->
      <section class="card" v-if="referenceItems.length">
        <h2 class="clickable" @click="showRef = !showRef">
          面试逐题复盘（{{ referenceItems.length }} 题）
          <span class="fold">{{ showRef ? '收起 ▲' : '展开 ▼' }}</span>
        </h2>
        <p v-if="retrainErr" class="retrain-err">{{ retrainErr }}</p>
        <div v-if="showRef">
          <div v-for="it in referenceItems" :key="it.index" class="qa-item">
            <p class="q"><b>面试官提问</b>：{{ it.question }}</p>
            <p v-if="it.answer" class="ans"><b>你的回答</b>：{{ it.answer }}</p>
            <p v-else class="ans skip"><b>你的回答</b>：本题未作答</p>
            <div class="ref-box"><span class="tag">参考答案</span>{{ it.ref || '本题参考答案生成失败，可重新生成报告' }}</div>
            <div v-if="it.good.length || it.weak.length" class="crit">
              <p v-if="it.good.length" class="good"><b>✓ 答得好的地方</b>：{{ it.good.join('；') }}</p>
              <p v-if="it.weak.length" class="warn"><b>△ 欠缺 / 答得不好</b>：{{ it.weak.join('；') }}</p>
            </div>
            <button
              v-if="it.trainable"
              type="button"
              class="retrain-btn"
              :disabled="retrainingKey === it.index"
              @click="retrainOn(it)"
            >
              {{ retrainingKey === it.index ? '正在生成专项练习…' : '这道题没答好 · 再来一轮专项练习' }}
            </button>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { downloadReport, exportApi, historyApi, interviewApi } from '../api'
import ScoreRadar from '../components/ScoreRadar.vue'
import ExpressionChart from '../components/ExpressionChart.vue'

const route = useRoute()
const router = useRouter()
const report = ref(null)
const error = ref('')
const isGenerating = ref(false)
const showRef = ref(false)
const exportMsg = ref('')
const rawMessages = ref([])
const jobTitle = ref('')

const hasDim = computed(() => Object.keys(report.value?.dimensions || {}).length > 0)
const hasProsCons = computed(
  () => Boolean(
    report.value?.match_analysis?.strengths?.length
    || report.value?.match_analysis?.gaps?.length
  )
)

// 表情数据源：历史报告无表情时间轴时用空序列（不报错也不渲染空图）
const exprData = computed(() => {
  const ea = report.value?.expression_analysis || {}
  const seq = Array.isArray(ea.timeline) ? ea.timeline
    : (Array.isArray(ea.sequence) ? ea.sequence : [])
  const has = Boolean(report.value && (ea.comment || ea.highlights?.length || seq.length))
  return { has, sequence: seq }
})

// 逐题复盘：优先使用报告里 AI 生成的参考答案(qna)；
// 老报告没有 qna 时，回退用消息里的参考要点配对
const strList = (v) => (Array.isArray(v) ? v.map(String).filter(Boolean) : [])
const referenceItems = computed(() => {
  const qna = report.value?.qna
  let items = []
  if (Array.isArray(qna) && qna.length) {
    for (const it of qna) {
      if (!it.question) continue
      items.push({
        index: items.length + 1,
        question: it.question,
        answer: it.answer || '',
        ref: it.model_answer || '',
        good: strList(it.good_points),
        weak: strList(it.weak_points),
      })
    }
  } else {
    const arr = rawMessages.value
    for (let i = 0; i < arr.length; i++) {
      const m = arr[i]
      if (m.role !== 'assistant' || !m.reference) continue
      const answerParts = []
      for (let j = i + 1; j < arr.length; j++) {
        if (arr[j].role === 'user') answerParts.push(arr[j].content)
        else break // 下一条面试官消息 = 新的一题
      }
      items.push({
        index: items.length + 1,
        question: m.content,
        answer: answerParts.join('\n'),
        ref: m.reference,
        good: [],
        weak: [],
      })
    }
  }
  items = items.map((it) => ({
    ...it,
    // 允许发起专项复练：这题答得不好 / 有明确不足 / 直接没作答
    trainable: !it.answer || it.weak.length > 0,
  }))
  return items
})

// 薄弱题 → 再来一轮专项练习
const retrainingKey = ref(0)
const retrainErr = ref('')
async function retrainOn(it) {
  if (retrainingKey.value) return
  retrainingKey.value = it.index
  retrainErr.value = ''
  try {
    const data = await interviewApi.retrain(route.params.id, it.question)
    router.push(`/interview/${data.session_id}`)
  } catch (e) {
    retrainErr.value = e.response?.data?.detail || '发起专项练习失败，请稍后重试'
    retrainingKey.value = 0
  }
}

const reportTitle = computed(() => jobTitle.value || '面试评估报告')

const scoreClass = computed(() => {
  const s = report.value?.overall_score || 0
  if (s >= 85) return 'score-good'
  if (s >= 70) return 'score-mid'
  return 'score-low'
})

onMounted(async () => {
  try {
    const detail = await historyApi.detail(route.params.id) // 通过 session_id 取详情
    jobTitle.value = detail.job_title || ''
    rawMessages.value = detail.messages || []
    report.value = detail.report
    if (report.value) return
    // 报告尚未生成：会话已结束 → 进入"生成中"并自动轮询，直到报告就绪
    if (detail.status === 'completed') {
      isGenerating.value = true
      pollReport()
      return
    }
    error.value = '该会话还没有评分报告，请先在面试中结束面试。'
  } catch (e) {
    error.value = e.response?.data?.detail || '加载报告失败'
  }
})

// 轮询：报告在后端后台生成，就绪后自动渲染（离开页面即停止）
let disposed = false
let pollTimer = null

function pollReport() {
  if (disposed) return
  pollTimer = setTimeout(async () => {
    try {
      const detail = await historyApi.detail(route.params.id)
      if (detail.report) {
        jobTitle.value = detail.job_title || ''
        rawMessages.value = detail.messages || []
        report.value = detail.report
        isGenerating.value = false
        return
      }
      if (detail.status !== 'completed') {
        error.value = '该会话还没有评分报告，请先在面试中结束面试。'
        isGenerating.value = false
        return
      }
      pollReport() // 仍在生成，继续等
    } catch (e) {
      error.value = '报告仍在生成中，网络暂时不可用，即将自动重试…'
      pollReport()
    }
  }, 1500)
}

onBeforeUnmount(() => {
  disposed = true
  if (pollTimer) clearTimeout(pollTimer)
})

async function doExport(format) {
  exportMsg.value = `正在生成 ${format.toUpperCase()}…`
  try {
    // 先触发生成（获取 report_id），再用 blob 方式下载
    const info = await exportApi.export(report.value.id, format)
    await downloadReport(report.value.id, format)
    exportMsg.value = `${format.toUpperCase()} 已导出：${info.filename}（${info.size} 字节）`
  } catch (e) {
    exportMsg.value = ''
    const detail = e.response?.data?.detail || '导出失败，请稍后重试'
    if (e.response?.status === 402 && window.confirm(`${detail}\n\n是否前往会员中心开通？`)) {
      router.push({ name: 'membership' })
      return
    }
    alert(detail)
  }
}
</script>

<style scoped>
.report-view { max-width: 900px; margin: 0 auto; padding: 24px 24px 56px; }

/* 生成中：整屏上下居中，卡片收窄更聚焦 */
.report-view.is-gen {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.report-view.is-gen .gen {
  width: min(560px, 100%);
  margin: 0 auto;
}
.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  flex-wrap: wrap;
  gap: 14px;
}
.report-header h1 {
  color: var(--ink);
  font-size: 22px;
  font-weight: 740;
  letter-spacing: -0.012em;
}
.actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.btn-docx, .btn-pdf {
  border-radius: var(--radius-chip);
  cursor: pointer;
  font-size: 13.5px;
  font-weight: 600;
  height: 38px;
  padding: 0 18px;
  border: 1px solid transparent;
  display: inline-flex;
  align-items: center;
  transition: var(--transition);
}
.btn-docx { background: var(--ink); color: #fff; border-color: var(--ink); }
.btn-docx:hover { background: var(--ink-hover); box-shadow: 0 8px 20px rgba(15, 17, 21, 0.18); }
.btn-pdf { background: var(--card); color: var(--ink); border-color: var(--border); }
.btn-pdf:hover { border-color: var(--ink); background: var(--ink-soft); }
.btn-docx:active, .btn-pdf:active { transform: scale(0.98); }
.ghost-link {
  color: var(--text-secondary);
  text-decoration: none;
  border: 1px solid var(--border);
  padding: 0 16px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  border-radius: var(--radius-chip);
  font-size: 13.5px;
  transition: var(--transition);
}
.ghost-link:hover { color: var(--ink); border-color: var(--ink); }
.export-msg { color: var(--success); font-size: 13px; margin-bottom: 14px; }
.card {
  background: var(--card);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-sm);
  padding: 22px 24px;
  margin-bottom: 16px;
}
.empty { text-align: center; padding: 48px; }

/* 报告生成中骨架 */
.gen {
  text-align: center;
  padding: 56px 24px;
}
.gen-dots {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 20px;
}
.gen-dots i {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--ink);
  opacity: 0.25;
  animation: gen-bounce 1.2s var(--ease) infinite;
}
.gen-dots i:nth-child(2) { animation-delay: 0.15s; }
.gen-dots i:nth-child(3) { animation-delay: 0.3s; }
@keyframes gen-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.25; }
  30% { transform: translateY(-6px); opacity: 1; }
}
.gen h2 {
  font-size: 20px;
  font-weight: 720;
  color: var(--ink);
}
.gen-sub {
  margin: 10px auto 0;
  max-width: 46ch;
  color: var(--text-secondary);
  font-size: 13.5px;
  line-height: 1.8;
}
.gen-err { margin-top: 14px; }
.error { color: var(--danger); }
.primary-link { display: inline-block; margin-top: 12px; color: var(--ink); }
.score-card {
  display: flex;
  gap: 28px;
  align-items: center;
}
.score-num {
  font-size: 64px;
  font-weight: 780;
  min-width: 160px;
  text-align: center;
  letter-spacing: -0.02em;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.score-num span { font-size: 18px; color: var(--text-muted); font-weight: 400; margin-left: 2px; }
.score-good { color: var(--success); }
.score-mid { color: var(--warning); }
.score-low { color: var(--danger); }
.score-right { flex: 1; }
.score-right h3 { margin-bottom: 8px; font-size: 14.5px; color: var(--ink); }
.summary { color: var(--text); line-height: 1.85; font-size: 14.5px; }
.reason { line-height: 1.85; color: var(--text); font-size: 14.5px; }
h2 {
  font-size: 17px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 14px;
  letter-spacing: -0.005em;
}
h2 .level { color: var(--ink); }
h3 { font-size: 14px; margin-bottom: 8px; font-weight: 650; }
h3.good { color: var(--success-text); }
h3.warn { color: var(--warning-text); }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 32px; margin-top: 14px; }
.two-col ul, .suggestions, .plain-list { padding-left: 20px; }
.two-col li, .suggestions li, .plain-list li { margin-bottom: 8px; line-height: 1.75; color: var(--text); font-size: 14px; }
.suggestions li::marker { color: var(--ink); font-weight: 700; }
.clickable {
  cursor: pointer;
  user-select: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.fold { font-size: 13px; color: var(--text-secondary); font-weight: 450; }
.qa-item {
  padding: 14px 2px 16px 14px;
  border-left: 2px solid var(--border-soft);
  margin-bottom: 4px;
}
.qa-item p { margin: 0 0 8px; line-height: 1.8; font-size: 14px; color: var(--text); }
.qa-item b { color: var(--ink); font-weight: 650; }
.qa-item .ans.skip { color: var(--text-muted); }
.qa-item .ans { white-space: pre-wrap; }
.ref-box {
  background: var(--bg-soft);
  border: 1px solid var(--border-soft);
  border-radius: 12px;
  padding: 10px 14px;
  font-size: 13.5px;
  line-height: 1.8;
  color: var(--text-secondary);
  white-space: pre-wrap;
}
.ref-box .tag {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  color: var(--success-text);
  background: var(--success-bg);
  border-radius: 999px;
  padding: 2px 10px;
  margin-right: 8px;
  vertical-align: 1px;
}
.ref-item { display: none; }
.crit { margin: 10px 0 4px; padding: 10px 14px; background: var(--bg-soft); border-radius: 12px; font-size: 13.5px; line-height: 1.8; }
.crit p { margin: 0 0 4px; }
.crit p:last-child { margin-bottom: 0; }
.crit .good { color: var(--success); }
.crit .warn { color: #b45309; }
.retrain-btn {
  margin-top: 10px;
  border: 1px solid var(--ink);
  background: transparent;
  color: var(--ink);
  font-size: 13px;
  font-weight: 700;
  padding: 7px 16px;
  border-radius: 999px;
  cursor: pointer;
  transition: var(--transition, all 0.2s);
}
.retrain-btn:hover:not(:disabled) { background: var(--ink); color: #fff; }
.retrain-btn:disabled { opacity: 0.55; cursor: not-allowed; }
.retrain-err { color: var(--danger); font-size: 13px; margin: 0 0 8px; }
@media (max-width: 640px) {
  .two-col { grid-template-columns: 1fr; }
  .score-card { flex-direction: column; align-items: flex-start; }
}
</style>
