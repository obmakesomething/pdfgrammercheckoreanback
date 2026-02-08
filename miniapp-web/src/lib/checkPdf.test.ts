import { describe, expect, it } from 'vitest'

import { checkPdf, extractFileNameFromContentDisposition, parseErrorsFoundHeader, uint8ArrayToBase64 } from './checkPdf'

describe('parseErrorsFoundHeader', () => {
  it('parses X-Errors-Found header', () => {
    const headers = new Headers({ 'X-Errors-Found': '17' })
    expect(parseErrorsFoundHeader(headers)).toBe(17)
  })

  it('returns null when missing', () => {
    const headers = new Headers()
    expect(parseErrorsFoundHeader(headers)).toBeNull()
  })
})

describe('extractFileNameFromContentDisposition', () => {
  it('prefers filename* when present', () => {
    const header = "attachment; filename=\"fallback.pdf\"; filename*=UTF-8''%ED%85%8C%EC%8A%A4%ED%8A%B8_%EB%A7%9E%EC%B6%A4%EB%B2%95%EA%B2%80%EC%82%AC.pdf"
    expect(extractFileNameFromContentDisposition(header)).toBe('테스트_맞춤법검사.pdf')
  })

  it('uses filename when filename* is absent', () => {
    const header = 'attachment; filename="grammar_checked.pdf"'
    expect(extractFileNameFromContentDisposition(header)).toBe('grammar_checked.pdf')
  })
})

describe('uint8ArrayToBase64', () => {
  it('encodes bytes to base64', () => {
    const bytes = new Uint8Array([0x48, 0x69]) // "Hi"
    expect(uint8ArrayToBase64(bytes)).toBe('SGk=')
  })
})

describe('checkPdf', () => {
  it('uploads a PDF and returns the corrected bytes', async () => {
    const file = new File([new Uint8Array([0x25, 0x50, 0x44, 0x46])], 'input.pdf', {
      type: 'application/pdf',
    })

    const mockFetch: typeof fetch = async () => {
      return new Response(new Uint8Array([1, 2, 3]), {
        status: 200,
        headers: {
          'Content-Type': 'application/pdf',
          'X-Errors-Found': '3',
          'Content-Disposition': 'attachment; filename="grammar_checked.pdf"',
        },
      })
    }

    const result = await checkPdf({
      apiBaseUrl: 'https://api.example.com',
      file,
      fetchImpl: mockFetch,
    })

    expect(result.type).toBe('ok')
    if (result.type !== 'ok') throw new Error('expected ok')
    expect(result.errorsFound).toBe(3)
    expect(result.fileName).toBe('grammar_checked.pdf')
    expect(Array.from(result.bytes)).toEqual([1, 2, 3])
  })

  it('throws a readable error when the server responds with JSON error', async () => {
    const file = new File([new Uint8Array([0x25, 0x50, 0x44, 0x46])], 'input.pdf', {
      type: 'application/pdf',
    })

    const mockFetch: typeof fetch = async () => {
      return new Response(JSON.stringify({ status: 'error', message: 'bad request' }), {
        status: 400,
        headers: {
          'Content-Type': 'application/json',
        },
      })
    }

    await expect(
      checkPdf({
        apiBaseUrl: 'https://api.example.com',
        file,
        fetchImpl: mockFetch,
      })
    ).rejects.toThrow('bad request')
  })

  it('returns payment_required details when the server responds with 402', async () => {
    const file = new File([new Uint8Array([0x25, 0x50, 0x44, 0x46])], 'input.pdf', {
      type: 'application/pdf',
    })

    const mockFetch: typeof fetch = async () => {
      return new Response(
        JSON.stringify({
          status: 'payment_required',
          message: '결제가 필요합니다.',
          char_count: 50001,
          free_char_limit: 50000,
          unit_chars: 10000,
          unit_price_won: 100,
          required_units: 1,
          price_won: 100,
        }),
        {
          status: 402,
          headers: {
            'Content-Type': 'application/json',
          },
        }
      )
    }

    const result = await checkPdf({
      apiBaseUrl: 'https://api.example.com',
      file,
      fetchImpl: mockFetch,
    })

    expect(result.type).toBe('payment_required')
    if (result.type !== 'payment_required') throw new Error('expected payment_required')
    expect(result.message).toBe('결제가 필요합니다.')
    expect(result.charCount).toBe(50001)
    expect(result.freeCharLimit).toBe(50000)
    expect(result.unitChars).toBe(10000)
    expect(result.unitPriceWon).toBe(100)
    expect(result.requiredUnits).toBe(1)
    expect(result.priceWon).toBe(100)
  })
})
