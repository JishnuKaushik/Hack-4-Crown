import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL

if (!baseURL) {
  throw new Error('VITE_API_BASE_URL is not set — check frontend/.env')
}

export const apiClient = axios.create({ baseURL })
