<template>
  <div class="admin-view">
    <!-- 顶部 -->
    <div class="top">
      <div>
        <h1>后台管理系统</h1>
        <p class="sub">管理员控制台：账号、面试会话、行业调研与求职项目记录统一管理（操作即改库）。</p>
      </div>
      <button class="ghost" :disabled="loading" @click="loadAll">
        {{ loading ? '加载中…' : '刷新数据' }}
      </button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <!-- 总览统计 -->
    <div class="stats">
      <div class="stat"><span class="k">总用户</span><span class="v">{{ users.length }}</span><span class="s">管理员 {{ admins.length }}</span></div>
      <div class="stat"><span class="k">面试场次</span><span class="v">{{ totalSessions }}</span><span class="s">进行中 {{ runningCount }}</span></div>
      <div class="stat"><span class="k">已结束面试</span><span class="v">{{ completedCount }}</span><span class="s">带报告 {{ hasReportCount }}</span></div>
      <div class="stat"><span class="k">行业调研</span><span class="v">{{ totalIndustry }}</span><span class="s">覆盖 {{ industry.length }} 条可见</span></div>
      <div class="stat"><span class="k">求职项目</span><span class="v">{{ totalProject }}</span><span class="s">覆盖 {{ project.length }} 条可见</span></div>
      <div class="stat"><span class="k">活跃度</span><span class="v">{{ activeUsers }}</span><span class="s">有面试记录的用户</span></div>
    </div>

    <!-- 分区页签 -->
    <div class="tabs">
      <button
        v-for="t in tabs"
        :key="t.key"
        class="tab"
        :class="{ on: tab === t.key }"
        @click="tab = t.key"
      >{{ t.label }}</button>
    </div>

    <!-- 用户管理 -->
    <section v-if="tab === 'users'" class="panel card">
      <div class="bar">
        <h2>用户列表 <span class="cnt">{{ filteredUsers.length }}</span></h2>
        <input v-model.trim="qUser" class="search" placeholder="搜索用户名 / ID" />
      </div>
      <table v-if="filteredUsers.length" class="tbl">
        <thead><tr>
          <th>ID</th><th>用户名</th><th>类型</th><th>注册时间</th>
          <th>面试</th><th>行业</th><th>求职</th><th>操作</th>
        </tr></thead>
        <tbody>
          <tr v-for="u in filteredUsers" :key="u.id">
            <td>{{ u.id }}</td>
            <td class="strong">{{ u.username }}</td>
            <td><span class="tag" :class="u.is_admin ? 'tag-admin' : 'tag-user'">{{ u.is_admin ? '管理员' : '用户' }}</span></td>
            <td class="muted">{{ u.created_at }}</td>
            <td>{{ u.session_count }}</td>
            <td>{{ u.industry_count }}</td>
            <td>{{ u.project_count }}</td>
            <td>
              <button v-if="!u.is_admin" class="btn-del" :disabled="deleting === u.id" @click="removeUser(u)">
                {{ deleting === u.id ? '删除中…' : '删除' }}
              </button>
              <span v-else class="muted">受保护</span>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty">没有匹配的用户</p>
    </section>

    <!-- 面试会话 -->
    <section v-if="tab === 'sessions'" class="panel card">
      <div class="bar">
        <h2>面试会话 <span class="cnt">{{ filteredSessions.length }}</span></h2>
        <div class="filters">
          <select v-model="qStatus" class="search">
            <option value="">全部状态</option>
            <option value="in_progress">进行中</option>
            <option value="completed">已结束</option>
          </select>
          <input v-model.trim="qSession" class="search" placeholder="搜索岗位 / 用户" />
        </div>
      </div>
      <table v-if="filteredSessions.length" class="tbl">
        <thead><tr>
          <th>ID</th><th>用户</th><th>岗位</th><th>面试官</th><th>状态</th>
          <th>消息</th><th>报告</th><th>开始时间</th><th>操作</th>
        </tr></thead>
        <tbody>
          <tr v-for="s in filteredSessions" :key="s.id">
            <td>{{ s.id }}</td>
            <td class="strong">{{ s.username }}</td>
            <td>{{ s.job_title }}</td>
            <td class="muted">{{ s.interviewer_name }}</td>
            <td><span class="tag" :class="s.status === 'completed' ? 'tag-done' : 'tag-run'">{{ s.status === 'completed' ? '已结束' : '进行中' }}</span></td>
            <td>{{ s.message_count }}</td>
            <td>{{ s.has_report ? '✓' : '—' }}</td>
            <td class="muted">{{ s.created_at }}</td>
            <td class="ops">
              <button class="btn-view" @click="viewSession(s)">查看</button>
              <button class="btn-del" :disabled="deleting === 's' + s.id" @click="removeSession(s)">{{ deleting === 's' + s.id ? '…' : '删除' }}</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty">没有匹配的会话</p>
    </section>

    <!-- 行业调研记录 -->
    <section v-if="tab === 'industry'" class="panel card">
      <div class="bar">
        <h2>行业调研记录 <span class="cnt">{{ filteredIndustry.length }}</span></h2>
        <input v-model.trim="qIndustry" class="search" placeholder="搜索行业 / 用户" />
      </div>
      <table v-if="filteredIndustry.length" class="tbl">
        <thead><tr><th>ID</th><th>用户</th><th>行业</th><th>内容预览</th><th>时间</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="r in filteredIndustry" :key="r.id">
            <td>{{ r.id }}</td>
            <td class="strong">{{ r.username }}</td>
            <td>{{ r.industry_name }}</td>
            <td class="preview">{{ r.content_preview }}</td>
            <td class="muted">{{ r.created_at }}</td>
            <td><button class="btn-del" :disabled="deleting === 'i' + r.id" @click="removeIndustry(r)">{{ deleting === 'i' + r.id ? '…' : '删除' }}</button></td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty">暂无行业调研记录</p>
    </section>

    <!-- 求职项目记录 -->
    <section v-if="tab === 'project'" class="panel card">
      <div class="bar">
        <h2>求职项目记录 <span class="cnt">{{ filteredProject.length }}</span></h2>
        <input v-model.trim="qProject" class="search" placeholder="搜索项目 / 用户" />
      </div>
      <table v-if="filteredProject.length" class="tbl">
        <thead><tr><th>ID</th><th>用户</th><th>类型</th><th>项目</th><th>内容预览</th><th>时间</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="r in filteredProject" :key="r.id">
            <td>{{ r.id }}</td>
            <td class="strong">{{ r.username }}</td>
            <td><span class="tag" :class="r.type === 'channels' ? 'tag-done' : 'tag-warn'">{{ r.type === 'channels' ? '渠道清单' : '讲项目话术' }}</span></td>
            <td>{{ r.project_name || '—' }}</td>
            <td class="preview">{{ r.content_preview }}</td>
            <td class="muted">{{ r.created_at }}</td>
            <td><button class="btn-del" :disabled="deleting === 'p' + r.id" @click="removeProject(r)">{{ deleting === 'p' + r.id ? '…' : '删除' }}</button></td>
          </tr>
        </tbody>
      </table>
      <p v-else class="empty">暂无求职项目记录</p>
    </section>

    <!-- 会话审阅弹窗 -->
    <div v-if="detail.open" class="overlay" @click.self="detail.open = false">
      <div class="modal card">
        <div class="modal-head">
          <h2>会话 #{{ detail.data?.id }} 审阅</h2>
          <button class="ghost" @click="detail.open = false">关闭</button>
        </div>
        <p v-if="detail.error" class="error">{{ detail.error }}</p>
        <p v-if="detail.loading" class="empty">加载中…</p>
        <template v-else-if="detail.data">
          <div class="meta">
            <span>用户：<b>{{ detail.data.username }}</b></span>
            <span>岗位：<b>{{ detail.data.job_title }}</b></span>
            <span>面试官：<b>{{ detail.data.interviewer_name }}</b></span>
            <span>状态：<b>{{ detail.data.status === 'completed' ? '已结束' : '进行中' }}</b></span>
            <span>开始：<span class="muted">{{ detail.data.created_at }}</span></span>
          </div>
          <div v-if="detail.data.report" class="report-card">
            <b class="score">{{ detail.data.report.overall_score }}<span>/100</span></b>
            <p>{{ detail.data.report.summary }}</p>
          </div>
          <div class="msgs">
            <div v-for="(m, i) in detail.data.messages" :key="i" class="msg" :class="m.role">
              <span class="who">{{ m.role === 'user' ? '候选人' : '面试官' }}</span>
              <pre class="text">{{ m.content }}</pre>
              <pre v-if="m.reference" class="ref">参考要点：{{ m.reference }}</pre>
            </div>
            <p v-if="!detail.data.messages.length" class="empty">该会话暂无消息</p>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { adminApi } from '../api'

