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
.history-view { max-width: 1100px; margin: 0 auto; padding: 24px 16px 48px; }
.hero h1 { color: var(--primary); margin-bottom: 6px; }
.hero p { color: var(--text-secondary); margin-bottom: 18px; }
.layout { display: grid; grid-template-columns: 340px 1fr; gap: 16px; align-items: start; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }
.muted { color: var(--text-secondary); font-size: 13px; }
.error { color: #dc2626; }
.session-list { list-style: none; margin: 0; padding: 0; max-height: 70vh; overflow-y: auto; }
.session-item { padding: 12px; border-radius: 10px; cursor: pointer; margin-bottom: 6px; }
.session-item:hover { background: #f8fafc; }
.session-item.active { background: #eff6ff; }
.btn-del {
  margin-left: auto; border: 1px solid #fecaca; background: #fff; color: #dc2626;
  font-size: 11px; padding: 2px 8px; border-radius: 8px; cursor: pointer;
  opacity: 0; transition: opacity 0.15s;
}
.session-item:hover .btn-del { opacity: 1; }
.btn-del:hover { background: #fef2f2; }
.session-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.session-head strong { font-size: 14px; }
.tag { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: #eef2ff; color: #3730a3; }
.tag.warn { background: #fef9c3; color: #a16207; }
.score { font-size: 12px; font-weight: 600; }
.score-good { color: #059669; }
.score-mid { color: #d97706; }
.score-low { color: #dc2626; }
.session-meta { display: flex; gap: 10px; color: var(--text-secondary); font-size: 11px; margin-top: 6px; flex-wrap: wrap; }
.detail-head { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.detail-head h2 { font-size: 18px; }
.btn-report {
  background: var(--primary); color: #fff; text-decoration: none;
  padding: 6px 14px; border-radius: 8px; font-size: 13px;
}
.meta-line { color: var(--text-secondary); font-size: 12px; margin: 8px 0 14px; }
.msgs { max-height: 65vh; overflow-y: auto; }
.msg { display: flex; margin-bottom: 10px; }
.msg.right { justify-content: flex-end; }
.bubble {
  max-width: 90%; background: #f1f3f5; padding: 10px 14px; border-radius: 12px;
  white-space: pre-wrap; line-height: 1.7; font-size: 14px;
}
.msg.right .bubble { background: var(--primary); color: #fff; }
.ref { margin-top: 8px; padding-top: 8px; border-top: 1px dashed rgba(37, 99, 235, 0.3); }
.ref-label {
  font-size: 11px; background: #e0e7ff; color: #3730a3;
  padding: 1px 6px; border-radius: 6px;
}
.ref pre {
  margin: 6px 0 0; white-space: pre-wrap; font-family: inherit;
  font-size: 13px; color: var(--text-secondary);
}
@media (max-width: 760px) { .layout { grid-template-columns: 1fr; } }
</style>
