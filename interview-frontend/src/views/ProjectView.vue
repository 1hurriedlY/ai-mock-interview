<template>
  <div class="project-view">
    <div class="hero">
      <h1>求职渠道 &amp; 讲项目话术</h1>
      <p>想知道去哪找工作/接单？想把项目讲得面试官爱听？两个入口直接生成。</p>
    </div>

    <div class="tabs">
      <button :class="{ active: tab === 'channels' }" @click="switchTab('channels')">渠道清单</button>
      <button :class="{ active: tab === 'script' }" @click="switchTab('script')">讲项目话术</button>
      <button :class="{ active: tab === 'history' }" @click="switchTab('history')">历史</button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <!-- 渠道清单 -->
    <div v-if="tab === 'channels'" class="panel">
      <button :disabled="loading" @click="genChannels">
        {{ loading ? '生成中…' : '生成渠道平台清单' }}
      </button>
      <p v-if="channels.summary" class="overview">{{ channels.summary }}</p>
      <section v-for="cat in channels.categories" :key="cat.category">
        <h3>{{ cat.category }}</h3>
        <ul class="item-list">
          <li v-for="item in cat.items" :key="item.name">
            <div class="item-head">
              <strong>{{ item.name }}</strong>
              <span class="tag" :class="item.free ? 'free' : 'paid'">
                {{ item.free ? '免费' : '付费' }}
              </span>
              <span class="tag suitable">{{ item.suitable }}</span>
            </div>
            <p>{{ item.description }}</p>
          </li>
        </ul>
      </section>
    </div>

    <!-- 讲项目话术 -->
    <div v-if="tab === 'script'" class="panel">
      <div class="form-row">
        <input v-model.trim="projectName" placeholder="项目名称，如：支付网关系统" />
      </div>
      <div class="form-row">
        <textarea
          v-model="projectDesc"
          rows="3"
          placeholder="项目描述（可选）：技术栈、你负责的部分、成果…"
        ></textarea>
      </div>
      <button :disabled="loading || !projectName" @click="genScript">
        {{ loading ? '生成中…' : '生成 STAR 讲项目话术' }}
      </button>

      <div v-if="script?.content" class="script-result">
        <h2>{{ script.content.project_name }}</h2>
        <p class="overview">{{ script.content.summary }}</p>

        <section>
          <h3>STAR 拆解</h3>
          <div class="star-grid">
            <div class="star-card"><strong>S 背景</strong><p>{{ script.content.star.situation }}</p></div>
            <div class="star-card"><strong>T 任务</strong><p>{{ script.content.star.task }}</p></div>
            <div class="star-card"><strong>A 行动</strong><p>{{ script.content.star.action }}</p></div>
            <div class="star-card"><strong>R 结果</strong><p>{{ script.content.star.result }}</p></div>
          </div>
        </section>

        <section v-if="script.content.deep_dive?.length">
          <h3>深挖追问应对</h3>
          <ul class="qa-list">
            <li v-for="d in script.content.deep_dive" :key="d.question">
              <p class="q">Q：{{ d.question }}</p>
              <p class="a">A：{{ d.answer }}</p>
            </li>
          </ul>
        </section>

        <section v-if="script.content.pitfalls?.length">
          <h3>踩坑复盘</h3>
          <ul class="qa-list">
            <li v-for="p in script.content.pitfalls" :key="p.issue">
              <p class="q">坑：{{ p.issue }}</p>
              <p class="a">复盘：{{ p.lesson }}</p>
            </li>
          </ul>
        </section>

        <section v-if="script.content.script">
          <h3>完整话术（3 分钟可背）</h3>
          <pre class="script-box">{{ script.content.script }}</pre>
        </section>
      </div>
    </div>

    <!-- 历史 -->
    <div v-if="tab === 'history'" class="panel">
      <p v-if="history.length === 0" class="muted">暂无历史记录</p>
      <ul class="history-list">
        <li v-for="h in history" :key="h.id">
          <button class="link" @click="openHistory(h.id)">
            {{ h.type === 'script' ? '📝 ' + (h.project_name || '话术') : '🗂️ 渠道清单' }}
          </button>
          <span class="muted">{{ h.summary }}</span>
          <span class="muted">{{ h.created_at }}</span>
          <button class="btn-del" title="删除这条记录" @click="removeHistory(h)">删除</button>
        </li>
      </ul>

      <div v-if="historyDetail" class="history-detail">
        <button class="link" @click="historyDetail = null">← 返回</button>
        <template v-if="historyDetail.type === 'channels'">
          <h2>渠道平台清单</h2>
          <p class="overview">{{ historyDetail.content.summary }}</p>
          <section v-for="cat in historyDetail.content.categories" :key="cat.category">
            <h3>{{ cat.category }}</h3>
            <ul class="item-list">
              <li v-for="item in cat.items" :key="item.name">
                <div class="item-head">
                  <strong>{{ item.name }}</strong>
                  <span class="tag" :class="item.free ? 'free' : 'paid'">{{ item.free ? '免费' : '付费' }}</span>
                  <span class="tag suitable">{{ item.suitable }}</span>
                </div>
                <p>{{ item.description }}</p>
              </li>
            </ul>
          </section>
        </template>
        <template v-else>
          <h2>{{ historyDetail.content.project_name }}</h2>
          <p class="overview">{{ historyDetail.content.summary }}</p>
          <section>
            <h3>STAR 拆解</h3>
            <div class="star-grid">
              <div class="star-card"><strong>S 背景</strong><p>{{ historyDetail.content.star.situation }}</p></div>
              <div class="star-card"><strong>T 任务</strong><p>{{ historyDetail.content.star.task }}</p></div>
              <div class="star-card"><strong>A 行动</strong><p>{{ historyDetail.content.star.action }}</p></div>
              <div class="star-card"><strong>R 结果</strong><p>{{ historyDetail.content.star.result }}</p></div>
            </div>
          </section>
          <section v-if="historyDetail.content.script">
            <h3>完整话术</h3>
            <pre class="script-box">{{ historyDetail.content.script }}</pre>
          </section>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { projectApi } from '../api/index.js'

