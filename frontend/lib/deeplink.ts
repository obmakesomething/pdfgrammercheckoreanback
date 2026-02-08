export const TOSS_MINIAPP_NAME = 'pdfgrammercheckorean'
export const TOSS_DEEP_LINK = `intoss://${TOSS_MINIAPP_NAME}`

export function openDeepLink(url: string): void {
  // NOTE: Browsers may block scheme navigations without user gesture.
  // We still attempt it, and provide a manual button in UI.
  window.location.href = url
}

