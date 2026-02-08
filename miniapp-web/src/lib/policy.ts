export function shouldShowAdForCharCount(charCount: number | null, freeCharLimit: number): boolean {
  // Backward compatible: if server doesn't provide char count, default to showing ads.
  if (charCount == null) return true
  if (!Number.isFinite(charCount) || charCount < 0) return true
  return charCount <= freeCharLimit
}

