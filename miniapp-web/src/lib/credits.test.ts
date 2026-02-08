import { describe, expect, it } from 'vitest'

import { fetchCreditsBalance, grantIapOrder } from './credits'

describe('credits API', () => {
  it('fetchCreditsBalance returns balance from JSON', async () => {
    const mockFetch: typeof fetch = async () => {
      return new Response(JSON.stringify({ status: 'success', balance: 7 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }

    await expect(
      fetchCreditsBalance({
        apiBaseUrl: 'https://api.example.com',
        userId: 'device-1',
        fetchImpl: mockFetch,
      })
    ).resolves.toBe(7)
  })

  it('grantIapOrder returns grant result from JSON', async () => {
    const mockFetch: typeof fetch = async () => {
      return new Response(
        JSON.stringify({
          status: 'success',
          granted: true,
          credits_added: 5,
          balance: 12,
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }
      )
    }

    const result = await grantIapOrder({
      apiBaseUrl: 'https://api.example.com',
      userId: 'device-1',
      orderId: 'order-1',
      sku: 'CREDIT_5',
      fetchImpl: mockFetch,
    })

    expect(result.granted).toBe(true)
    expect(result.creditsAdded).toBe(5)
    expect(result.balance).toBe(12)
  })
})

