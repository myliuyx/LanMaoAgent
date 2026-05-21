import { defineStore } from 'pinia'
import { ref } from 'vue'
import router from '@/router'

export const useAppStore = defineStore('app', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const isLoggedIn = ref<boolean>(!!localStorage.getItem('token'))
  const userInfo = ref<{ id: number; username: string; role: string } | null>(null)
  // tokenVerified 标记：避免每次路由跳转都调 authApi.verify()
  const tokenVerified = ref<boolean>(false)

  const setToken = (newToken: string) => {
    token.value = newToken
    isLoggedIn.value = true
    localStorage.setItem('token', newToken)
    tokenVerified.value = true
  }

  const setUserInfo = (info: { id: number; username: string; role: string }) => {
    userInfo.value = info
  }

  const logout = () => {
    token.value = ''
    isLoggedIn.value = false
    userInfo.value = null
    tokenVerified.value = false
    localStorage.removeItem('token')
    router.push('/login')
  }

  return {
    token,
    isLoggedIn,
    userInfo,
    tokenVerified,
    setToken,
    setUserInfo,
    logout,
  }
})
