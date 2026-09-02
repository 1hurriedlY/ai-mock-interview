/* 登录态 store：token/用户名/管理员标记 持久化到 localStorage，
 * 供路由守卫与 axios 拦截器使用。不引 Pinia，用轻量 reactive 单例即可。
 */
import { reactive } from 'vue'

const TOKEN_KEY = 'interview_token'
const USERNAME_KEY = 'interview_username'
const ADMIN_KEY = 'interview_is_admin'

export const authState = reactive({
  token: localStorage.getItem(TOKEN_KEY) || '',
  username: localStorage.getItem(USERNAME_KEY) || '',
  isAdmin: localStorage.getItem(ADMIN_KEY) === '1',
})

export function setAuth(token, username, isAdmin = false) {
  authState.token = token || ''
  authState.username = username || ''
  authState.isAdmin = Boolean(isAdmin)
  if (authState.token) localStorage.setItem(TOKEN_KEY, authState.token)
  else localStorage.removeItem(TOKEN_KEY)
  if (authState.username) localStorage.setItem(USERNAME_KEY, authState.username)
  else localStorage.removeItem(USERNAME_KEY)
  if (authState.isAdmin) localStorage.setItem(ADMIN_KEY, '1')
  else localStorage.removeItem(ADMIN_KEY)
}

export function clearAuth() {
  authState.token = ''
  authState.username = ''
  authState.isAdmin = false
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USERNAME_KEY)
  localStorage.removeItem(ADMIN_KEY)
}

export function isAuthed() {
  return Boolean(authState.token)
}
