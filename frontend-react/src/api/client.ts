import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const client = axios.create({
  baseURL: API_URL,
  // The browser session is held in an HttpOnly cookie. Do not persist or attach
  // a JWT here: the only temporary Bearer use is explicit in authApi.createSession.
  withCredentials: true,
})

export default client
