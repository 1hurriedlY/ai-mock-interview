/* 前端路由：
 * - '/' 官网落地页（公开）→ 未登录看产品介绍，点「开始使用」→ /login；已登录访问自动进 /home
 * - '/home' 登录后的面试准备台
 * - 其余业务页需登录，管理页需管理员
 */
import { createRouter, createWebHistory } from 'vue-router'
import { authState } from '../store/auth'

const routes = [
  { path: '/', name: 'landing', component: () => import('../views/LandingView.vue'), meta: { public: true } },
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
  { path: '/home', name: 'home', component: () => import('../views/HomeView.vue') },
  { path: '/interview/:id?', name: 'interview', component: () => import('../views/InterviewView.vue') },
  { path: '/report/:id', name: 'report', component: () => import('../views/ReportView.vue') },
  { path: '/history', name: 'history', component: () => import('../views/HistoryView.vue') },
  { path: '/industry', name: 'industry', component: () => import('../views/IndustryView.vue') },
  { path: '/project', name: 'project', component: () => import('../views/ProjectView.vue') },
  { path: '/settings', name: 'settings', component: () => import('../views/SettingsView.vue') },
  { path: '/admin', name: 'admin', component: () => import('../views/AdminView.vue'), meta: { admin: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

// 登录守卫：业务页需登录；落地页/登录页公开；已登录访问落地页 → 直接进工作台
router.beforeEach((to) => {
  const logged = Boolean(authState.token)
  if (to.name === 'landing' && logged) {
    return { name: 'home' }
  }
  if (!to.meta.public && !logged) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && logged) {
    return { name: 'home' }
  }
  if (to.meta.admin && !authState.isAdmin) {
    return { name: 'home' }
  }
  return true
})

export default router
