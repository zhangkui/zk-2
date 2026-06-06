import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login, getCurrentUser, changePassword as apiChangePassword } from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => userInfo.value?.role === 'admin')

  async function doLogin(username, password) {
    const res = await login(username, password)
    token.value = res.access_token
    localStorage.setItem('token', res.access_token)
    await fetchUserInfo()
  }

  async function fetchUserInfo() {
    try {
      userInfo.value = await getCurrentUser()
    } catch (e) {
      logout()
      throw e
    }
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
  }

  async function changePassword(oldPassword, newPassword) {
    await apiChangePassword(oldPassword, newPassword)
  }

  return {
    token, userInfo, isLoggedIn, isAdmin,
    doLogin, fetchUserInfo, logout, changePassword
  }
})
