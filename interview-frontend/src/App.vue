<template>
  <main class="app-shell">
    <!-- 背景动态涟漪（纯装饰，aria 隐藏；prefers-reduced-motion 下自动静止） -->
    <div class="bg-ripple" v-show="bgFx" aria-hidden="true">
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
        </nav>

        <div class="side-bottom">
          <!-- 用户头像区：点击弹出小窗 -->
          <div ref="footRef" class="foot">
            <button class="user-chip" :class="{ on: popOpen }" @click="togglePop" :title="auth.username">
              <span class="avatar" :style="avCss">{{ initials }}</span>
              <span v-if="auth.username" class="uname">{{ auth.username }}</span>
              <span class="chev" :class="{ up: popOpen }">▴</span>
            </button>

            <transition name="pop">
              <div v-if="popOpen" class="pop card" role="dialog">
                <!-- 身份 -->
                <div class="pop-head">
                  <span class="avatar lg" :style="avCss">{{ initials }}</span>
                  <div class="who">
                    <b>{{ auth.username }}</b>
                    <span v-if="auth.isAdmin" class="admin-badge">管理员</span>
                  </div>
                </div>

                <!-- 入口区 -->
                <div class="pop-menu">
                  <button class="nav-btn" @click="openSettings">
                    <span>设置</span><span class="arrow">→</span>
                  </button>
                  <router-link v-if="auth.isAdmin" class="nav-btn" to="/admin" @click="popOpen = false">
                    <span>管理后台</span><span class="arrow">→</span>
                  </router-link>
                </div>

                <button class="pop-logout" @click="logout">退出登录</button>
              </div>
            </transition>
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
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authState, clearAuth } from './store/auth'
import { avatarStyle, initialsOf } from './utils/avatar'
import { Settings } from './utils/settings'

const route = useRoute()
const router = useRouter()
const auth = authState

const isStandalone = computed(() => route.name === 'login' || route.name === 'landing')

// ---------- 头像 ----------
const initials = computed(() => initialsOf(auth.username))
const avCss = computed(() => avatarStyle(auth.username))

// ---------- 用户小窗 ----------
const popOpen = ref(false)
const footRef = ref(null)

function togglePop() {
  popOpen.value = !popOpen.value
}

function onDocClick(e) {
  if (footRef.value && !footRef.value.contains(e.target)) popOpen.value = false
}

// ---------- 全局设置状态（真正开关在独立设置页 /settings） ----------
const S = Settings.keys
const bgFx = ref(Settings.isOn(S.bgFx, true))
const reduceMotion = ref(Settings.isOn(S.reduceMotion, false))

function applyReduce() {
  document.documentElement.classList.toggle('reduce-motion', reduceMotion.value)
}

// 设置页改动后同步到本组件（涟漪显隐 / html.reduce-motion）
function onPrefs(e) {
  const { key, val } = e.detail || {}
  if (key === 'bgFx') bgFx.value = val
  else if (key === 'reduceMotion') {
    reduceMotion.value = val
    applyReduce()
  }
}

function openSettings() {
  popOpen.value = false
  router.push({ name: 'settings' })
}

function logout() {
  clearAuth()
  router.push({ name: 'login' })
}

onMounted(() => {
  applyReduce()
  window.addEventListener('msi:prefs', onPrefs)
  document.addEventListener('click', onDocClick)
})
onBeforeUnmount(() => {
  window.removeEventListener('msi:prefs', onPrefs)
  document.removeEventListener('click', onDocClick)
})
</script>

<style scoped>
.app-shell { min-height: 100vh; display: flex; }

