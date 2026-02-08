import { useEffect, useMemo, useRef, useState } from 'react'
import { IAP, getDeviceId, saveBase64Data, showFullScreenAd, type IapProductListItem } from '@apps-in-toss/web-framework'
import { checkPdf, uint8ArrayToBase64 } from './lib/checkPdf'
import { fetchCreditsBalance, grantIapOrder } from './lib/credits'

const DEFAULT_API_BASE_URL = 'https://api.pdfgrammercheckorean.site'
const MAX_PDF_SIZE_MB = 20

type Status = 'idle' | 'checking' | 'ready' | 'error'
type PaywallInfo = {
  message: string
  charCount: number
  freeCharLimit: number
  unitChars: number
  unitPriceWon: number
  requiredUnits: number
  priceWon: number
  creditsBalance: number
}

function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let n = bytes
  let i = 0
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024
    i++
  }
  return `${n.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

async function tryShowFullScreenAd(adGroupId?: string): Promise<void> {
  if (!adGroupId) return
  if (!showFullScreenAd.isSupported()) return

  await new Promise<void>((resolve) => {
    let done = false
    const handle: { cleanup?: () => void } = {}
    const finish = () => {
      if (done) return
      done = true
      handle.cleanup?.()
      resolve()
    }

    handle.cleanup = showFullScreenAd({
      options: { adGroupId },
      onEvent: (event) => {
        if (event.type === 'dismissed' || event.type === 'failedToShow') {
          finish()
        }
      },
      onError: () => finish(),
    })

    // Never block on ad events forever.
    window.setTimeout(() => finish(), 4000)
  })
}

function App() {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
  const adGroupId = import.meta.env.VITE_AD_GROUP_ID

  const [status, setStatus] = useState<Status>('idle')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [errorsFound, setErrorsFound] = useState<number | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [paywall, setPaywall] = useState<PaywallInfo | null>(null)
  const [deviceId, setDeviceId] = useState<string | null>(null)
  const [creditsBalance, setCreditsBalance] = useState<number | null>(null)
  const [iapProducts, setIapProducts] = useState<IapProductListItem[] | null>(null)
  const [iapLoading, setIapLoading] = useState(false)
  const [iapError, setIapError] = useState<string | null>(null)
  const [purchasingSku, setPurchasingSku] = useState<string | null>(null)

  const resultBytesRef = useRef<Uint8Array | null>(null)
  const resultFileNameRef = useRef<string>('grammar_checked.pdf')

  const fileTooLarge = useMemo(() => {
    if (!selectedFile) return false
    return selectedFile.size > MAX_PDF_SIZE_MB * 1024 * 1024
  }, [selectedFile])

  const handleSelectFile = (file: File | null) => {
    setSelectedFile(file)
    setStatus('idle')
    setErrorsFound(null)
    setMessage(null)
    setPaywall(null)
    setCreditsBalance(null)
    setIapProducts(null)
    setIapError(null)
    resultBytesRef.current = null
    resultFileNameRef.current = 'grammar_checked.pdf'

    if (file && file.size > MAX_PDF_SIZE_MB * 1024 * 1024) {
      setStatus('error')
      setMessage(`파일이 너무 커요. ${MAX_PDF_SIZE_MB}MB 이하의 PDF만 업로드할 수 있어요.`)
    }
  }

  const handleCheck = async () => {
    if (!selectedFile) return
    if (fileTooLarge) return

    setStatus('checking')
    setMessage(null)
    setErrorsFound(null)
    setPaywall(null)
    setIapProducts(null)
    setIapError(null)
    resultBytesRef.current = null

    try {
      const result = await checkPdf({
        apiBaseUrl,
        file: selectedFile,
        deviceId: deviceId || undefined,
      })

      if (result.type === 'payment_required') {
        setStatus('error')
        setPaywall({
          message: result.message,
          charCount: result.charCount,
          freeCharLimit: result.freeCharLimit,
          unitChars: result.unitChars,
          unitPriceWon: result.unitPriceWon,
          requiredUnits: result.requiredUnits,
          priceWon: result.priceWon,
          creditsBalance: result.creditsBalance,
        })
        setMessage(result.message)
        setCreditsBalance(result.creditsBalance)
        return
      }

      resultBytesRef.current = result.bytes
      resultFileNameRef.current = result.fileName

      // Best-effort ad (optional) before revealing the result.
      try {
        await tryShowFullScreenAd(adGroupId)
      } catch {
        // ignore
      }

      setErrorsFound(result.errorsFound)
      setStatus('ready')
      setMessage('검사가 완료되었습니다.')
    } catch (err) {
      const msg = err instanceof Error ? err.message : '요청 중 오류가 발생했습니다.'
      setStatus('error')
      setMessage(msg)
    }
  }

  const handleSave = async () => {
    const bytes = resultBytesRef.current
    if (!bytes) return

    setSaving(true)
    setMessage(null)

    const fileName = resultFileNameRef.current || 'grammar_checked.pdf'

    try {
      const base64 = uint8ArrayToBase64(bytes)
      await saveBase64Data({
        data: base64,
        fileName,
        mimeType: 'application/pdf',
      })
      setMessage('결과 PDF를 저장했습니다.')
    } catch (err) {
      // Fallback: browser download (useful in local dev and some webviews).
      try {
        // TS note: BlobPart doesn't accept SharedArrayBuffer, but our data is effectively ArrayBuffer-backed.
        const arrayBuffer = bytes.buffer.slice(
          bytes.byteOffset,
          bytes.byteOffset + bytes.byteLength
        ) as ArrayBuffer
        const blob = new Blob([arrayBuffer], { type: 'application/pdf' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = fileName
        document.body.appendChild(a)
        a.click()
        a.remove()
        URL.revokeObjectURL(url)
        setMessage('결과 PDF 다운로드를 시작했습니다.')
      } catch {
        const msg = err instanceof Error ? err.message : '저장에 실패했습니다.'
        setStatus('error')
        setMessage(msg)
      }
    } finally {
      setSaving(false)
    }
  }

  const reset = () => handleSelectFile(null)

  useEffect(() => {
    // `getDeviceId()` is used as a pseudonymous key for credit balance.
    try {
      const id = getDeviceId()
      if (id) setDeviceId(id)
    } catch {
      // ignore (local dev / unsupported env)
    }
  }, [])

  useEffect(() => {
    if (!paywall) return
    if (!deviceId) return

    let cancelled = false

    const loadBalance = async () => {
      try {
        const bal = await fetchCreditsBalance({ apiBaseUrl, userId: deviceId })
        if (cancelled) return
        setCreditsBalance(bal)
      } catch (err) {
        if (cancelled) return
        const msg = err instanceof Error ? err.message : '크레딧 정보를 불러오지 못했습니다.'
        setIapError(msg)
      }
    }

    const loadProducts = async () => {
      setIapLoading(true)
      setIapError(null)
      try {
        const list = await IAP.getProductItemList()
        if (cancelled) return
        if (!list) {
          setIapProducts([])
          setIapError('현재 토스 앱 버전에서는 인앱 결제를 지원하지 않아요. 앱 업데이트 후 다시 시도해주세요.')
          return
        }
        setIapProducts(list.products || [])
      } catch (err) {
        if (cancelled) return
        const msg = err instanceof Error ? err.message : '인앱 결제 상품을 불러오지 못했습니다.'
        setIapError(msg)
        setIapProducts([])
      } finally {
        if (!cancelled) setIapLoading(false)
      }
    }

    void loadBalance()
    void loadProducts()

    return () => {
      cancelled = true
    }
  }, [paywall, deviceId, apiBaseUrl])

  const handlePurchase = async (sku: string) => {
    if (!deviceId) {
      setMessage('기기 정보를 가져올 수 없어 결제를 진행할 수 없어요.')
      return
    }

    setPurchasingSku(sku)
    setMessage(null)

    let cleanup: (() => void) | undefined

    try {
      cleanup = IAP.createOneTimePurchaseOrder({
        options: {
          sku,
          processProductGrant: async ({ orderId }) => {
            try {
              await grantIapOrder({
                apiBaseUrl,
                userId: deviceId,
                orderId,
                sku,
              })
              try {
                await IAP.completeProductGrant({ params: { orderId } })
              } catch {
                // ignore (older app versions may not support it)
              }
              return true
            } catch {
              return false
            }
          },
        },
        onEvent: async (event) => {
          if (event.type !== 'success') return

          try {
            const bal = await fetchCreditsBalance({ apiBaseUrl, userId: deviceId })
            setCreditsBalance(bal)
            if (paywall && selectedFile && bal >= paywall.requiredUnits) {
              // Auto-retry once credits are sufficient.
              void handleCheck()
            }
          } catch {
            // ignore
          } finally {
            setPurchasingSku(null)
            cleanup?.()
            setMessage('크레딧 구매가 완료되었습니다.')
          }
        },
        onError: (error) => {
          const msg = error instanceof Error ? error.message : '결제 중 오류가 발생했습니다.'
          setPurchasingSku(null)
          cleanup?.()
          setMessage(msg)
        },
      })
    } catch (err) {
      const msg = err instanceof Error ? err.message : '결제 요청에 실패했습니다.'
      setPurchasingSku(null)
      cleanup?.()
      setMessage(msg)
    }
  }

  return (
    <div className="app">
      <header className="hero">
        <h1 className="title">PDF 한국어 맞춤법 검사기</h1>
        <p className="subtitle">
          PDF를 업로드하면, 오류가 표시된 PDF를 저장할 수 있어요.
        </p>
      </header>

      <main className="panel">
        <div className="field">
          <div className="labelRow">
            <span className="label">PDF 파일</span>
            <span className="meta">{MAX_PDF_SIZE_MB}MB 이하</span>
          </div>

          <div className="fileRow">
            <input
              id="pdf-file"
              className="fileInput"
              type="file"
              accept="application/pdf"
              onChange={(e) => handleSelectFile(e.currentTarget.files?.[0] ?? null)}
              disabled={status === 'checking'}
            />
            <label className="button secondary" htmlFor="pdf-file" aria-disabled={status === 'checking'}>
              PDF 선택
            </label>

            <div className="fileMeta" aria-live="polite">
              {selectedFile ? (
                <>
                  <div className="fileName">{selectedFile.name}</div>
                  <div className="fileSize">{formatBytes(selectedFile.size)}</div>
                </>
              ) : (
                <div className="hint">선택된 파일이 없습니다</div>
              )}
            </div>
          </div>
        </div>

        <div className="actions">
          <button
            className="button primary"
            type="button"
            onClick={handleCheck}
            disabled={!selectedFile || status === 'checking' || fileTooLarge}
          >
            {status === 'checking' ? '검사 중...' : '검사하기'}
          </button>
          <button
            className="button ghost"
            type="button"
            onClick={reset}
            disabled={status === 'checking'}
          >
            초기화
          </button>
        </div>

        {status === 'checking' && (
          <div className="progress" role="status" aria-label="검사 중">
            <div className="spinner" />
            <div className="progressText">PDF를 업로드하고 처리 중입니다</div>
          </div>
        )}

        {message && (
          <div className={`notice ${status === 'error' ? 'error' : 'info'}`} role="alert">
            {message}
          </div>
        )}

        {status === 'error' && paywall && (
          <div className="result" aria-label="결제 안내">
            <div className="resultGrid">
              <div className="resultItem">
                <div className="resultLabel">텍스트 글자 수</div>
                <div className="resultValue">
                  {paywall.charCount.toLocaleString()}자
                </div>
              </div>
              <div className="resultItem">
                <div className="resultLabel">필요 크레딧</div>
                <div className="resultValue">
                  {paywall.requiredUnits.toLocaleString()}개
                </div>
              </div>
            </div>

            <div className="notice info" role="note">
              50,000자까지는 광고 시청 후 무료입니다. 초과분은 10,000자당 100원으로 계산됩니다.
            </div>

            <div className="resultGrid">
              <div className="resultItem">
                <div className="resultLabel">내 크레딧</div>
                <div className="resultValue">
                  {(creditsBalance ?? 0).toLocaleString()}개
                </div>
              </div>
              <div className="resultItem">
                <div className="resultLabel">부족 크레딧</div>
                <div className="resultValue">
                  {Math.max(0, paywall.requiredUnits - (creditsBalance ?? 0)).toLocaleString()}개
                </div>
              </div>
            </div>

            <div className="productSection" aria-label="크레딧 구매">
              <div className="labelRow">
                <span className="label">크레딧 구매</span>
                {iapLoading && <span className="meta">불러오는 중...</span>}
              </div>

              {iapError && (
                <div className="notice error" role="alert">
                  {iapError}
                </div>
              )}

              {iapProducts && iapProducts.length > 0 ? (
                <div className="productList">
                  {iapProducts.map((p) => (
                    <div key={p.sku} className="productRow">
                      <div className="productMeta">
                        <div className="productName">{p.displayName}</div>
                        <div className="productDesc">{p.description}</div>
                      </div>
                      <button
                        className="button secondary"
                        type="button"
                        onClick={() => handlePurchase(p.sku)}
                        disabled={Boolean(purchasingSku)}
                      >
                        {purchasingSku === p.sku ? '결제 중...' : `${p.displayAmount} 구매`}
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="hint">
                  인앱 결제 상품이 없습니다. 콘솔에서 IAP 상품(SKU)을 등록해주세요.
                </div>
              )}
            </div>

            <button
              className="button primary"
              type="button"
              onClick={reset}
            >
              다른 PDF 선택
            </button>
          </div>
        )}

        {status === 'ready' && (
          <div className="result">
            <div className="resultGrid">
              <div className="resultItem">
                <div className="resultLabel">발견된 오류</div>
                <div className="resultValue">
                  {typeof errorsFound === 'number' ? errorsFound.toLocaleString() : '-'}
                </div>
              </div>
              <div className="resultItem">
                <div className="resultLabel">결과 파일명</div>
                <div className="resultValue mono">{resultFileNameRef.current}</div>
              </div>
            </div>

            <button
              className="button primary"
              type="button"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? '저장 중...' : '결과 PDF 저장'}
            </button>
          </div>
        )}
      </main>

      <footer className="footer">
        <p className="finePrint">개인정보(이메일 등)는 입력받지 않습니다.</p>
      </footer>
    </div>
  )
}

export default App
