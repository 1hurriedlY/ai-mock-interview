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
.industry-view { max-width: 900px; margin: 0 auto; padding: 24px 24px 56px; }
.hero h1 {
  font-size: 22px;
  font-weight: 740;
  letter-spacing: -0.012em;
  color: var(--ink);
}
.hero p { color: var(--text-secondary); font-size: 14px; margin: 6px 0 16px; }

/* 调研输入行：胶囊主按钮 + 大圆角输入 */
.research-bar { display: flex; gap: 10px; margin-bottom: 14px; }
.research-bar input {
  flex: 1;
  height: 46px;
  padding: 0 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-chip);
  background: var(--card);
  font-size: 14px;
  transition: var(--transition);
}
.research-bar input:focus {
  outline: none;
  border-color: var(--ink);
  box-shadow: var(--ring);
}
.research-bar input::placeholder { color: var(--text-muted); }
.research-bar button {
  height: 46px;
  padding: 0 24px;
  background: var(--ink);
  color: #fff;
  border: none;
  border-radius: var(--radius-chip);
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: var(--transition);
  white-space: nowrap;
}
.research-bar button:hover:not(:disabled) {
  background: var(--ink-hover);
  box-shadow: 0 8px 20px rgba(15, 17, 21, 0.18);
}
.research-bar button:active:not(:disabled) { transform: scale(0.98); }
.research-bar button:disabled { opacity: 0.5; cursor: not-allowed; }

.history-bar { margin: 14px 0 6px; }
.error { color: var(--danger); margin: 10px 0 0; font-size: 14px; }
.muted { color: var(--text-secondary); font-size: 13px; }
.link {
  background: none;
  border: none;
  color: var(--ink);
  cursor: pointer;
  font-size: 13.5px;
  padding: 0;
  font-weight: 600;
}
.link:hover { text-decoration: underline; }

.report { margin-top: 24px; }
.report-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.report-header h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 760;
  letter-spacing: -0.012em;
  color: var(--ink);
}
.overview { color: var(--text-secondary); line-height: 1.85; margin-top: 10px; font-size: 14px; }

/* 区块标题：靠字字重分层 */
section { margin-top: 28px; }
section h3 {
  font-size: 15.5px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 14px;
  letter-spacing: -0.005em;
}

.chain-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.chain-card {
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-card);
  padding: 14px 16px;
  background: var(--bg-soft);
  transition: var(--transition);
}
.chain-card:hover {
  border-color: var(--border);
  box-shadow: var(--shadow-sm);
}
.chain-card strong { font-size: 14px; color: var(--ink); }
.chain-card p {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-secondary);
}

.player-list, .skill-list { list-style: none; padding: 0; }
.player-list li, .skill-list li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 13px 2px;
  border-bottom: 1px solid var(--border-soft);
}
.player-list li:last-child, .skill-list li:last-child { border-bottom: none; }
.player-list li strong, .skill-list li strong {
  font-size: 14px;
  color: var(--ink);
  min-width: 64px;
}
.player-list p, .skill-list p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13.5px;
  flex: 1;
  line-height: 1.7;
}

.tag {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: var(--radius-chip);
  white-space: nowrap;
  font-weight: 600;
}
.tag.must { background: var(--danger-bg); color: var(--danger-text); }
.tag.bonus { background: var(--success-bg); color: var(--success-text); }

.trend-list { padding-left: 0; list-style: none; }
.trend-list li {
  position: relative;
  padding: 4px 0 4px 18px;
  color: var(--text);
  font-size: 14px;
  line-height: 1.7;
}
.trend-list li::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 13px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--ink);
  opacity: 0.4;
}

.qa-list { list-style: none; padding: 0; }
.qa-list li {
  padding: 14px 16px;
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-card);
  margin-bottom: 8px;
  background: var(--card);
}
.qa-list .question { font-weight: 600; margin: 0 0 4px; color: var(--ink); font-size: 14px; }
.qa-list .angle { color: var(--text-secondary); margin: 0; font-size: 13.5px; }

/* 历史 */
.history { margin-top: 36px; }
.history > h2 {
  font-size: 18px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 10px;
}
.history > ul { list-style: none; padding: 0; }
.history li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 4px;
  border-bottom: 1px solid var(--border-soft);
  transition: var(--transition);
}
.history li:last-child { border-bottom: none; }
.history li:hover { background: var(--bg-soft); }
.history li .link { white-space: nowrap; font-size: 14px; }
.overview-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
}
.btn-del {
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--danger);
  font-size: 12px;
  padding: 4px 12px;
  border-radius: var(--radius-chip);
  cursor: pointer;
  opacity: 0;
  transition: var(--transition);
  white-space: nowrap;
}
.history li:hover .btn-del { opacity: 1; }
.btn-del:hover { background: var(--danger-bg); border-color: var(--danger); }
</style>