const tabs = [
  { key: 'users', label: '用户' },
  { key: 'sessions', label: '面试会话' },
  { key: 'industry', label: '行业调研' },
  { key: 'project', label: '求职项目' },
]

const tab = ref('users')
const users = ref([])
const sessions = ref([])
const industry = ref([])
const project = ref([])
const loading = ref(false)
const error = ref('')
const deleting = ref(null)

// 搜索 / 筛选
const qUser = ref('')
const qSession = ref('')
const qStatus = ref('')
const qIndustry = ref('')
const qProject = ref('')

// 会话审阅弹窗
const detail = ref({ open: false, loading: false, error: '', data: null })

const filteredUsers = computed(() => {
  const k = qUser.value.trim().toLowerCase()
  if (!k) return users.value
  return users.value.filter((u) => u.username.toLowerCase().includes(k) || String(u.id) === k)
})
const filteredSessions = computed(() => {
  const k = qSession.value.trim().toLowerCase()
  return sessions.value.filter((s) => {
    if (qStatus.value && s.status !== qStatus.value) return false
    if (!k) return true
    return s.job_title.toLowerCase().includes(k) || s.username.toLowerCase().includes(k)
  })
})
const filteredIndustry = computed(() => {
  const k = qIndustry.value.trim().toLowerCase()
  if (!k) return industry.value
  return industry.value.filter((r) => r.industry_name.toLowerCase().includes(k) || r.username.toLowerCase().includes(k))
})
const filteredProject = computed(() => {
  const k = qProject.value.trim().toLowerCase()
  if (!k) return project.value
  return project.value.filter((r) => (r.project_name || '').toLowerCase().includes(k) || r.username.toLowerCase().includes(k))
})

