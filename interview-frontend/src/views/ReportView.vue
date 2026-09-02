<template>
  <div class="report-view">
    <div v-if="error && !report" class="card empty">
      <p class="error">{{ error }}</p>
      <router-link class="primary-link" to="/history">回历史页</router-link>
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
        <div v-if="report.match_analysis.strengths?.length" class="two-col">
          <div>
            <h3 class="good">✓ 候选人亮点</h3>
            <ul><li v-for="(s, i) in report.match_analysis.strengths" :key="i">{{ s }}</li></ul>
          </div>
          <div>
            <h3 class="warn">△ 待加强</h3>
            <ul><li v-for="(g, i) in report.match_analysis.gaps" :key="i">{{ g }}</li></ul>
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

      <!-- 参考要点（可折叠） -->
      <section class="card" v-if="referenceMsgs.length">
        <h2 class="clickable" @click="showRef = !showRef">
          面试参考要点（{{ referenceMsgs.length }} 题）
          <span class="fold">{{ showRef ? '收起 ▲' : '展开 ▼' }}</span>
        </h2>
        <div v-if="showRef">
          <div v-for="m in referenceMsgs" :key="m.index" class="ref-item">
            <p class="q">{{ m.q }}</p>
            <pre class="ref-text">{{ m.ref }}</pre>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { downloadReport, exportApi, historyApi } from '../api'
import ScoreRadar from '../components/ScoreRadar.vue'
import ExpressionChart from '../components/ExpressionChart.vue'

const route = useRoute()
const report = ref(null)
const error = ref('')
const showRef = ref(false)
const exportMsg = ref('')
const references = ref([])
const jobTitle = ref('')

const hasDim = computed(() => Object.keys(report.value?.dimensions || {}).length > 0)

// 表情数据源：历史报告无表情时间轴时用空序列（不报错也不渲染空图）
const exprData = computed(() => {
  const ea = report.value?.expression_analysis || {}
  const seq = Array.isArray(ea.timeline) ? ea.timeline
    : (Array.isArray(ea.sequence) ? ea.sequence : [])
  const has = Boolean(report.value && (ea.comment || ea.highlights?.length || seq.length))
  return { has, sequence: seq }
})

const referenceMsgs = computed(() => references.value.filter((m) => m.q && m.ref))

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
    references.value = detail.messages
      .filter((m) => m.role === 'assistant' && m.reference)
      .map((m) => ({ q: m.content.slice(0, 60), ref: m.reference }))
    report.value = detail.report
    if (!report.value) {
      error.value = '该会话还没有评分报告，请先在面试中结束面试。'
    }
  } catch (e) {
    error.value = e.response?.data?.detail || '加载报告失败'
  }
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
    alert(e.response?.data?.detail || '导出失败，请稍后重试')
  }
}
</script>

<style scoped>
.report-view { max-width: 860px; margin: 0 auto; padding: 24px 16px 48px; }
.report-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 10px; }
.report-header h1 { color: var(--primary); font-size: 22px; }
.actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.btn-docx, .btn-pdf {
  border: none; color: #fff; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px;
}
.btn-docx { background: #2563eb; }
.btn-pdf { background: #dc2626; }
.ghost-link {
  color: var(--text-secondary); text-decoration: none; border: 1px solid var(--border);
  padding: 7px 14px; border-radius: 8px; font-size: 13px;
}
.export-msg { color: #059669; font-size: 13px; margin-bottom: 12px; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 16px; }
.empty { text-align: center; padding: 40px; }
.error { color: #dc2626; }
.primary-link {
  display: inline-block; margin-top: 10px; color: var(--primary); text-decoration: none;
}
.score-card { display: flex; gap: 20px; align-items: center; }
.score-num { font-size: 56px; font-weight: 700; min-width: 160px; text-align: center; }
.score-num span { font-size: 18px; color: var(--text-secondary); font-weight: 400; }
.score-good { color: #059669; }
.score-mid { color: #d97706; }
.score-low { color: #dc2626; }
.score-right h3 { margin-bottom: 8px; }
.summary { color: var(--text); line-height: 1.8; }
.reason { line-height: 1.8; color: var(--text); }
h2 { font-size: 17px; margin-bottom: 14px; }
h2 .level { color: var(--primary); }
h3 { font-size: 14px; margin-bottom: 8px; }
h3.good { color: #059669; }
h3.warn { color: #d97706; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 12px; }
.two-col ul, .suggestions, .plain-list { padding-left: 20px; }
.two-col li, .suggestions li, .plain-list li { margin-bottom: 6px; line-height: 1.7; }
.suggestions li::marker { color: var(--primary); font-weight: 600; }
.clickable { cursor: pointer; user-select: none; display: flex; justify-content: space-between; align-items: center; }
.fold { font-size: 13px; color: var(--text-secondary); font-weight: 400; }
.ref-item { border-left: 3px solid var(--border); padding: 6px 12px; margin-bottom: 12px; }
.ref-item .q { font-weight: 600; margin-bottom: 6px; }
.ref-text {
  white-space: pre-wrap; font-family: inherit; font-size: 13px; color: var(--text-secondary);
  line-height: 1.7; margin: 0;
}
@media (max-width: 640px) { .two-col { grid-template-columns: 1fr; } }
</style>
