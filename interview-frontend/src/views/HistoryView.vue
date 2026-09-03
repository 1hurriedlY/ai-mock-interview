<template>
  <div class="history-view">
    <div class="hero">
      <h1>面试历史</h1>
      <p>回看每一场模拟面试的对话与评分报告。</p>
    </div>

    <div class="layout">
      <!-- 会话列表 -->
      <div class="card list-col">
        <p v-if="loading" class="muted">加载中…</p>
        <p v-else-if="sessions.length === 0" class="muted">还没有面试记录，去首页开始第一场吧。</p>
        <ul v-else class="session-list">
          <li
            v-for="s in sessions"
            :key="s.id"
            :class="['session-item', { active: currentId === s.id }]"
            @click="openSession(s.id)"
          >
            <div class="session-head">
              <strong>{{ s.job_title }}</strong>
              <span class="tag">{{ s.interviewer_name }}</span>
              <span v-if="s.report" class="score" :class="scoreClass(s.report.overall_score)">
                {{ s.report.overall_score }} 分
              </span>
              <button
                class="btn-del"
                title="删除这条历史记录"
                @click.stop="removeSession(s)"
              >删除</button>
            </div>
            <div class="session-meta">
              <span>{{ s.status === 'completed' ? '已结束' : '未完成' }}</span>
              <span>{{ s.created_at }}</span>
              <span>{{ s.message_count }} 条消息</span>
            </div>
          </li>
        </ul>
      </div>

      <!-- 详情 -->
      <div class="card detail-col">
        <p v-if="!detail" class="muted">选择左侧一场面试查看详情</p>

        <template v-if="detail">
          <div class="detail-head">
            <h2>{{ detail.job_title }}</h2>
            <router-link
              v-if="detail.report"
              class="btn-report"
              :to="{ name: 'report', params: { id: detail.id } }"
            >查看报告</router-link>
            <span v-else class="tag warn">未生成报告</span>
          </div>
          <p class="meta-line">
            {{ detail.interviewer_name }} · {{ detail.created_at }} · {{ detail.message_count }} 条消息
          </p>

          <div class="msgs">
            <div v-for="m in detail.messages" :key="m.id" class="msg" :class="m.role === 'user' ? 'right' : 'left'">
              <div class="bubble">
                {{ m.content }}
                <div v-if="m.role === 'assistant' && m.reference" class="ref">
                  <span class="ref-label">参考要点</span>
                  <pre>{{ m.reference }}</pre>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { historyApi } from '../api'

const sessions = ref([])
const detail = ref(null)
const currentId = ref(null)
const loading = ref(false)
const error = ref('')

function scoreClass(score) {
  if (score >= 85) return 'score-good'
  if (score >= 70) return 'score-mid'
  return 'score-low'
}

onMounted(loadSessions)

async function loadSessions() {
  loading.value = true
  error.value = ''
  try {
    sessions.value = await historyApi.list()
  } catch (e) {
    error.value = e.response?.data?.detail || '加载历史失败'
  } finally {
    loading.value = false
  }
}

async function openSession(id) {
  currentId.value = id
  detail.value = null
  try {
    detail.value = await historyApi.detail(id)
  } catch (e) {
    error.value = e.response?.data?.detail || '加载详情失败'
  }
}

// 删除一条历史记录：二次确认 → 调接口 → 本地移除（是当前查看项则清空详情）
async function removeSession(s) {
  if (!window.confirm(`确定删除「${s.job_title}」(${s.created_at}) 这条面试记录吗？\n删除后对话与评分报告不可恢复。`)) return
  try {
    await historyApi.remove(s.id)
    sessions.value = sessions.value.filter((x) => x.id !== s.id)
    if (currentId.value === s.id) {
      currentId.value = null
      detail.value = null
    }
  } catch (e) {
    error.value = e.response?.data?.detail || '删除失败，请重试'
  }
}
</script>

