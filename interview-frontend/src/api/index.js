/* API 封装：axios 实例 + 认证拦截器 + 各业务接口。
 * - 请求拦截器自动带 Authorization: Bearer <token>
 * - 响应 401 时清登录态并跳转登录页（token 失效）
 * - 流式对话（SSE）不用 axios，见 useStreamChat
 */
import axios from 'axios'
import router from '../router'
import { authState, clearAuth } from '../store/auth'

// vite dev 代理 /api → http://localhost:8000
const http = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

// 请求拦截：自动带 token
http.interceptors.request.use((config) => {
  if (authState.token) {
    config.headers.Authorization = `Bearer ${authState.token}`
  }
  return config
})

// 响应拦截：401 → 清登录态 → 跳登录
http.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && router.currentRoute.value.name !== 'login') {
      clearAuth()
      router.push({ name: 'login' })
    }
    return Promise.reject(err)
  }
)

export const authApi = {
  register: (username, password) => http.post('/auth/register', { username, password }).then(r => r.data),
  login: (username, password) => http.post('/auth/login', { username, password }).then(r => r.data),
  me: () => http.get('/auth/me').then(r => r.data),
}

export const resumeApi = {
  upload: (file) => {
    const form = new FormData()
    form.append('file', file)
    return http.post('/resume/upload', form).then(r => r.data)
  },
}

export const interviewApi = {
  roles: () => http.get('/interview/roles').then(r => r.data),
  start: (jobTitle, role, resumeId = '', level = {}) =>
    http.post('/interview/start', {
      job_title: jobTitle,
      role,
      resume_id: resumeId,
      difficulty: level.difficulty || 'medium',
      education: level.education || 'any',
    }).then(r => r.data),
  end: (sessionId, expressionSeq = []) =>
    http.post(`/interview/${sessionId}/end`, { expression_seq: expressionSeq }).then(r => r.data),
}

export const historyApi = {
  list: () => http.get('/history').then(r => r.data),
  detail: (id) => http.get(`/history/${id}`).then(r => r.data),
  remove: (id) => http.delete(`/history/${id}`).then(r => r.data),
}

export const exportApi = {
  export: (reportId, format) =>
    http.post(`/report/${reportId}/export`, null, { params: { format } }).then(r => r.data),
  downloadUrl: (reportId, format) => `/api/report/${reportId}/download?format=${format}`,
}

// 触发浏览器下载（带 token 的下载链接无法直接 <a href>，用 fetch → blob）
export async function downloadReport(reportId, format) {
  // 中性 URL（无扩展名）+ 格式走请求头：避免 IDM/下载管理器按 .pdf 后缀抢先接管
  const url = `/report/${reportId}/file`
  const res = await http.get(url, {
    responseType: 'blob',
    headers: { 'X-Export-Format': format },
  })
  const blobUrl = URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = blobUrl
  a.download = `面试评估报告_${reportId}.${format}`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(blobUrl)
}

export const industryApi = {
  research: (industryName) => http.post('/industry/research', { industry_name: industryName }).then(r => r.data),
  history: () => http.get('/industry/history').then(r => r.data),
  detail: (id) => http.get(`/industry/history/${id}`).then(r => r.data),
  remove: (id) => http.delete(`/industry/history/${id}`).then(r => r.data),
}

export const projectApi = {
  channels: () => http.post('/project/channels').then(r => r.data),
  script: (projectName, description = '') =>
    http.post('/project/script', { project_name: projectName, description }).then(r => r.data),
  history: () => http.get('/project/history').then(r => r.data),
  detail: (id) => http.get(`/project/history/${id}`).then(r => r.data),
  remove: (id) => http.delete(`/project/history/${id}`).then(r => r.data),
}

export const adminApi = {
  users: () => http.get('/admin/users').then(r => r.data),
  deleteUser: (id) => http.delete(`/admin/users/${id}`).then(r => r.data),
  sessions: () => http.get('/admin/sessions').then(r => r.data),
  sessionDetail: (id) => http.get(`/admin/sessions/${id}`).then(r => r.data),
  deleteSession: (id) => http.delete(`/admin/sessions/${id}`).then(r => r.data),
  industry: () => http.get('/admin/industry').then(r => r.data),
  deleteIndustry: (id) => http.delete(`/admin/industry/${id}`).then(r => r.data),
  project: () => http.get('/admin/project').then(r => r.data),
  deleteProject: (id) => http.delete(`/admin/project/${id}`).then(r => r.data),
}

export default http
