<template>
  <div class="login-view">
    <form class="card" @submit.prevent="submit">
      <h1>模拟面试 AI 助手</h1>
      <p class="subtitle">登录后开始你的模拟面试练习</p>

      <label>用户名</label>
      <input v-model.trim="username" placeholder="至少 2 个字符" autocomplete="username" />

      <label>密码</label>
      <input v-model="password" type="password" placeholder="至少 6 位" autocomplete="current-password" />

      <p v-if="error" class="error">{{ error }}</p>

      <button type="submit" :disabled="loading || !canSubmit" class="primary">
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
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: linear-gradient(135deg, #eef2ff 0%, #f5f6f8 100%);
}
.card {
  width: 100%;
  max-width: 380px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 32px 28px;
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.06);
}
h1 { font-size: 22px; text-align: center; color: var(--primary); }
.subtitle { text-align: center; color: var(--text-secondary); margin: 6px 0 24px; font-size: 13px; }
label { display: block; font-size: 13px; color: var(--text-secondary); margin: 14px 0 6px; }
input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
}
input:focus { outline: none; border-color: var(--primary); }
.error { color: #dc2626; font-size: 13px; margin-top: 10px; }
button.primary {
  width: 100%;
  margin-top: 20px;
  padding: 11px;
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  cursor: pointer;
}
button.primary:disabled { opacity: 0.5; cursor: not-allowed; }
.switch {
  text-align: center;
  color: var(--primary);
  font-size: 13px;
  margin-top: 16px;
  cursor: pointer;
  user-select: none;
}
</style>
