<template>
  <div class="admin-view">
    <div class="hero">
      <h1>账号管理</h1>
      <p>管理员视图：查看所有账号与面试数据，可删除用户或任意会话。</p>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <!-- 用户列表 -->
    <section class="card">
      <h2>账号列表</h2>
      <p v-if="loading" class="muted">加载中…</p>
      <table v-else class="tbl">
        <thead>
          <tr>
            <th>ID</th><th>用户名</th><th>类型</th><th>注册时间</th>
            <th>面试数</th><th>行业调研</th><th>求职工具</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.id }}</td>
            <td>{{ u.username }}</td>
            <td>
              <span class="tag" :class="u.is_admin ? 'tag-admin' : 'tag-user'">
                {{ u.is_admin ? '管理员' : '普通用户' }}
              </span>
            </td>
            <td>{{ u.created_at }}</td>
            <td>{{ u.session_count }}</td>
            <td>{{ u.industry_count }}</td>
            <td>{{ u.project_count }}</td>
            <td>
              <button
                v-if="!u.is_admin"
                class="btn-del"
                :disabled="deleting === u.id"
                @click="removeUser(u)"
              >{{ deleting === u.id ? '删除中…' : '删除' }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- 全量会话 -->
    <section class="card">
      <div class="sec-head">
        <h2>全部面试会话</h2>
        <button class="ghost" @click="load">刷新</button>
      </div>
      <p v-if="sessions.length === 0" class="muted">暂无会话</p>
      <table v-else class="tbl">
        <thead>
          <tr>
            <th>ID</th><th>用户</th><th>岗位</th><th>面试官</th>
            <th>状态</th><th>消息数</th><th>报告</th><th>时间</th><th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in sessions" :key="s.id">
            <td>{{ s.id }}</td>
            <td>{{ s.username }}</td>
            <td>{{ s.job_title }}</td>
            <td>{{ s.interviewer_name }}</td>
            <td>
              <span class="tag" :class="s.status === 'completed' ? 'tag-done' : 'tag-run'">
                {{ s.status === 'completed' ? '已结束' : '进行中' }}
              </span>
            </td>
            <td>{{ s.message_count }}</td>
            <td>{{ s.has_report ? '✓' : '—' }}</td>
            <td>{{ s.created_at }}</td>
            <td>
              <button
                class="btn-del"
                :disabled="deleting === 's' + s.id"
                @click="removeSession(s)"
              >{{ deleting === 's' + s.id ? '删除中…' : '删除' }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { adminApi } from '../api'

const users = ref([])
const sessions = ref([])
const loading = ref(false)
const error = ref('')
const deleting = ref(null) // 防止重复点击：用户 id 或 's'+会话 id

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [u, s] = await Promise.all([adminApi.users(), adminApi.sessions()])
    users.value = u
    sessions.value = s
  } catch (e) {
    error.value = e.response?.data?.detail || '加载失败'
  } finally {
    loading.value = false
  }
}

async function removeUser(u) {
  if (!window.confirm(`确定删除用户「${u.username}」(ID ${u.id}) 吗？\n其全部面试记录、行业调研、求职工具数据将一并删除，不可恢复。`)) return
  deleting.value = u.id
  error.value = ''
  try {
    await adminApi.deleteUser(u.id)
    users.value = users.value.filter((x) => x.id !== u.id)
    sessions.value = sessions.value.filter((x) => x.user_id !== u.id)
  } catch (e) {
    error.value = e.response?.data?.detail || '删除失败'
  } finally {
    deleting.value = null
  }
}

async function removeSession(s) {
  if (!window.confirm(`确定删除会话「${s.job_title}」(ID ${s.id}, 用户 ${s.username}) 吗？删除后不可恢复。`)) return
  deleting.value = 's' + s.id
  error.value = ''
  try {
    await adminApi.deleteSession(s.id)
    sessions.value = sessions.value.filter((x) => x.id !== s.id)
  } catch (e) {
    error.value = e.response?.data?.detail || '删除失败'
  } finally {
    deleting.value = null
  }
}

onMounted(load)
</script>

<style scoped>
.admin-view { max-width: 1100px; margin: 0 auto; padding: 24px 24px 56px; }
.hero h1 {
  font-size: 22px;
  font-weight: 740;
  letter-spacing: -0.012em;
  color: var(--ink);
  margin-bottom: 4px;
}
.hero p { color: var(--text-secondary); font-size: 14px; margin: 4px 0 16px; }
.card {
  background: var(--card);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-sm);
  padding: 20px 22px;
  margin-bottom: 16px;
}
.card h2 {
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
  margin: 0 0 12px;
}
.sec-head { display: flex; justify-content: space-between; align-items: center; }
.muted { color: var(--text-secondary); font-size: 13px; }
.error { color: var(--danger); margin-bottom: 10px; }
.tbl { width: 100%; border-collapse: collapse; font-size: 13px; }
.tbl th, .tbl td { text-align: left; padding: 10px 10px; border-bottom: 1px solid var(--border-soft); white-space: nowrap; }
.tbl th { color: var(--text-secondary); font-weight: 600; font-size: 12px; }
.tbl tbody tr { transition: var(--transition); }
.tbl tbody tr:hover { background: var(--bg-soft); }
.tbl tbody tr:last-child td { border-bottom: none; }
.tag {
  font-size: 11px;
  padding: 2px 10px;
  border-radius: var(--radius-chip);
  white-space: nowrap;
  font-weight: 600;
}
.tag-admin { background: var(--danger-bg); color: var(--danger-text); }
.tag-user { background: var(--ink-soft); color: var(--ink); }
.tag-done { background: var(--success-bg); color: var(--success-text); }
.tag-run { background: var(--warning-bg); color: var(--warning-text); }
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
.btn-del:hover:not(:disabled) {
  background: var(--danger-bg);
  border-color: var(--danger);
}
.ghost {
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--text-secondary);
  font-size: 12.5px;
  padding: 6px 16px;
  border-radius: var(--radius-chip);
  cursor: pointer;
  transition: var(--transition);
}
.ghost:hover { color: var(--ink); border-color: var(--ink); }
</style>
