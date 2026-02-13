import { describe, expect, it } from 'vitest'

import { shouldShowAdForCharCount } from './policy'

describe('shouldShowAdForCharCount', () => {
  it('shows ads when charCount is missing (backward compatible)', () => {
    expect(shouldShowAdForCharCount(null, 50000)).toBe(true)
  })

  it('shows ads for free-tier docs', () => {
    expect(shouldShowAdForCharCount(0, 50000)).toBe(true)
    expect(shouldShowAdForCharCount(50000, 50000)).toBe(true)
  })

  it('does not show ads for paid-tier docs', () => {
    expect(shouldShowAdForCharCount(50001, 50000)).toBe(false)
  })
})

