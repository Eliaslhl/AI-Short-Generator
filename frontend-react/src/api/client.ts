import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const client = axios.create({
  baseURL: API_URL,
  // The browser session is held exclusively in an HttpOnly cookie.
  withCredentials: true,
})

export default client
