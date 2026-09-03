<template>
  <div ref="root" class="login-view">
    <router-link class="back-btn" to="/">← 返回主界面</router-link>
    <form class="login-card glass" data-reveal @submit.prevent="submit">
      <div class="brand-mark">
        <span class="brand-emoji">●‿●</span>
      </div>
      <h1>欢迎回来</h1>
      <p class="subtitle">登录后开始你的模拟面试练习</p>

      <label>邮箱</label>
      <input v-model.trim="username" placeholder="至少 2 个字符" autocomplete="username" />

      <label>密码</label>
      <input v-model="password" type="password" placeholder="至少 6 位" autocomplete="current-password" />

      <p v-if="error" class="error">{{ error }}</p>

      <button type="submit" :disabled="loading || !canSubmit" class="btn btn-primary btn-lg">
        {{ loading ? '提交中…' : isLogin ? '登录' : '注册并登录' }}
      </button>

      <p class="switch" @click="isLogin = !isLogin">
        {{ isLogin ? '没有账号？点此注册' : '已有账号？去登录' }}
      </p>
    </form>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authApi } from '../api'
import { setAuth } from '../store/auth'
import { bindReveal } from '../utils/reveal'

const route = useRoute()
const router = useRouter()
const root = ref(null)

const isLogin = ref(true)
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const canSubmit = computed(() => username.value.length >= 2 && password.value.length >= 6)

onMounted(() => {
  bindReveal(root.value)
})

async function submit() {
  if (!canSubmit.value || loading.value) return
  loading.value = true
  error.value = ''
  try {
    const api = isLogin.value ? authApi.login : authApi.register
    const data = await api(username.value, password.value)
    setAuth(data.access_token, data.username, data.is_admin)
    router.push(String(route.query.redirect || '/home'))
  } catch (e) {
    error.value = e.response?.data?.detail || '操作失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-view {
  position: relative;
  width: 100%;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 20px;
}
/* 左上角悬浮返回钮（卡片框外，毛玻璃胶囊） */
.back-btn {
  position: absolute;
  top: 22px;
  left: 24px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: var(--radius-chip);
  background: rgba(255, 255, 255, 0.7);
  -webkit-backdrop-filter: saturate(140%) blur(12px);
  backdrop-filter: saturate(140%) blur(12px);
  border: 1px solid var(--border-soft);
  color: var(--text-secondary);
  font-size: 13.5px;
  font-weight: 600;
  text-decoration: none;
  box-shadow: var(--shadow-sm);
  transition: var(--transition);
}
.back-btn:hover {
  color: var(--ink);
  border-color: var(--ink);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}
.back-btn:active { transform: scale(0.97); }
.login-card {
  width: 100%;
  max-width: 400px;
  background: transparent;
  border: 1px solid var(--border-soft);
  border-radius: var(--radius-panel);
  box-shadow: var(--shadow-lg);
  padding: 28px 28px 22px;
  text-align: center;
}
.brand-mark {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: var(--ink);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  letter-spacing: 0.02em;
  margin: 0 auto 14px;
  box-shadow: 0 10px 20px rgba(15, 17, 21, 0.16);
}
h1 {
  font-size: 22px;
  font-weight: 720;
  letter-spacing: -0.01em;
  color: var(--ink);
}
.subtitle {
  color: var(--text-secondary);
  margin: 4px 0 20px;
  font-size: 13px;
}
label {
  display: block;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
  margin: 12px 0 6px;
}
input {
  width: 100%;
  height: 40px;
  padding: 0 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-input);
  background: var(--bg-soft);
  font-size: 14px;
  transition: var(--transition);
  text-align: left;
}
input:focus {
  outline: none;
  border-color: var(--ink);
  background: var(--card);
  box-shadow: var(--ring);
}
input::placeholder { color: var(--text-muted); }
.error { color: var(--danger); font-size: 13px; margin-top: 10px; }
/* 提交按钮：与密码框拉开距离（类名已是 btn btn-primary btn-lg，按 type 匹配） */
.login-card button[type='submit'] {
  width: 100%;
  margin-top: 30px;
}
.switch {
  color: var(--text-secondary);
  font-size: 13px;
  margin-top: 14px;
  cursor: pointer;
  user-select: none;
}
.switch:hover { color: var(--ink); }
</style>