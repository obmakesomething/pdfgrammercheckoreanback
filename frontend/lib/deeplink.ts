export const TOSS_MINIAPP_NAME = 'pdfgrammercheckorean'

// For pre-release QA, set NEXT_PUBLIC_TOSS_DEPLOYMENT_ID to open intoss-private directly.
// For production release, keep it unset so it uses intoss://<appName>.
const tossDeploymentId =
  typeof process !== 'undefined'
    ? process.env.NEXT_PUBLIC_TOSS_DEPLOYMENT_ID?.trim()
    : undefined

export const TOSS_DEEP_LINK = tossDeploymentId
  ? `intoss-private://${TOSS_MINIAPP_NAME}?_deploymentId=${encodeURIComponent(tossDeploymentId)}`
  : `intoss://${TOSS_MINIAPP_NAME}`

export const TOSS_INSTALL_URL = 'https://toss.im'

export function openDeepLink(url: string): void {
  if (typeof window === 'undefined') return

  // NOTE: Browsers may block scheme navigations without user gesture.
  // Try multiple navigation strategies to maximize open success.
  const iframe = document.createElement('iframe')
  iframe.style.display = 'none'
  iframe.src = url
  document.body.appendChild(iframe)

  window.setTimeout(() => {
    try {
      iframe.remove()
    } catch {
      // no-op
    }
  }, 1200)

  window.location.href = url
}