<style scoped>
.history-view { max-width: 1100px; margin: 0 auto; padding: 24px 24px 56px; }
.hero h1 {
  font-size: 22px;
  font-weight: 740;
  letter-spacing: -0.012em;
  color: var(--ink);
  margin-bottom: 4px;
}
.hero p { color: var(--text-secondary); font-size: 14px; margin: 4px 0 16px; }
.layout { display: grid; grid-template-columns: 340px 1fr; gap: 16px; align-items: start; }
.card {
  background: var(--card);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-sm);
  padding: 18px 20px;
}
.muted { color: var(--text-secondary); font-size: 13px; }
.error { color: var(--danger); }
.session-list { list-style: none; margin: 0; padding: 0; max-height: 72vh; overflow-y: auto; }
.session-item {
  padding: 13px 14px;
  border-radius: 14px;
  cursor: pointer;
  margin-bottom: 4px;
  border: 1px solid transparent;
  transition: var(--transition);
}
.session-item:hover { background: var(--bg-soft); }
.session-item.active {
  background: var(--ink-soft);
  border-color: var(--ink);
}
.session-item.active .session-head strong { color: var(--ink); }
.btn-del {
  margin-left: auto;
  border: 1px solid transparent;
  background: none;
  color: var(--danger);
  font-size: 11.5px;
  padding: 3px 10px;
  border-radius: var(--radius-chip);
  cursor: pointer;
  opacity: 0;
  transition: var(--transition);
}
.session-item:hover .btn-del { opacity: 1; }
.btn-del:hover { background: var(--danger-bg); }
.session-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.session-head strong { font-size: 14px; color: var(--ink); }
.tag {
  font-size: 11px;
  padding: 2px 10px;
  border-radius: var(--radius-chip);
  background: var(--ink-soft);
  color: var(--ink);
  font-weight: 600;
}
.tag.warn { background: var(--warning-bg); color: var(--warning-text); }
.score { font-size: 12.5px; font-weight: 650; }
.score-good { color: var(--success); }
.score-mid { color: var(--warning); }
.score-low { color: var(--danger); }
.session-meta {
  display: flex;
  gap: 10px;
  color: var(--text-secondary);
  font-size: 11.5px;
  margin-top: 6px;
  flex-wrap: wrap;
}
.detail-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}
.detail-head h2 {
  font-size: 20px;
  font-weight: 760;
  letter-spacing: -0.01em;
  color: var(--ink);
}
.btn-report {
  background: var(--ink);
  color: #fff;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  padding: 0 18px;
  height: 38px;
  border-radius: var(--radius-chip);
  font-size: 13.5px;
  font-weight: 600;
  transition: var(--transition);
}
.btn-report:hover {
  background: var(--ink-hover);
  box-shadow: 0 8px 20px rgba(15, 17, 21, 0.18);
}
.meta-line { color: var(--text-secondary); font-size: 12.5px; margin: 10px 0 16px; }
.msgs { max-height: 66vh; overflow-y: auto; }
.msg { display: flex; margin-bottom: 12px; }
.msg.right { justify-content: flex-end; }
.bubble {
  max-width: 92%;
  background: var(--ink-soft);
  padding: 11px 16px;
  border-radius: 18px;
  white-space: pre-wrap;
  line-height: 1.75;
  font-size: 14px;
  color: var(--text);
}
.msg.right .bubble {
  background: var(--ink);
  color: #fff;
  border-bottom-right-radius: 6px;
}
.msg:not(.right) .bubble { border-bottom-left-radius: 6px; }
.ref { margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--border-soft); }
.ref-label {
  font-size: 11px;
  font-weight: 600;
  background: var(--ink-soft);
  color: var(--ink);
  padding: 1px 8px;
  border-radius: var(--radius-chip);
}
.ref pre {
  margin: 8px 0 0;
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.75;
}
@media (max-width: 760px) { .layout { grid-template-columns: 1fr; } }
</style>
