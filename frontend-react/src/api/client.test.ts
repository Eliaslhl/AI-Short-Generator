import { describe, expect, it } from 'vitest'
import client from './client'
import { authApi } from './index'

describe('session HTTP client', () => {
  it('uses credentialed requests without a global Bearer interceptor', () => {
    expect(client.defaults.withCredentials).toBe(true)
    const handlers = (client.interceptors.request as unknown as { handlers: unknown[] }).handlers
    expect(handlers).toHaveLength(0)
  })

  it('does not expose a browser JWT-to-session exchange helper', () => {
    expect(authApi).not.toHaveProperty('createSession')
  })
})
