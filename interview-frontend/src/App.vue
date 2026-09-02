<template>
  <main class="app-shell">
    <template v-if="!isLoginPage">
      <nav class="top-nav">
        <span class="brand">模拟面试 AI 助手</span>
        <router-link to="/home">首页</router-link>
        <router-link to="/history">面试历史</router-link>
        <router-link to="/industry">行业调研</router-link>
        <router-link to="/project">求职渠道</router-link>
        <router-link v-if="auth.isAdmin" to="/admin">账号管理</router-link>
        <span class="spacer"></span>
        <span v-if="auth.isAdmin" class="admin-badge">管理员</span>
        <span v-if="auth.username" class="user">{{ auth.username }}</span>
        <button class="logout" @click="logout">退出</button>
      </nav>
    </template>
    <router-view />
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authState, clearAuth } from './store/auth'

const route = useRoute()
const router = useRouter()
const auth = authState

const isLoginPage = computed(() => route.name === 'login')

function logout() {
  clearAuth()
  router.push({ name: 'login' })
}
</script>

<style scoped>
.app-shell { min-height: 100vh; }
.top-nav {
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 12px 24px;
  border-bottom: 1px solid var(--border);
  background: #fff;
  position: sticky;
  top: 0;
  z-index: 10;
}
.top-nav .brand { font-weight: 700; color: var(--primary); }
.top-nav a { color: var(--text); text-decoration: none; font-size: 14px; }
.top-nav a.router-link-active { color: var(--primary); font-weight: 600; }
.spacer { flex: 1; }
.user { color: var(--text-secondary); font-size: 13px; }
.admin-badge {
  color: #b91c1c; font-size: 12px; border: 1px solid #fecaca;
  background: #fef2f2; padding: 1px 8px; border-radius: 10px;
}
.logout {
  background: none; border: 1px solid var(--border); color: var(--text-secondary);
  padding: 4px 12px; border-radius: 8px; cursor: pointer; font-size: 13px;
}
</style>