// 统计（用户维度全量精确；会话状态按最近 500 场快照）
const admins = computed(() => users.value.filter((u) => u.is_admin))
const totalSessions = computed(() => users.value.reduce((a, u) => a + u.session_count, 0))
const totalIndustry = computed(() => users.value.reduce((a, u) => a + u.industry_count, 0))
const totalProject = computed(() => users.value.reduce((a, u) => a + u.project_count, 0))
const runningCount = computed(() => sessions.value.filter((s) => s.status !== 'completed').length)
const completedCount = computed(() => sessions.value.filter((s) => s.status === 'completed').length)
const hasReportCount = computed(() => sessions.value.filter((s) => s.has_report).length)
const activeUsers = computed(() => users.value.filter((u) => u.session_count > 0).length)

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    const [u, s, i, p] = await Promise.all([
      adminApi.users(),
      adminApi.sessions(),
      adminApi.industry(),
      adminApi.project(),
    ])
    users.value = u
    sessions.value = s
    industry.value = i
    project.value = p
  } catch (e) {
    error.value = e.response?.data?.detail || '加载失败，请确认使用管理员账号'
  } finally {
    loading.value = false
  }
}

function removeUser(u) {
  if (!window.confirm(`确定删除用户「${u.username}」(ID ${u.id})？\n其全部面试、消息、报告、行业与求职记录将一并删除，不可恢复。`)) return
  doDelete(() => adminApi.deleteUser(u.id), () => {
    users.value = users.value.filter((x) => x.id !== u.id)
    sessions.value = sessions.value.filter((x) => x.user_id !== u.id)
    industry.value = industry.value.filter((x) => x.user_id !== u.id)
    project.value = project.value.filter((x) => x.user_id !== u.id)
  }, u.id)
}
function removeSession(s) {
  if (!window.confirm(`确定删除会话「${s.job_title}」(ID ${s.id}, 用户 ${s.username})？其消息与报告一并删除，不可恢复。`)) return
  doDelete(() => adminApi.deleteSession(s.id), () => {
    sessions.value = sessions.value.filter((x) => x.id !== s.id)
  }, 's' + s.id)
}
function removeIndustry(r) {
  if (!window.confirm(`确定删除行业调研「${r.industry_name}」(ID ${r.id}, 用户 ${r.username})？`)) return
  doDelete(() => adminApi.deleteIndustry(r.id), () => {
    industry.value = industry.value.filter((x) => x.id !== r.id)
  }, 'i' + r.id)
}
function removeProject(r) {
  if (!window.confirm(`确定删除「${r.project_name || r.type}」记录 (ID ${r.id}, 用户 ${r.username})？`)) return
  doDelete(() => adminApi.deleteProject(r.id), () => {
    project.value = project.value.filter((x) => x.id !== r.id)
  }, 'p' + r.id)
}

