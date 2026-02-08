function getErrorMessageFromJson(data: unknown): string | null {
  if (!data || typeof data !== 'object') return null
  const record = data as Record<string, unknown>
  if (typeof record.message === 'string') return record.message
  if (typeof record.error === 'string') return record.error
  return null
}

function toInt(value: unknown, fallback: number): number {
  const n = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(n)) return fallback
  return Math.trunc(n)
}

type FetchCreditsBalanceParams = {
  apiBaseUrl: string
  userId: string
  fetchImpl?: typeof fetch
}

export async function fetchCreditsBalance({
  apiBaseUrl,
  userId,
  fetchImpl = fetch,
}: FetchCreditsBalanceParams): Promise<number> {
  const url = new URL('/api/credits/balance', apiBaseUrl)
  url.searchParams.set('user_id', userId)

  const response = await fetchImpl(url.toString(), { method: 'GET' })
  const contentType = response.headers.get('Content-Type') || ''

  if (!response.ok) {
    if (contentType.includes('application/json')) {
      const data: unknown = await response.json().catch(() => null)
      const message =
        getErrorMessageFromJson(data) || response.statusText || '요청에 실패했습니다.'
      throw new Error(message)
    }
    const text = await response.text().catch(() => '')
    throw new Error(text || response.statusText || '요청에 실패했습니다.')
  }

  const data: unknown = await response.json().catch(() => null)
  if (!data || typeof data !== 'object') throw new Error('서버 응답이 올바르지 않습니다.')
  const record = data as Record<string, unknown>
  if (record.status !== 'success') {
    throw new Error(getErrorMessageFromJson(data) || '요청에 실패했습니다.')
  }

  return toInt(record.balance, 0)
}

type GrantIapOrderParams = {
  apiBaseUrl: string
  userId: string
  orderId: string
  sku: string
  fetchImpl?: typeof fetch
}

export async function grantIapOrder({
  apiBaseUrl,
  userId,
  orderId,
  sku,
  fetchImpl = fetch,
}: GrantIapOrderParams): Promise<{
  granted: boolean
  creditsAdded: number
  balance: number
}> {
  const url = new URL('/api/iap/grant', apiBaseUrl)

  const response = await fetchImpl(url.toString(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: userId,
      order_id: orderId,
      sku,
    }),
  })

  const contentType = response.headers.get('Content-Type') || ''

  if (!response.ok) {
    if (contentType.includes('application/json')) {
      const data: unknown = await response.json().catch(() => null)
      const message =
        getErrorMessageFromJson(data) || response.statusText || '요청에 실패했습니다.'
      throw new Error(message)
    }
    const text = await response.text().catch(() => '')
    throw new Error(text || response.statusText || '요청에 실패했습니다.')
  }

  const data: unknown = await response.json().catch(() => null)
  if (!data || typeof data !== 'object') throw new Error('서버 응답이 올바르지 않습니다.')
  const record = data as Record<string, unknown>
  if (record.status !== 'success') {
    throw new Error(getErrorMessageFromJson(data) || '요청에 실패했습니다.')
  }

  return {
    granted: Boolean(record.granted),
    creditsAdded: toInt(record.credits_added, 0),
    balance: toInt(record.balance, 0),
  }
}

