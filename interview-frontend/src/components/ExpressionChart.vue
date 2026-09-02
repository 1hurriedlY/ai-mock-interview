<template>
  <div class="expression-chart">
    <!-- ① 表情时间轴（echarts 堆叠面积图，x 秒 / y 累计次数） -->
    <div ref="chartEl" class="chart" :class="{ 'is-hidden': !chartReady }"></div>
    <p v-if="chartReady === false" class="empty">本次面试未采集到表情数据（未开摄像头或未识别到人脸）。</p>

    <!-- ② 表情频次条形（未开摄像头时给简短说明） -->
    <div v-if="hasCounts" class="bars">
      <div v-for="b in counts" :key="b.label" class="bar-row">
        <span class="bar-label">{{ b.label }}</span>
        <div class="bar-track">
          <div class="bar-fill" :style="{ width: b.pct + '%' }"></div>
        </div>
        <span class="bar-num">{{ b.n }}</span>
      </div>
    </div>
    <p v-if="!hasCounts" class="empty">无表情频次数据。</p>

    <!-- ③ 表情点评（评分 Agent 结合时间轴生成的文字点评） -->
    <p v-if="comment" class="comment">{{ comment }}</p>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([LineChart, BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps({
  sequence: { type: Array, default: () => [] }, // [{ time, expression, confidence }]
  comment: { type: String, default: '' },       // 大模型表情点评文字
})

const chartEl = ref(null)
let chart = null
const chartReady = ref(false) // undefined=初始化中 false=无可绘图 true=已渲染
const ready = ref(false)      // dom 挂载完成

const CN = {
  neutral: '平静', happy: '开心', sad: '难过', angry: '生气',
  fearful: '紧张', disgusted: '厌恶', surprised: '惊讶',
}

// 过滤 no_face 断点；无有效数据的序列直接判空
const validSeq = computed(() => (props.sequence || []).filter((s) => s.expression && s.expression !== 'no_face'))
const hasData = computed(() => validSeq.value.length > 0)

// 各表情累计次数 → 频次条形
const counts = computed(() => {
  const m = {}
  for (const s of validSeq.value) m[s.expression] = (m[s.expression] || 0) + 1
  return Object.entries(m)
    .map(([k, n]) => ({ label: CN[k] || k, n }))
    .sort((a, b) => b.n - a.n)
})
const hasCounts = computed(() => counts.value.length > 0)

// 表情时间轴：x=秒，y=各类别在该秒内的累计次数（堆叠曲线近似"占比走势"）
function buildSeries() {
  const timeBuckets = new Map() // second -> { expr: count }
  let maxT = 0
  for (const s of validSeq.value) {
    const t = Math.round(s.time)
    maxT = Math.max(maxT, t)
    if (!timeBuckets.has(t)) timeBuckets.set(t, {})
    const b = timeBuckets.get(t)
    b[s.expression] = (b[s.expression] || 0) + 1
  }
  const cats = Array.from(new Set(validSeq.value.map((s) => s.expression)))
  const seconds = Array.from({ length: maxT + 1 }, (_, i) => i)
  const series = cats.map((c) => ({
    name: CN[c] || c,
    type: 'line',
    stack: 'total',
    smooth: true,
    showSymbol: false,
    lineStyle: { width: 1.2 },
    areaStyle: { opacity: 0.7 },
    emphasis: { focus: 'series' },
    data: seconds.map((t) => (timeBuckets.get(t)?.[c] || 0)),
  }))
  return { seconds, series }
}

function renderChart() {
  if (!chartEl.value || !ready.value) return
  if (!hasData.value) {
    chartReady.value = false
    return
  }
  chartReady.value = true
  if (!chart) chart = echarts.init(chartEl.value)
  const { seconds, series } = buildSeries()
  chart.setOption({
    animation: false,
    color: ['#fbbf24', '#f472b6', '#60a5fa', '#a78bfa', '#34d399', '#f87171', '#94a3b8'],
    grid: { left: 8, right: 12, top: 26, bottom: 8, containLabel: true },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: seconds,
      name: '秒',
      nameTextStyle: { fontSize: 11, color: '#9ca3af' },
      axisLine: { lineStyle: { color: '#d1d5db' } },
      axisLabel: { fontSize: 10, color: '#9ca3af' },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      name: '表情数',
      nameTextStyle: { fontSize: 11, color: '#9ca3af' },
      axisLabel: { fontSize: 10, color: '#9ca3af' },
      splitLine: { lineStyle: { color: '#f3f4f6' } },
    },
    series,
  }, true)
  // 容器刚从 display:none 变为可见时 init 可能拿到 0 宽，下一帧补一次 resize
  nextTick(() => chart?.resize())
}

function handleResize() {
  chart?.resize()
}

onMounted(() => {
  ready.value = true
  renderChart()
  window.addEventListener('resize', handleResize)
})
// 序列更新时重绘（renderChart 内部处理空数据→隐藏、可见后补 resize）
watch(() => props.sequence, renderChart, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (chart) { chart.dispose(); chart = null }
})
</script>

<style scoped>
.expression-chart { width: 100%; }
.chart { width: 100%; height: 220px; }
.chart.is-hidden { display: none; }
.empty { color: var(--text-secondary); font-size: 13px; padding: 8px 0; }
.bars { margin-top: 10px; display: flex; flex-direction: column; gap: 5px; }
.bar-row { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.bar-label { width: 40px; color: var(--text-secondary); text-align: right; flex-shrink: 0; }
.bar-track { flex: 1; height: 10px; background: #f3f4f6; border-radius: 5px; overflow: hidden; }
.bar-fill { height: 100%; background: var(--primary); border-radius: 5px; opacity: 0.85; }
.bar-num { width: 24px; color: var(--text); }
.comment { margin-top: 12px; font-size: 13px; line-height: 1.8; color: var(--text); background: #f9fafb; padding: 10px 12px; border-radius: 8px; border-left: 3px solid var(--primary); }
</style>
