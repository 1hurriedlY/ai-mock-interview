<template>
  <div class="industry-view">
    <div class="hero">
      <h1>行业调研</h1>
      <p>输入陌生行业，AI 帮你从 0 到 1 拆解：产业链、头部玩家、商业模式、趋势、岗位技能与面试题。</p>
    </div>

    <div class="research-bar">
      <input
        v-model.trim="industryName"
        placeholder="输入行业名，如：工业软件、储能、SaaS、跨境电商…"
        @keyup.enter="research"
      />
      <button :disabled="loading || !industryName" @click="research">
        {{ loading ? '调研中…' : '开始调研' }}
      </button>
    </div>
    <p v-if="error" class="error">{{ error }}</p>

    <!-- 历史入口：常驻，不依赖是否已生成报告 -->
    <div class="history-bar">
      <button class="link" @click="loadHistory">
        {{ showHistory ? '收起历史 ▲' : '查看调研历史 ▼' }}
      </button>
    </div>

    <!-- 调研报告 -->
    <div v-if="report" class="report">
      <div class="report-header">
        <h2>{{ report.content.industry || industryName }}</h2>
      </div>
      <p class="overview">{{ report.content.overview }}</p>

      <section v-if="report.content.industry_chain?.length">
        <h3>产业链拆解</h3>
        <div class="chain-grid">
          <div v-for="c in report.content.industry_chain" :key="c.name" class="chain-card">
            <strong>{{ c.name }}</strong>
            <p>{{ c.description }}</p>
          </div>
        </div>
      </section>

      <section v-if="report.content.key_players?.length">
        <h3>头部玩家</h3>
        <ul class="player-list">
          <li v-for="p in report.content.key_players" :key="p.name">
            <span class="tag">{{ p.type }}</span>
            <strong>{{ p.name }}</strong>
            <p>{{ p.description }}</p>
          </li>
        </ul>
      </section>

      <section v-if="report.content.business_models?.length">
        <h3>商业模式</h3>
        <ul>
          <li v-for="b in report.content.business_models" :key="b.name">
            <strong>{{ b.name }}</strong> — {{ b.description }}
          </li>
        </ul>
      </section>

      <section v-if="report.content.trends?.length">
        <h3>行业趋势</h3>
        <ul class="trend-list">
          <li v-for="t in report.content.trends" :key="t">{{ t }}</li>
        </ul>
      </section>

      <section v-if="report.content.job_skills?.length">
        <h3>岗位技能要求</h3>
        <ul class="skill-list">
          <li v-for="s in report.content.job_skills" :key="s.skill">
            <span class="tag" :class="s.level === '加分' ? 'bonus' : 'must'">{{ s.level }}</span>
            <strong>{{ s.skill }}</strong>
            <p>{{ s.description }}</p>
          </li>
        </ul>
      </section>

      <section v-if="report.content.interview_questions?.length">
        <h3>面试常见问题</h3>
        <ul class="qa-list">
          <li v-for="q in report.content.interview_questions" :key="q.question">
            <p class="question">Q：{{ q.question }}</p>
            <p class="angle">考察点：{{ q.angle }}</p>
          </li>
        </ul>
      </section>
    </div>

    <!-- 历史列表 -->
    <div v-if="showHistory" class="history">
      <h2>调研历史</h2>
      <p v-if="history.length === 0" class="muted">暂无历史记录</p>
      <ul>
        <li v-for="h in history" :key="h.id">
          <button class="link" @click="openHistory(h.id)">{{ h.industry_name }}</button>
          <span class="muted overview-text">{{ h.overview }}</span>
          <span class="muted">{{ h.created_at }}</span>
          <button class="btn-del" title="删除这份报告" @click="removeHistory(h)">删除</button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { industryApi } from '../api/index.js'

const industryName = ref('')
const loading = ref(false)
const error = ref('')
const report = ref(null)
const showHistory = ref(false)
const history = ref([])

async function research() {
  if (!industryName.value || loading.value) return
  loading.value = true
  error.value = ''
  report.value = null
  try {
    report.value = await industryApi.research(industryName.value)
  } catch (e) {
    error.value = e.response?.data?.detail || '调研失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

async function loadHistory() {
  showHistory.value = !showHistory.value
  if (!showHistory.value) return
  try {
    history.value = await industryApi.history()
  } catch (e) {
    error.value = e.response?.data?.detail || '加载历史失败'
  }
}

async function openHistory(id) {
  try {
    report.value = await industryApi.detail(id)
    showHistory.value = false
  } catch (e) {
    error.value = e.response?.data?.detail || '加载失败'
  }
}

// 删除一份历史报告：二次确认 → 调接口 → 本地移除（正在查看该份则清空）
async function removeHistory(h) {
  if (!window.confirm(`确定删除「${h.industry_name}」(${h.created_at}) 这份调研报告吗？删除后不可恢复。`)) return
  try {
    await industryApi.remove(h.id)
    history.value = history.value.filter((x) => x.id !== h.id)
    if (report.value?.id === h.id) report.value = null
  } catch (e) {
    error.value = e.response?.data?.detail || '删除失败，请重试'
  }
}
</script>

<style scoped>
.industry-view { max-width: 860px; margin: 0 auto; padding: 24px 16px; }
.hero h1 { margin-bottom: 8px; }
.hero p { color: #666; margin-bottom: 20px; }
.research-bar { display: flex; gap: 8px; margin-bottom: 12px; }
.research-bar input { flex: 1; padding: 10px 12px; border: 1px solid #ccc; border-radius: 6px; }
.research-bar button { padding: 10px 20px; background: #2563eb; color: #fff; border: none; border-radius: 6px; cursor: pointer; }
.research-bar button:disabled { opacity: 0.5; cursor: not-allowed; }
.error { color: #dc2626; }
.report { margin-top: 20px; }
.report-header { display: flex; align-items: center; justify-content: space-between; }
.report-header h2 { margin: 0; }
.link { background: none; border: none; color: #2563eb; cursor: pointer; text-decoration: underline; }
.overview { color: #444; line-height: 1.7; }
section { margin-top: 24px; }
section h3 { border-left: 4px solid #2563eb; padding-left: 8px; margin-bottom: 12px; }
.chain-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }
.chain-card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px 12px; background: #f9fafb; }
.player-list, .skill-list { list-style: none; padding: 0; }
.player-list li, .skill-list li { display: flex; align-items: flex-start; gap: 8px; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
.player-list p, .skill-list p { margin: 0; color: #666; flex: 1; }
.tag { font-size: 12px; padding: 2px 8px; border-radius: 10px; background: #e0e7ff; color: #3730a3; white-space: nowrap; }
.tag.must { background: #fee2e2; color: #b91c1c; }
.tag.bonus { background: #dcfce7; color: #166534; }
.trend-list { padding-left: 20px; }
.trend-list li { margin-bottom: 6px; }
.qa-list { list-style: none; padding: 0; }
.qa-list li { padding: 10px; border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 8px; }
.qa-list .question { font-weight: 600; margin: 0 0 4px; }
.qa-list .angle { color: #666; margin: 0; }
.history { margin-top: 32px; }
.history-bar { margin: 4px 0 12px; }
.history li { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
.history li .link { white-space: nowrap; }
.overview-text { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.btn-del {
  border: 1px solid #fecaca; background: #fff; color: #dc2626;
  font-size: 12px; padding: 2px 10px; border-radius: 8px; cursor: pointer;
  opacity: 0; transition: opacity 0.15s; white-space: nowrap;
}
.history li:hover .btn-del { opacity: 1; }
.btn-del:hover { background: #fef2f2; }
.muted { color: #999; }
</style>
