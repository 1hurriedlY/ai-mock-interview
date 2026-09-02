<template>
  <div ref="el" class="radar" :style="{ height: height + 'px' }"></div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent, RadarComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

// 按需注册 echarts 模块（大幅减小 bundle；雷达图只需这些）
echarts.use([RadarChart, TooltipComponent, RadarComponent, CanvasRenderer])

const props = defineProps({
  // { "专业技能": 85, "沟通表达": 80, ... }
  dimensions: { type: Object, default: () => ({}) },
  height: { type: Number, default: 320 },
})

const el = ref(null)
let chart = null

function render() {
  if (!chart) return
  const names = Object.keys(props.dimensions || {})
  const values = names.map((k) => Number(props.dimensions[k]) || 0)
  chart.setOption({
    tooltip: { trigger: 'item' },
    radar: {
      indicator: names.map((name) => ({ name, max: 100 })),
      radius: '65%',
      splitNumber: 4,
      axisName: { color: '#1f2937', fontSize: 13 },
      splitArea: { areaStyle: { color: ['#f8fafc', '#eef2ff'] } },
      splitLine: { lineStyle: { color: '#cbd5e1' } },
      axisLine: { lineStyle: { color: '#cbd5e1' } },
    },
    series: [{
      type: 'radar',
      data: [{ value: values, name: '综合表现' }],
      areaStyle: { color: 'rgba(37, 99, 235, 0.18)' },
      lineStyle: { color: '#2563eb', width: 2 },
      itemStyle: { color: '#2563eb' },
    }],
  })
}

function handleResize() {
  chart?.resize()
}

onMounted(() => {
  chart = echarts.init(el.value)
  render()
  window.addEventListener('resize', handleResize)
})

watch(() => props.dimensions, render, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.radar { width: 100%; }
</style>
