import { createRouter, createWebHistory } from 'vue-router'

import Home from '@/views/Home.vue'

const routes = [
  { path: '/', redirect: '/home/alerts' },
  { path: '/login', name: 'Login', component: () => import('@/views/LoginPage.vue') },
  {
    path: '/home',
    redirect: '/home/alerts',
    name: 'Home',
    component: Home,
    meta: { requiresAuth: true },
    children: [
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue'), meta: { requiresAuth: true } },
      { path: 'alerts/:alert_id?', name: 'Alerts', component: () => import('@/views/Alerts.vue'), meta: { requiresAuth: true } },
      { path: 'maintenance', name: 'Maintenance', component: () => import('@/views/Maintenance.vue'), meta: { requiresAuth: true } },
      { path: 'users/:user_id?', name: 'Users', component: () => import('@/views/Users.vue'), meta: { requiresAuth: true } },
      { path: 'schedules', name: 'Schedules', component: () => import('@/views/Schedules.vue'), meta: { requiresAuth: true } },
      { path: 'pipelines', name: 'Pipelines', component: () => import('@/views/Pipelines.vue'), meta: { requiresAuth: true } },
      { path: 'templates', name: 'Templates', component: () => import('@/views/Templates.vue'), meta: { requiresAuth: true } }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    sessionStorage.setItem('redirect', to.fullPath)
    next({
      name: 'Login'
    })
  } else if (to.name === 'Login' && token) {
    next({ name: 'Home' })
  } else {
    next()
  }
})

export default router
