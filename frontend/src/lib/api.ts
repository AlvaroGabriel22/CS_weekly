import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('qwi_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  // Uploads: com FormData o navegador precisa definir o multipart/boundary
  // sozinho — o default 'application/json' quebraria o parse no backend (422).
  if (config.data instanceof FormData) {
    config.headers.delete?.('Content-Type')
    delete (config.headers as Record<string, unknown>)['Content-Type']
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('qwi_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
