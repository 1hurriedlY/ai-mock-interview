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
.project-view { max-width: 860px; margin: 0 auto; padding: 24px 16px; }
.hero h1 { margin-bottom: 8px; }
.hero p { color: #666; margin-bottom: 20px; }
.tabs { display: flex; gap: 8px; margin-bottom: 20px; }
.tabs button {
  padding: 8px 16px; border: 1px solid #ccc; background: #fff; border-radius: 6px;
  cursor: pointer; font-size: 14px;
}
.tabs button.active { background: #2563eb; color: #fff; border-color: #2563eb; }
.error { color: #dc2626; margin-bottom: 12px; }
.panel button {
  padding: 10px 20px; background: #2563eb; color: #fff; border: none; border-radius: 6px;
  cursor: pointer;
}
.panel button:disabled { opacity: 0.5; cursor: not-allowed; }
.overview { color: #444; margin: 12px 0; line-height: 1.7; }
section { margin-top: 24px; }
section h3 { border-left: 4px solid #2563eb; padding-left: 8px; margin-bottom: 12px; }
.item-list { list-style: none; padding: 0; }
.item-list li { border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; background: #f9fafb; }
.item-head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; flex-wrap: wrap; }
.item-head p { margin: 0; color: #666; }
.item-list p { color: #666; }
.tag { font-size: 12px; padding: 2px 8px; border-radius: 10px; white-space: nowrap; }
.tag.free { background: #dcfce7; color: #166534; }
.tag.paid { background: #fef9c3; color: #a16207; }
.tag.suitable { background: #e0e7ff; color: #3730a3; }
.form-row { margin-bottom: 10px; }
.form-row input, .form-row textarea {
  width: 100%; padding: 10px 12px; border: 1px solid #ccc; border-radius: 6px;
  font-family: inherit; font-size: 14px;
}
.script-result { margin-top: 24px; }
.star-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; }
.star-card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; background: #f9fafb; }
.star-card strong { display: block; margin-bottom: 6px; color: #2563eb; }
.star-card p { color: #444; margin: 0; }
.qa-list { list-style: none; padding: 0; }
.qa-list li { border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; }
.qa-list .q { font-weight: 600; margin: 0 0 4px; }
.qa-list .a { color: #666; margin: 0; }
.script-box {
  background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px;
  white-space: pre-wrap; font-family: inherit; line-height: 1.8; color: #333;
}
.history-list { list-style: none; padding: 0; }
.history-list li { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
.history-list .muted { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.link { background: none; border: none; color: #2563eb; cursor: pointer; text-decoration: underline; }
.btn-del {
  border: 1px solid #fecaca; background: #fff; color: #dc2626;
  font-size: 12px; padding: 2px 10px; border-radius: 8px; cursor: pointer;
  opacity: 0; transition: opacity 0.15s;
}
.history-list li:hover .btn-del { opacity: 1; }
.btn-del:hover { background: #fef2f2; }
.muted { color: #999; }
.history-detail { margin-top: 20px; }
</style>
