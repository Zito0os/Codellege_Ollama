import { useEffect, useRef, useState } from 'react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const MAX_FILE_SIZE = 10 * 1024 * 1024

function App() {
  const [image, setImage] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [result, setResult] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [loadingSeconds, setLoadingSeconds] = useState(0)
  const [progressLabel, setProgressLabel] = useState('Enviando la imagen a Ollama…')
  const abortControllerRef = useRef(null)

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrl])

  useEffect(() => {
    if (!isLoading) return undefined

    const timer = window.setInterval(() => {
      setLoadingSeconds((seconds) => seconds + 1)
    }, 1000)
    return () => window.clearInterval(timer)
  }, [isLoading])

  function selectImage(file) {
    setError('')
    setResult('')

    if (!file) return
    if (!file.type.startsWith('image/')) {
      setImage(null)
      setPreviewUrl('')
      setError('Elige un archivo de imagen, como JPG, PNG o WEBP.')
      return
    }
    if (file.size > MAX_FILE_SIZE) {
      setImage(null)
      setPreviewUrl('')
      setError('La imagen debe pesar menos de 10 MB.')
      return
    }

    setImage(file)
    setPreviewUrl(URL.createObjectURL(file))
  }

  function handleDrop(event) {
    event.preventDefault()
    setIsDragging(false)
    selectImage(event.dataTransfer.files[0])
  }

  async function analyzeImage(event) {
    event.preventDefault()
    if (!image || isLoading) return

    setIsLoading(true)
    setError('')
    setResult('')
    setLoadingSeconds(0)
    setProgressLabel('Enviando la imagen a Ollama…')

    const formData = new FormData()
    formData.append('imagen', image)
    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      const response = await fetch(`${API_URL}/analizar/stream`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'No se pudo analizar esta imagen.')
      }

      if (!response.body) throw new Error('El navegador no pudo iniciar la respuesta en directo.')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let pending = ''
      let fullText = ''
      let streamFinished = false

      function handleStreamLine(line) {
        if (!line.trim()) return
        const eventData = JSON.parse(line)

        if (eventData.type === 'token') {
          fullText += eventData.content
          setResult(fullText)
          setProgressLabel('Ollama está generando el análisis…')
        } else if (eventData.type === 'error') {
          throw new Error(eventData.detail)
        } else if (eventData.type === 'status') {
          setProgressLabel(eventData.message)
        } else if (eventData.type === 'done') {
          streamFinished = true
        }
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        pending += decoder.decode(value, { stream: true })
        const lines = pending.split('\n')
        pending = lines.pop() || ''
        lines.forEach(handleStreamLine)
      }

      pending += decoder.decode()
      handleStreamLine(pending)

      if (!streamFinished) throw new Error('La conexión terminó antes de completar el análisis.')
      if (!fullText) setResult('El modelo no devolvió ingredientes reconocibles.')
    } catch (requestError) {
      setError(
        requestError.name === 'AbortError'
          ? 'Análisis cancelado.'
          : requestError.message ||
              'No se pudo conectar con la API. Comprueba que FastAPI y Ollama estén activos.',
      )
    } finally {
      abortControllerRef.current = null
      setIsLoading(false)
    }
  }

  function cancelAnalysis() {
    abortControllerRef.current?.abort()
  }

  function clearImage() {
    setImage(null)
    setPreviewUrl('')
    setResult('')
    setError('')
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Despensa, inicio">
          <span className="brand-mark" aria-hidden="true">
            <span />
            <span />
          </span>
          <span>despensa<span className="brand-period">.</span></span>
        </a>
        <span className="connection-status"><span /> Análisis local</span>
      </header>

      <section className="intro" aria-labelledby="page-title">
        <p className="eyebrow">INVENTARIO VISUAL <span> / </span> 01</p>
        <h1 id="page-title">¿Qué hay en tu<br className="desktop-break" /> refrigerador?</h1>
        <p className="intro-copy">
          Una foto basta para reconocer tus ingredientes. Revisa lo que tienes antes de hacer la compra.
        </p>
      </section>

      <form className="workspace" onSubmit={analyzeImage}>
        <section className="image-panel" aria-labelledby="image-heading">
          <div className="panel-heading">
            <div>
              <span className="step-number">01</span>
              <h2 id="image-heading">Tu fotografía</h2>
            </div>
            {image && (
              <button className="text-button" type="button" onClick={clearImage}>
                Quitar imagen
              </button>
            )}
          </div>

          <div
            className={`drop-zone${isDragging ? ' is-dragging' : ''}${image ? ' has-image' : ''}`}
            onDragEnter={(event) => {
              event.preventDefault()
              setIsDragging(true)
            }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={(event) => {
              if (!event.currentTarget.contains(event.relatedTarget)) setIsDragging(false)
            }}
            onDrop={handleDrop}
          >
            {previewUrl ? (
              <img className="image-preview" src={previewUrl} alt="Vista previa del refrigerador" />
            ) : (
              <div className="empty-preview" aria-hidden="true">
                <div className="fridge-illustration">
                  <span className="fridge-top"><i /></span>
                  <span className="fridge-bottom"><i /></span>
                </div>
                <span className="preview-caption">VISTA PREVIA</span>
              </div>
            )}
            <input
              className="file-input"
              id="image-upload"
              type="file"
              accept="image/*"
              onChange={(event) => {
                const selectedFile = event.target.files[0]
                event.target.value = ''
                selectImage(selectedFile)
              }}
            />
            <label className="upload-link" htmlFor="image-upload">
              {image ? 'Cambiar fotografía' : 'Elegir fotografía'}
            </label>
            <p className="drop-hint">o arrastra una imagen aquí · JPG, PNG o WEBP · máx. 10 MB</p>
          </div>

          {image && (
            <div className="file-detail">
              <span className="file-indicator" aria-hidden="true" />
              <span className="file-name">{image.name}</span>
              <span className="file-size">{(image.size / (1024 * 1024)).toFixed(1)} MB</span>
            </div>
          )}
        </section>

        <section className="result-panel" aria-labelledby="result-heading" aria-live="polite">
          <div className="panel-heading">
            <div>
              <span className="step-number">02</span>
              <h2 id="result-heading">Ingredientes detectados</h2>
            </div>
            {result && !isLoading && <span className="result-tag">ANÁLISIS LISTO</span>}
          </div>

          <div className={`result-body${result ? ' has-result' : ''}`}>
            {isLoading && !result ? (
              <div className="loading-state">
                <span className="loading-mark" aria-hidden="true" />
                <p>Revisando lo que hay en tu refrigerador…</p>
                <span>Puede tardar unos segundos</span>
              </div>
            ) : error ? (
              <div className="message-state error-state" role="alert">
                <span className="message-symbol" aria-hidden="true">!</span>
                <p>{error}</p>
              </div>
            ) : result ? (
              <div className="analysis-result">{result}</div>
            ) : (
              <div className="message-state empty-state">
                <span className="empty-symbol" aria-hidden="true">—</span>
                <p>El análisis aparecerá aquí.</p>
                <span>Incluye cantidades aproximadas y nivel de confianza.</span>
              </div>
            )}
          </div>

          {isLoading && (
            <div className="progress-section">
              <div className="progress-meta">
                <span>
                  {loadingSeconds >= 60 && !result
                    ? 'El modelo sigue trabajando; si tarda varios minutos, revisa Ollama y el modelo instalado.'
                    : loadingSeconds >= 20 && !result
                      ? 'El modelo está preparando la respuesta. La primera carga puede tardar más.'
                      : progressLabel}
                </span>
                <time>{loadingSeconds}s</time>
              </div>
              <div
                className="progress-track"
                role="progressbar"
                aria-label="Análisis de imagen en curso"
                aria-valuetext={`${loadingSeconds} segundos transcurridos`}
              >
                <span className="progress-indicator" />
              </div>
              <button className="cancel-button" type="button" onClick={cancelAnalysis}>
                Cancelar análisis
              </button>
            </div>
          )}

          <button className="analyze-button" type="submit" disabled={!image || isLoading}>
            <span>{isLoading ? 'Analizando' : 'Analizar fotografía'}</span>
            {!isLoading && <span className="button-arrow" aria-hidden="true">↗</span>}
          </button>
          <p className="privacy-note">La imagen se procesa localmente con Ollama.</p>
        </section>
      </form>

      <footer className="page-footer">
        <span>DESPENSA <span className="footer-divider">/</span> VISIÓN POR COMPUTADORA</span>
        <span>MODELO QWEN3-VL · 4B</span>
      </footer>
    </main>
  )
}

export default App