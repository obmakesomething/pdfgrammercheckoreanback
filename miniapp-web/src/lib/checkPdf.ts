export function parseErrorsFoundHeader(headers: Headers): number | null {
  const raw = headers.get('X-Errors-Found')
  if (!raw) return null

  const n = Number(raw)
  if (!Number.isFinite(n)) return null
  return n
}

export function parseCharCountHeader(headers: Headers): number | null {
  const raw = headers.get('X-Char-Count')
  if (!raw) return null

  const n = Number(raw)
  if (!Number.isFinite(n)) return null
  return n
}

export function extractFileNameFromContentDisposition(header: string | null): string |null {
  if (!header) return null

  const filenameStarMatch = header.match(/filename\*\s*=\s*([^;]+)/i)
  if (filenameStarMatch) {
    const raw = filenameStarMatch[1].trim().replace(/^"|"$/g, '')

    // Common form: UTF-8''%E3%85%87...
    const parts = raw.split("''")
    const encoded = parts.length > 1 ? parts.slice(1).join("''") : raw

    try {
      return decodeURIComponent(encoded)
    } catch {
      // If decoding fails, fall back to raw.
      return encoded
    }
  }

  const filenameMatch = header.match(/filename\s*=\s*([^;]+)/i)
  if (filenameMatch) {
    return filenameMatch[1].trim().replace(/^"|"$/g, '')
  }

  return null
}

export function uint8ArrayToBase64(bytes: Uint8Array): string {
  // Avoid stack overflow from huge spreads.
  const chunkSize = 0x8000
  let binary = ''
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize))
  }
  return btoa(binary)
}

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

export type CheckPdfOkResult = {
  type: 'ok'
  bytes: Uint8Array
  errorsFound: number | null
  fileName: string
  charCount: number | null
}

export type CheckPdfPaymentRequiredResult = {
  type: 'payment_required'
  message: string
  charCount: number
  freeCharLimit: number
  unitChars: number
  unitPriceWon: number
  requiredUnits: number
  priceWon: number
  creditsBalance: number
}

export type CheckPdfResult = CheckPdfOkResult | CheckPdfPaymentRequiredResult

function parsePaymentRequiredJson(data: unknown): CheckPdfPaymentRequiredResult | null {
  if (!data || typeof data !== 'object') return null
  const record = data as Record<string, unknown>
  if (record.status !== 'payment_required') return null

  return {
    type: 'payment_required',
    message: typeof record.message === 'string' ? record.message : '결제가 필요합니다.',
    charCount: toInt(record.char_count, 0),
    freeCharLimit: toInt(record.free_char_limit, 0),
    unitChars: toInt(record.unit_chars, 0),
    unitPriceWon: toInt(record.unit_price_won, 0),
    requiredUnits: toInt(record.required_units, 0),
    priceWon: toInt(record.price_won, 0),
    creditsBalance: toInt(record.credits_balance, 0),
  }
}

type CheckPdfParams = {
  apiBaseUrl: string
  file: File
  deviceId?: string
  fetchImpl?: typeof fetch
}

function isLikelyNetworkError(error: unknown): boolean {
  if (!(error instanceof Error)) return false
  if (error.name === 'AbortError') return true
  if (error instanceof TypeError) return true

  const msg = error.message.toLowerCase()
  return (
    msg.includes('failed to fetch') ||
    msg.includes('networkerror') ||
    msg.includes('load failed')
  )
}

export async function checkPdf({ apiBaseUrl, file, deviceId, fetchImpl = fetch }: CheckPdfParams): Promise<CheckPdfResult> {
  const url = new URL('/api/check-pdf', apiBaseUrl)

  const formData = new FormData()
  formData.append('pdf', file, file.name || 'input.pdf')
  if (deviceId) {
    formData.append('device_id', deviceId)
  }

  let response: Response
  try {
    response = await fetchImpl(url.toString(), {
      method: 'POST',
      body: formData,
    })
  } catch (error) {
    // Some app webviews intermittently fail with a transport-level fetch error.
    // Retry once before surfacing a user-facing error.
    if (!isLikelyNetworkError(error)) throw error

    try {
      response = await fetchImpl(url.toString(), {
        method: 'POST',
        body: formData,
      })
    } catch (retryError) {
      if (isLikelyNetworkError(retryError)) {
        throw new Error('네트워크 연결이 원활하지 않습니다. 잠시 후 다시 시도해주세요.')
      }
      throw retryError
    }
  }

  if (!response.ok) {
    const contentType = response.headers.get('Content-Type') || ''

    if (contentType.includes('application/json')) {
      const data: unknown = await response.json().catch(() => null)
      if (response.status === 402) {
        const paymentRequired = parsePaymentRequiredJson(data)
        if (paymentRequired) return paymentRequired
      }
      const message =
        getErrorMessageFromJson(data) || response.statusText || '요청에 실패했습니다.'
      throw new Error(message)
    }

    const text = await response.text().catch(() => '')
    throw new Error(text || response.statusText || '요청에 실패했습니다.')
  }

  const bytes = new Uint8Array(await response.arrayBuffer())
  const errorsFound = parseErrorsFoundHeader(response.headers)
  const charCount = parseCharCountHeader(response.headers)
  const fileName =
    extractFileNameFromContentDisposition(response.headers.get('Content-Disposition')) ||
    'grammar_checked.pdf'

  return {
    type: 'ok',
    bytes,
    errorsFound,
    fileName,
    charCount,
  }
}
