import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/layout/MainLayout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '仪表盘', icon: 'Odometer' }
      },
      {
        path: 'materials',
        name: 'Materials',
        component: () => import('@/views/Materials.vue'),
        meta: { title: '物料管理', icon: 'Box' }
      },
      {
        path: 'inventory',
        name: 'Inventory',
        component: () => import('@/views/Inventory.vue'),
        meta: { title: '库存管理', icon: 'Goods' }
      },
      {
        path: 'warnings',
        name: 'Warnings',
        component: () => import('@/views/Warnings.vue'),
        meta: { title: '预警中心', icon: 'Warning' }
      },
      {
        path: 'operations',
        name: 'Operations',
        component: () => import('@/views/Operations.vue'),
        meta: { title: '操作记录', icon: 'List' }
      },
      {
        path: 'stocktake',
        name: 'Stocktake',
        component: () => import('@/views/StocktakeList.vue'),
        meta: { title: '盘点任务管理', icon: 'Finished' }
      },
      {
        path: 'stocktake/create',
        name: 'StocktakeCreate',
        component: () => import('@/views/StocktakeCreate.vue'),
        meta: { title: '创建盘点任务', icon: 'Plus', hidden: true }
      },
      {
        path: 'stocktake/:id',
        name: 'StocktakeDetail',
        component: () => import('@/views/StocktakeDetail.vue'),
        meta: { title: '盘点任务详情', icon: 'View', hidden: true }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/Users.vue'),
        meta: { title: '用户管理', icon: 'User', roles: ['admin'] }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()

  if (to.meta.requiresAuth !== false) {
    if (!userStore.token) {
      ElMessage.warning('请先登录')
      return next({ path: '/login', query: { redirect: to.fullPath } })
    }
    if (!userStore.userInfo) {
      try {
        await userStore.fetchUserInfo()
      } catch (e) {
        return next('/login')
      }
    }
    if (to.meta.roles && !to.meta.roles.includes(userStore.userInfo.role) && userStore.userInfo.role !== 'admin') {
      ElMessage.error('权限不足')
      return next('/dashboard')
    }
  } else {
    if (userStore.token && to.path === '/login') {
      return next('/')
    }
  }
  next()
})

export default router