const tab = ref('channels')
const loading = ref(false)
const error = ref('')

const channels = ref({ summary: '', categories: [] })
const projectName = ref('')
const projectDesc = ref('')
const script = ref(null)

const history = ref([])
const historyDetail = ref(null)

function switchTab(t) {
  tab.value = t
  error.value = ''
  if (t === 'history') loadHistory()
}

async function genChannels() {
  loading.value = true
  error.value = ''
  try {
    channels.value = await projectApi.channels()
  } catch (e) {
    error.value = e.response?.data?.detail || '生成失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

async function genScript() {
  if (!projectName.value || loading.value) return
  loading.value = true
  error.value = ''
  script.value = null
  try {
    script.value = await projectApi.script(projectName.value, projectDesc.value)
  } catch (e) {
    error.value = e.response?.data?.detail || '生成失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

async function loadHistory() {
  try {
    history.value = await projectApi.history()
  } catch (e) {
    error.value = e.response?.data?.detail || '加载历史失败'
  }
}

async function openHistory(id) {
  try {
    historyDetail.value = await projectApi.detail(id)
  } catch (e) {
    error.value = e.response?.data?.detail || '加载失败'
  }
}

// 删除一条历史记录：二次确认 → 调接口 → 本地移除（正在查看该条则返回列表）
async function removeHistory(h) {
  const name = h.type === 'script' ? `话术「${h.project_name || '未命名'}」` : '渠道清单'
  if (!window.confirm(`确定删除这条${name}记录吗（${h.created_at}）？删除后不可恢复。`)) return
  try {
    await projectApi.remove(h.id)
    history.value = history.value.filter((x) => x.id !== h.id)
    if (historyDetail.value?.id === h.id) historyDetail.value = null
  } catch (e) {
    error.value = e.response?.data?.detail || '删除失败，请重试'
  }
}
</script>

<style scoped>
.project-view { max-width: 900px; margin: 0 auto; padding: 24px 24px 56px; }
.hero h1 {
  font-size: 22px;
  font-weight: 740;
  letter-spacing: -0.012em;
  color: var(--ink);
}
.hero p { color: var(--text-secondary); font-size: 14px; margin: 6px 0 16px; }

/* Tab：胶囊分组式选择 */
.tabs {
  display: inline-flex;
  gap: 4px;
  background: var(--bg-soft);
  padding: 4px;
  border-radius: var(--radius-chip);
  margin: 4px 0 4px;
}
.tabs button {
  padding: 7px 18px;
  border: none;
  background: transparent;
  border-radius: var(--radius-chip);
  cursor: pointer;
  font-size: 13.5px;
  color: var(--text-secondary);
  font-weight: 550;
  transition: var(--transition);
}
.tabs button:hover { color: var(--ink); }
.tabs button.active {
  background: var(--card);
  color: var(--ink);
  font-weight: 600;
  box-shadow: var(--shadow-sm);
}

.error { color: var(--danger); margin: 12px 0; font-size: 14px; }
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

.panel button {
  height: 44px;
  padding: 0 22px;
  background: var(--ink);
  color: #fff;
  border: none;
  border-radius: var(--radius-chip);
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: var(--transition);
}
.panel button:hover:not(:disabled) {
  background: var(--ink-hover);
  box-shadow: 0 8px 20px rgba(15, 17, 21, 0.18);
}
.panel button:active:not(:disabled) { transform: scale(0.98); }
.panel button:disabled { opacity: 0.5; cursor: not-allowed; }

.overview { color: var(--text); margin: 14px 0; line-height: 1.85; font-size: 14.5px; }
section { margin-top: 28px; }
section h3 {
  font-size: 15.5px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 14px;
  letter-spacing: -0.005em;
}

.form-row { margin-bottom: 12px; }
.form-row input, .form-row textarea {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-input);
  background: var(--bg-soft);
  font-family: inherit;
  font-size: 14px;
  transition: var(--transition);
}
.form-row input:focus, .form-row textarea:focus {
  outline: none;
  border-color: var(--ink);
  background: var(--card);
  box-shadow: var(--ring);
}
.form-row input::placeholder, .form-row textarea::placeholder { color: var(--text-muted); }

.script-result { margin-top: 28px; }
.script-result > h2 {
  font-size: 20px;
  font-weight: 720;
  color: var(--ink);
}
.star-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.star-card {
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-card);
  padding: 15px 16px;
  background: var(--bg-soft);
  transition: var(--transition);
}
.star-card:hover { border-color: var(--border); box-shadow: var(--shadow-sm); }
.star-card strong {
  display: block;
  margin-bottom: 8px;
  color: var(--ink);
  font-size: 13.5px;
  letter-spacing: 0.02em;
}
.star-card p { color: var(--text); margin: 0; font-size: 13.5px; line-height: 1.75; }

.item-list { list-style: none; padding: 0; }
.item-list li {
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-card);
  padding: 14px 16px;
  margin-bottom: 10px;
  background: var(--card);
  transition: var(--transition);
}
.item-list li:hover { border-color: var(--border); box-shadow: var(--shadow-sm); }
.item-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}
.item-head strong { font-size: 14.5px; color: var(--ink); }
.item-list p { color: var(--text-secondary); font-size: 13.5px; line-height: 1.7; margin: 0; }

