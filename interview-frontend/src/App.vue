<template>
  <main class="app-shell">
    <!-- 背景动态涟漪（纯装饰，aria 隐藏；prefers-reduced-motion 下自动静止） -->
    <div class="bg-ripple" aria-hidden="true">
      <i class="ripple r-a"></i>
      <i class="ripple r-b"></i>
      <i class="ripple r-c"></i>
    </div>

    <template v-if="!isStandalone">
      <aside class="side-nav">
        <div class="brand">模拟面试 AI 助手</div>

        <nav class="links">
          <router-link to="/home">首页</router-link>
          <router-link to="/history">面试历史</router-link>
          <router-link to="/industry">行业调研</router-link>
          <router-link to="/project">求职渠道</router-link>
          <router-link v-if="auth.isAdmin" to="/admin">账号管理</router-link>
        </nav>

        <div class="side-bottom">
          <span v-if="auth.isAdmin" class="admin-badge">管理员</span>
          <div class="user-row">
            <span v-if="auth.username" class="user">{{ auth.username }}</span>
            <button class="logout" @click="logout">退出</button>
          </div>
        </div>
      </aside>

      <div class="page">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </template>
    <router-view v-else v-slot="{ Component }">
      <transition name="page" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </main>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authState, clearAuth } from './store/auth'

const route = useRoute()
const router = useRouter()
const auth = authState

const isStandalone = computed(() => route.name === 'login' || route.name === 'landing')

function logout() {
  clearAuth()
  router.push({ name: 'login' })
}
</script>

<style scoped>
.app-shell { min-height: 100vh; display: flex; }

/* 桌面：左侧悬浮栏 + 右侧内容 */
.side-nav {
  position: sticky;
  top: 0;
  height: 100vh;
  width: 244px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 22px 14px 18px;
  background: rgba(255, 255, 255, 0.62);
  -webkit-backdrop-filter: saturate(140%) blur(16px);
  backdrop-filter: saturate(140%) blur(16px);
  border-right: 1px solid var(--border-soft);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 15px;
  color: var(--ink);
  padding: 2px 10px 18px;
}
.brand::before {
  content: '●‿●';
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: var(--ink);
  color: #fff;
  font-size: 14px;
}

.links {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.links a {
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 13.5px;
  font-weight: 550;
  padding: 10px 14px;
  border-radius: 12px;
  transition: var(--transition);
}
.links a:hover { color: var(--ink); background: var(--ink-soft); }
.links a.router-link-active {
  color: var(--ink);
  background: var(--ink-soft);
  font-weight: 600;
}

.side-bottom {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 12px;
  border-top: 1px solid var(--border-soft);
}
.user-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.user {
  color: var(--text-secondary);
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}
.admin-badge {
  align-self: flex-start;
  color: var(--danger-text);
  font-size: 11.5px;
  font-weight: 600;
  border: 1px solid var(--danger-bg);
  background: var(--danger-soft);
  padding: 2px 10px;
  border-radius: var(--radius-chip);
}
.logout {
  flex-shrink: 0;
  background: var(--card);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  padding: 6px 14px;
  border-radius: var(--radius-chip);
  cursor: pointer;
  font-size: 13px;
  transition: var(--transition);
}
.logout:hover { color: var(--ink); border-color: var(--ink); }

.page {
  flex: 1;
  min-width: 0;
  padding: 0 8px;
}

/* 窄屏：收成顶部横排 */
@media (max-width: 900px) {
  .app-shell { flex-direction: column; }
  .side-nav {
    position: static;
    height: auto;
    width: 100%;
    flex-direction: row;
    align-items: center;
    gap: 10px;
    padding: 10px 16px;
    border-right: none;
    border-bottom: 1px solid var(--border-soft);
    overflow-x: auto;
  }
  .brand { padding: 0 8px 0 0; white-space: nowrap; }
  .links { flex-direction: row; }
  .links a { padding: 7px 12px; white-space: nowrap; }
  .side-bottom {
    margin-top: 0;
    margin-left: auto;
    flex-direction: row;
    align-items: center;
    gap: 8px;
    padding-top: 0;
    border-top: none;
    flex-shrink: 0;
  }
  .user { display: none; }
}
</style>
