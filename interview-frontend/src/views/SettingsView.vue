<template>
  <div class="settings-view">
    <div class="head">
      <div>
        <h1>设置</h1>
        <p class="sub">偏好会保存在本机浏览器，换电脑需重新设置。</p>
      </div>
      <router-link class="ghost" to="/home">返回首页</router-link>
    </div>

    <!-- 我的账号 -->
    <section class="card account">
      <span class="avatar" :style="avCss">{{ initials }}</span>
      <div class="who">
        <b>{{ auth.username }}</b>
        <span class="role">{{ auth.isAdmin ? '管理员' : '普通用户' }}</span>
      </div>
      <span v-if="auth.isAdmin" class="admin-badge">管理员</span>
    </section>

    <!-- 通用 -->
    <section class="card group">
      <h2>通用</h2>
      <label class="row">
        <span class="info">
          <span class="name">背景动态效果</span>
          <span class="desc">登录后的涟漪光斑装饰，关闭后更素净</span>
        </span>
        <span class="sw"><input type="checkbox" :checked="bgFx" @change="set('bgFx', $event.target.checked)" /><i></i></span>
      </label>
      <label class="row">
        <span class="info">
          <span class="name">页面过渡动效</span>
          <span class="desc">关闭后过渡/滚动浮现等动画全部静止，更省资源</span>
        </span>
        <span class="sw"><input type="checkbox" :checked="reduceMotion" @change="set('reduceMotion', $event.target.checked)" /><i></i></span>
      </label>
    </section>

    <!-- 面试偏好 -->
    <section class="card group">
      <h2>面试偏好</h2>
      <label class="row">
        <span class="info">
          <span class="name">AI 回复自动朗读</span>
          <span class="desc">进入面试页后，收到 AI 回复自动语音朗读</span>
        </span>
        <span class="sw"><input type="checkbox" :checked="autoSpeak" @change="set('autoSpeak', $event.target.checked)" /><i></i></span>
      </label>
      <label class="row row-sel">
        <span class="info">
          <span class="name">默认面试官</span>
          <span class="desc">首页开启新面试时自动选中该角色</span>
        </span>
        <select :value="defaultRole" class="sel" @change="setRole($event.target.value)">
          <option value="technical">技术面</option>
          <option value="HR">HR 行为面</option>
          <option value="stress">压力面</option>
        </select>
      </label>
    </section>

    <p class="foot-note">「模拟面试 AI 助手」· 数据仅存于你的服务器 · v0.1</p>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { authState } from '../store/auth'
import { avatarStyle, initialsOf } from '../utils/avatar'
import { Settings } from '../utils/settings'

const auth = authState
const initials = ref(initialsOf(auth.username))
const avCss = ref(avatarStyle(auth.username))

const S = Settings.keys
const bgFx = ref(Settings.isOn(S.bgFx, true))
const reduceMotion = ref(Settings.isOn(S.reduceMotion, false))
const autoSpeak = ref(Settings.isOn(S.autoSpeak, false))
const defaultRole = ref(Settings.get(S.defaultRole) || 'technical')

function applyReduce() {
  document.documentElement.classList.toggle('reduce-motion', reduceMotion.value)
}
function emit(key, val) {
  window.dispatchEvent(new CustomEvent('msi:prefs', { detail: { key, val } }))
}
function set(key, val) {
  const map = { bgFx, reduceMotion, autoSpeak }
  map[key].value = val
  Settings.set(S[key], val ? '1' : '0')
  if (key === 'reduceMotion') applyReduce()
  emit(key, val)
}
function setRole(v) {
  defaultRole.value = v
  Settings.set(S.defaultRole, v)
  emit('defaultRole', v)
}

onMounted(() => {
  applyReduce()
  document.addEventListener('keydown', onKey)
})
function onKey(e) {
  if (e.key === 'Escape') window.history.back()
}
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>

<style scoped>
.settings-view { max-width: 720px; margin: 0 auto; padding: 24px 24px 64px; }
.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 18px; }
.head h1 { font-size: 26px; font-weight: 780; letter-spacing: -0.015em; color: var(--ink); }
.sub { color: var(--text-secondary); font-size: 14px; margin-top: 6px; }
.ghost {
  border: 1px solid var(--border);
  background: var(--card);
  color: var(--text-secondary);
  font-size: 13px;
  padding: 8px 18px;
  border-radius: var(--radius-chip);
  text-decoration: none;
  transition: var(--transition);
}
.ghost:hover { color: var(--ink); border-color: var(--ink); }

.card {
  background: var(--card);
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-sm);
  padding: 18px 20px;
  margin-bottom: 14px;
}
.account { display: flex; align-items: center; gap: 14px; }
.avatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 19px;
  font-weight: 700;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.25), 0 3px 8px rgba(0, 0, 0, 0.14);
  user-select: none;
}
.who { display: flex; flex-direction: column; gap: 4px; }
.who b { font-size: 16px; color: var(--ink); }
.role { font-size: 12px; color: var(--text-secondary); }
.admin-badge {
  margin-left: auto;
  color: var(--danger-text);
  font-size: 11.5px;
  font-weight: 600;
  border: 1px solid var(--danger-bg);
  background: var(--danger-soft);
  padding: 3px 12px;
  border-radius: var(--radius-chip);
}

.group h2 {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin: 0 0 6px;
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 2px;
  border-top: 1px solid var(--border-soft);
  cursor: pointer;
}
.row:first-of-type { border-top: none; }
.info { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.name { font-size: 14.5px; font-weight: 600; color: var(--ink); }
.desc { font-size: 12px; color: var(--text-muted); }
.sel {
  border: 1px solid var(--border);
  background: var(--bg-soft);
  color: var(--ink);
  font-size: 14px;
  height: 36px;
  padding: 0 12px;
  border-radius: 10px;
  cursor: pointer;
  flex-shrink: 0;
}

/* 开关 */
.sw { position: relative; flex-shrink: 0; }
.sw input { display: none; }
.sw i {
  display: block;
  width: 42px;
  height: 24px;
  border-radius: 999px;
  background: var(--border);
  position: relative;
  transition: background 0.18s var(--ease);
}
.sw i::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.22);
  transition: transform 0.18s var(--ease);
}
.sw input:checked + i { background: var(--ink); }
.sw input:checked + i::after { transform: translateX(18px); }
.foot-note { text-align: center; color: var(--text-muted); font-size: 12px; margin-top: 18px; }
</style>