async function doDelete(call, after, key) {
  deleting.value = key
  error.value = ''
  try {
    await call()
    after()
  } catch (e) {
    error.value = e.response?.data?.detail || '删除失败'
  } finally {
    deleting.value = null
  }
}

async function viewSession(s) {
  detail.value = { open: true, loading: true, error: '', data: null }
  try {
    const data = await adminApi.sessionDetail(s.id)
    detail.value = { open: true, loading: false, error: '', data }
  } catch (e) {
    detail.value = { open: true, loading: false, error: e.response?.data?.detail || '加载详情失败', data: null }
  }
}

onMounted(loadAll)
</script>

<style scoped>
.admin-view { max-width: 1180px; margin: 0 auto; padding: 24px 28px 64px; }
.top { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; flex-wrap: wrap; }
.top h1 { font-size: 26px; font-weight: 780; letter-spacing: -0.015em; color: var(--ink); }
.sub { color: var(--text-secondary); font-size: 14px; margin: 6px 0 18px; }
.error { color: var(--danger); margin-bottom: 12px; }

.stats {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 14px;
}
.stat {
  background: rgba(255, 255, 255, 0.56);
  -webkit-backdrop-filter: blur(22px) saturate(150%);
  backdrop-filter: blur(22px) saturate(150%);
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 18px;
  box-shadow: var(--shadow-sm);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stat .k { font-size: 12px; color: var(--text-secondary); }
.stat .v { font-size: 24px; font-weight: 760; color: var(--ink); line-height: 1.1; }
.stat .s { font-size: 11.5px; color: var(--text-muted); }

.tabs { display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }
.tab {
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--text-secondary);
  font-size: 13.5px;
  font-weight: 600;
  padding: 8px 20px;
  border-radius: var(--radius-chip);
  cursor: pointer;
  transition: var(--transition);
}
.tab:hover { color: var(--ink); border-color: var(--ink); }
.tab.on { background: var(--ink); color: #fff; border-color: var(--ink); }

.card {
  background: var(--card);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-sm);
  padding: 18px 20px;
}
.panel h2 { font-size: 15.5px; font-weight: 700; color: var(--ink); display: flex; align-items: center; gap: 8px; margin: 0; }
.cnt {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--ink);
  background: var(--ink-soft);
  padding: 1px 9px;
  border-radius: var(--radius-chip);
}
.bar { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.filters { display: flex; gap: 8px; }
.search {
  height: 34px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-input);
  background: var(--bg-soft);
  font-size: 13px;
  color: var(--text);
  min-width: 180px;
  transition: var(--transition);
}
.search:focus { outline: none; border-color: var(--ink); background: var(--card); box-shadow: var(--ring); }