.tag {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: var(--radius-chip);
  white-space: nowrap;
  font-weight: 600;
}
.tag.free { background: var(--success-bg); color: var(--success-text); }
.tag.paid { background: var(--warning-bg); color: var(--warning-text); }
.tag.suitable { background: var(--ink-soft); color: var(--ink); }

.qa-list { list-style: none; padding: 0; }
.qa-list li {
  padding: 13px 2px;
  border-bottom: 1px solid var(--border-soft);
}
.qa-list li:last-child { border-bottom: none; }
.qa-list .q { font-weight: 600; margin: 0 0 5px; color: var(--ink); font-size: 14px; }
.qa-list .a { color: var(--text-secondary); margin: 0; font-size: 13.5px; line-height: 1.75; }

.script-box {
  background: var(--bg-soft);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-card);
  padding: 18px 20px;
  white-space: pre-wrap;
  font-family: inherit;
  line-height: 1.85;
  color: var(--text);
  font-size: 14px;
}

.history-list { list-style: none; padding: 0; margin: 8px 0 0; }
.history-list li {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 4px;
  border-bottom: 1px solid var(--border-soft);
  transition: var(--transition);
}
.history-list li:last-child { border-bottom: none; }
.history-list li:hover { background: var(--bg-soft); }
.history-list .muted {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
}
.history-list li:hover .btn-del { opacity: 1; }
.btn-del:hover { background: var(--danger-bg); border-color: var(--danger); }
.history-detail { margin-top: 24px; }
</style>
