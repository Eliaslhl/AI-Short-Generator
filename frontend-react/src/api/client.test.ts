import { describe, expect, it, vi } from 'vitest'
import client from './client'
import { authApi } from './index'

describe('session HTTP client', () => {
  it('uses credentialed requests without a global Bearer interceptor', () => {
    expect(client.defaults.withCredentials).toBe(true)
    const handlers = (client.interceptors.request as unknown as { handlers: unknown[] }).handlers
    expect(handlers).toHaveLength(0)
  })

  it('sends a temporary Bearer only for the explicit session exchange', async () => {
    const post = vi.spyOn(client, 'post').mockResolvedValue({ data: { expires_at: '2030-01-01T00:00:00Z' } })

    await authApi.createSession('temporary-jwt')

    expect(post).toHaveBeenCalledWith('/auth/session', undefined, {
      headers: { Authorization: 'Bearer temporary-jwt' },
    })
    post.mockRestore()
  })
})