.tbl { width: 100%; border-collapse: collapse; font-size: 13px; }
.tbl th, .tbl td { text-align: left; padding: 9px 10px; border-bottom: 1px solid var(--border-soft); }
.tbl th { color: var(--text-secondary); font-weight: 600; font-size: 12px; white-space: nowrap; }
.tbl tbody tr { transition: var(--transition); }
.tbl tbody tr:hover { background: var(--bg-soft); }
.tbl tbody tr:last-child td { border-bottom: none; }
.strong { font-weight: 650; color: var(--ink); }
.muted { color: var(--text-muted); }
.preview { max-width: 360px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ops { display: flex; gap: 6px; }
.empty { color: var(--text-muted); font-size: 13px; padding: 18px 0; text-align: center; }

.tag { font-size: 11px; padding: 2px 10px; border-radius: var(--radius-chip); white-space: nowrap; font-weight: 600; }
.tag-admin { background: var(--danger-bg); color: var(--danger-text); }
.tag-user { background: var(--ink-soft); color: var(--ink); }
.tag-done { background: var(--success-bg); color: var(--success-text); }
.tag-run { background: var(--warning-bg); color: var(--warning-text); }
.tag-warn { background: var(--warning-bg); color: var(--warning-text); }

.btn-del {
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--danger);
  font-size: 12px;
  padding: 4px 12px;
  border-radius: var(--radius-chip);
  cursor: pointer;
  transition: var(--transition);
}
.btn-del:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-del:hover:not(:disabled) { background: var(--danger-bg); border-color: var(--danger); }
.btn-view {
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--ink);
  font-size: 12px;
  padding: 4px 12px;
  border-radius: var(--radius-chip);
  cursor: pointer;
  transition: var(--transition);
}
.btn-view:hover { border-color: var(--ink); background: var(--ink-soft); }
.ghost {
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--text-secondary);
  font-size: 13px;
  padding: 8px 18px;
  border-radius: var(--radius-chip);
  cursor: pointer;
  transition: var(--transition);
}
.ghost:hover { color: var(--ink); border-color: var(--ink); }
.ghost:disabled { opacity: 0.5; cursor: not-allowed; }

/* 弹窗 */
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 17, 21, 0.4);
  backdrop-filter: blur(3px);
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.modal {
  width: min(820px, 100%);
  max-height: 86vh;
  display: flex;
  flex-direction: column;
  padding: 20px 24px;
  overflow: hidden;
}
.modal-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.modal-head h2 { font-size: 17px; font-weight: 740; color: var(--ink); margin: 0; }
.meta { display: flex; flex-wrap: wrap; gap: 8px 22px; font-size: 13px; color: var(--text-secondary); padding: 10px 0; border-bottom: 1px solid var(--border-soft); margin-bottom: 12px; }
.report-card {
  background: var(--ink-soft);
  border-radius: 14px;
  padding: 12px 16px;
  margin-bottom: 12px;
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.report-card .score { font-size: 30px; color: var(--ink); white-space: nowrap; }
.report-card .score span { font-size: 13px; color: var(--text-secondary); }
.report-card p { color: var(--text); font-size: 13px; line-height: 1.7; margin: 0; }
.msgs { overflow-y: auto; display: flex; flex-direction: column; gap: 10px; padding-right: 4px; }
.msg { border-radius: 14px; padding: 10px 14px; }
.msg.user { background: var(--ink-soft); align-self: flex-end; max-width: 88%; }
.msg.assistant { background: var(--bg-soft); align-self: flex-start; max-width: 92%; }
.who { font-size: 11px; font-weight: 700; color: var(--text-secondary); display: block; margin-bottom: 4px; }
.text { white-space: pre-wrap; font-family: inherit; font-size: 13.5px; line-height: 1.7; color: var(--text); margin: 0; }
.ref { margin: 8px 0 0; font-size: 12px; color: var(--text-muted); white-space: pre-wrap; font-family: inherit; border-top: 1px dashed var(--border); padding-top: 6px; }

@media (max-width: 1000px) {
  .stats { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 640px) {
  .stats { grid-template-columns: repeat(2, 1fr); }
  .preview { display: none; }
  .tbl { font-size: 12px; }
}
</style>
