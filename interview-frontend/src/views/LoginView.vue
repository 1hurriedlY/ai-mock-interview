<template>
  <div class="login-view">
    <form class="login-card" @submit.prevent="submit">
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
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authApi } from '../api'
import { setAuth } from '../store/auth'

const route = useRoute()
const router = useRouter()

const isLogin = ref(true)
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

const canSubmit = computed(() => username.value.length >= 2 && password.value.length >= 6)

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
  width: 100%;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 20px;
}
.login-card {
  width: 100%;
  max-width: 400px;
  background: var(--card);
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
button.primary { width: 100%; margin-top: 18px; }
.switch {
  color: var(--text-secondary);
  font-size: 13px;
  margin-top: 14px;
  cursor: pointer;
  user-select: none;
}
.switch:hover { color: var(--ink); }
</style>