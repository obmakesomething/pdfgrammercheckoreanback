import { useMemo, useRef, useState } from 'react'
import { saveBase64Data, showFullScreenAd } from '@apps-in-toss/web-framework'
import { checkPdf, uint8ArrayToBase64 } from './lib/checkPdf'

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
    resultBytesRef.current = null

    try {
      const result = await checkPdf({
        apiBaseUrl,
        file: selectedFile,
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
        })
        setMessage(result.message)
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
                <div className="resultLabel">예상 결제</div>
                <div className="resultValue">
                  {paywall.priceWon.toLocaleString()}원
                </div>
              </div>
            </div>

            <div className="notice info" role="note">
              50,000자까지는 광고 시청 후 무료입니다. 초과분은 10,000자당 100원으로 계산됩니다.
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
