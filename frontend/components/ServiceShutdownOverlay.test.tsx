import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import ServiceShutdownOverlay from './ServiceShutdownOverlay'

vi.mock('@/lib/deeplink', () => {
  return {
    TOSS_DEEP_LINK: 'intoss://pdfgrammercheckorean',
    openDeepLink: vi.fn(),
  }
})

// Import after mock so the module binding is mocked.
import { openDeepLink, TOSS_DEEP_LINK } from '@/lib/deeplink'

describe('ServiceShutdownOverlay', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
    vi.useRealTimers()
  })

  it('renders the shutdown notice', () => {
    render(<ServiceShutdownOverlay />)
    expect(screen.getByText(/웹 서비스는 종료/i)).toBeInTheDocument()
  })

  it('attempts to open the Toss miniapp automatically', () => {
    render(<ServiceShutdownOverlay />)

    vi.advanceTimersByTime(1500)

    expect(openDeepLink).toHaveBeenCalledWith(TOSS_DEEP_LINK)
  })

  it('opens Toss miniapp when clicking the button', async () => {
    render(<ServiceShutdownOverlay />)

    fireEvent.click(screen.getByRole('button', { name: /toss.*열기/i }))
    expect(openDeepLink).toHaveBeenCalledWith(TOSS_DEEP_LINK)
  })
})
