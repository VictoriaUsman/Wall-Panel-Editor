import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
})

api.interceptors.response.use(
  r => r,
  err => {
    const isAuthPage = ['/login', '/register'].includes(window.location.pathname)
    if (err.response?.status === 401 && !isAuthPage) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// Lazy import to avoid circular dep
import { useAuthStore } from '../stores/authStore'

export default api