/* 桌面：左侧悬浮胶囊栏 + 右侧内容 */
.side-nav {
  position: sticky;
  top: 12px;
  height: calc(100vh - 24px);
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 12px 10px 12px 14px;
  padding: 24px 12px 18px;
  background: rgba(255, 255, 255, 0.55);
  -webkit-backdrop-filter: blur(24px) saturate(160%);
  backdrop-filter: blur(24px) saturate(160%);
  border: 1px solid rgba(255, 255, 255, 0.72);
  border-radius: 28px;
  box-shadow: var(--shadow-md);
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
/* 用户头像行（点击弹小窗） */
.foot { position: relative; }
.user-chip {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid transparent;
  background: transparent;
  padding: 6px 8px;
  border-radius: 16px;
  cursor: pointer;
  transition: var(--transition);
  text-align: left;
  color: var(--ink);
}
.user-chip:hover, .user-chip.on { background: rgba(255, 255, 255, 0.7); border-color: var(--border-soft); }
.avatar {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: 50%;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.02em;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.25), 0 2px 6px rgba(0, 0, 0, 0.14);
  user-select: none;
}
.avatar.lg { width: 46px; height: 46px; font-size: 17px; }
.uname {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--ink);
}
.chev { color: var(--text-muted); font-size: 10px; transition: transform 0.2s var(--ease); }
.chev.up { transform: rotate(180deg); }
.admin-badge {
  display: inline-block;
  width: fit-content;
  color: var(--danger-text);
  font-size: 11.5px;
  font-weight: 600;
  border: 1px solid var(--danger-bg);
  background: var(--danger-soft);
  padding: 2px 10px;
  border-radius: var(--radius-chip);
}

/* 用户小窗 */
.pop {
  position: absolute;
  left: 0;
  right: 0;
  bottom: calc(100% + 10px);
  width: 300px;
  z-index: 40;
  background: rgba(255, 255, 255, 0.92);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  backdrop-filter: blur(20px) saturate(150%);
  border: 1px solid var(--border-soft);
  border-radius: 20px;
  box-shadow: var(--shadow-lg);
  padding: 18px;
}
.pop-head { display: flex; align-items: center; gap: 12px; padding-bottom: 14px; }
.pop-head .who { display: flex; flex-direction: column; gap: 6px; }
.pop-head b { font-size: 15px; color: var(--ink); }
.pop-menu { display: flex; flex-direction: column; gap: 6px; }
.nav-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 11px 14px;
  border-radius: 13px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--ink);
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition);
  width: 100%;
}
.nav-btn:hover { background: var(--ink-soft); }
.arrow { color: var(--text-muted); font-size: 14px; transition: transform 0.15s var(--ease); }
.nav-btn:hover .arrow { color: var(--ink); transform: translateX(2px); }
.pop-logout {
  width: 100%;
  margin-top: 8px;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--danger);
  font-size: 13px;
  padding: 8px 0;
  border-radius: 12px;
  cursor: pointer;
  transition: var(--transition);
}
.pop-logout:hover { background: var(--danger-bg); border-color: var(--danger); }
/* 小窗过渡 */
.pop-enter-active, .pop-leave-active { transition: opacity 0.16s var(--ease), transform 0.16s var(--ease); }
.pop-enter-from, .pop-leave-to { opacity: 0; transform: translateY(6px) scale(0.98); }

.page {
  flex: 1;
  min-width: 0;
  padding: 0 8px;
}

/* 窄屏：收成顶部横向胶囊 */
@media (max-width: 900px) {
  .app-shell { flex-direction: column; }
  .side-nav {
    position: static;
    height: auto;
    width: auto;
    flex-direction: row;
    align-items: center;
    gap: 10px;
    margin: 10px 12px;
    padding: 10px 14px;
    border-radius: 24px;
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
  .foot { position: static; }
  .user-chip { width: auto; padding: 4px 6px; }
  .uname { display: none; }
  .chev { display: none; }
  .pop {
    position: fixed;
    top: 66px;
    left: 50%;
    transform: translateX(-50%);
    bottom: auto;
    right: auto;
    width: min(320px, calc(100vw - 32px));
  }
  .pop-enter-from, .pop-leave-to { transform: translate(-50%, 6px) scale(0.98); }
}
</style>
