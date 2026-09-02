/* 前端路由：登录页 + 主流程视图，带登录守卫。
 * - 未登录访问业务页 → 重定向 /login
 * - 已登录访问 /login → 重定向首页
 */
import { createRouter, createWebHistory } from 'vue-router'
import { authState } from '../store/auth'

const routes = [
  { path: '/', redirect: '/home' },
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { public: true } },
  { path: '/home', name: 'home', component: () => import('../views/HomeView.vue') },
  { path: '/interview/:id?', name: 'interview', component: () => import('../views/InterviewView.vue') },
  { path: '/report/:id', name: 'report', component: () => import('../views/ReportView.vue') },
  { path: '/history', name: 'history', component: () => import('../views/HistoryView.vue') },
  { path: '/industry', name: 'industry', component: () => import('../views/IndustryView.vue') },
  { path: '/project', name: 'project', component: () => import('../views/ProjectView.vue') },
  { path: '/admin', name: 'admin', component: () => import('../views/AdminView.vue'), meta: { admin: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 登录守卫：业务页需登录，登录页对已登录用户重定向回首页；管理页需管理员
router.beforeEach((to) => {
  const logged = Boolean(authState.token)
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
