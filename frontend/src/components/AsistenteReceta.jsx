import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition'
import { askRecipeAssistant } from '../api/assistant'

const KEYBOARD_PRESS = 'keyboard'

export default function AsistenteReceta({ recipe }) {
  const {
    transcript,
    listening,
    browserSupportsSpeechRecognition,
    isMicrophoneAvailable,
    resetTranscript,
  } = useSpeechRecognition()
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [voiceError, setVoiceError] = useState('')
  const toggleRef = useRef(null)
  const inputRef = useRef(null)
  const dialogRef = useRef(null)
  const endRef = useRef(null)
  const pendingStartRef = useRef(null)
  const dictationRequestedRef = useRef(false)
  const activePressRef = useRef(null)
  const releaseRequestedRef = useRef(false)
  const hadListeningRef = useRef(false)
  const transcriptRef = useRef('')
  const [pressed, setPressed] = useState(false)
  const isSecureContext = typeof window !== 'undefined' && window.isSecureContext
  const voiceUnavailable = !isSecureContext
    ? 'El dictado requiere una conexión segura (HTTPS o localhost).'
    : !browserSupportsSpeechRecognition
      ? 'Este navegador no es compatible con el dictado por voz.'
      : isMicrophoneAvailable === false
        ? 'No se pudo acceder al micrófono. Revisa los permisos del navegador.'
        : ''
  const question = [draft.trim(), transcript.trim()].filter(Boolean).join(' ')

  const closeChat = useCallback(() => {
    dictationRequestedRef.current = false
    activePressRef.current = null
    releaseRequestedRef.current = false
    hadListeningRef.current = false
    setPressed(false)
    void SpeechRecognition.stopListening()
    setOpen(false)
    toggleRef.current?.focus()
  }, [])

  useEffect(() => {
    if (!open) return undefined

    inputRef.current?.focus()

    function onKeyDown(event) {
      if (event.key === 'Escape') {
        event.preventDefault()
        closeChat()
        return
      }
      if (event.key !== 'Tab' || !dialogRef.current) return

      const focusables = dialogRef.current.querySelectorAll(
        'button:not(:disabled), input:not(:disabled), textarea:not(:disabled), [href], [tabindex]:not([tabindex="-1"])',
      )
      const list = [...focusables]
      if (!list.length) return

      const first = list[0]
      const last = list[list.length - 1]
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open, closeChat])

  useEffect(
    () => () => {
      dictationRequestedRef.current = false
      void SpeechRecognition.stopListening()
    },
    [],
  )

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  function startDictation(pressId) {
    if (
      voiceUnavailable ||
      activePressRef.current !== null ||
      pendingStartRef.current !== null ||
      loading
    ) {
      return
    }

    activePressRef.current = pressId
    setPressed(true)
    releaseRequestedRef.current = false
    dictationRequestedRef.current = true
    setVoiceError('')
    resetTranscript()
    const startTask = SpeechRecognition.startListening({
      language: 'es-MX',
      continuous: true,
    })
      .then(() => {
        if (!dictationRequestedRef.current) {
          return SpeechRecognition.stopListening()
        }
      })
      .catch(() => {
        dictationRequestedRef.current = false
        activePressRef.current = null
        setPressed(false)
        setVoiceError('No se pudo iniciar el micrófono. Revisa los permisos del navegador.')
      })
      .finally(() => {
        if (pendingStartRef.current === startTask) {
          pendingStartRef.current = null
        }
      })
    pendingStartRef.current = startTask
  }

  function stopDictation(pressId) {
    if (activePressRef.current !== pressId) return
    activePressRef.current = null
    setPressed(false)
    releaseRequestedRef.current = true
    dictationRequestedRef.current = false
    if (pendingStartRef.current === null) {
      void SpeechRecognition.stopListening()
    }
  }

  function handleMicPointerDown(event) {
    if (!event.isPrimary || (event.pointerType === 'mouse' && event.button !== 0)) return
    event.preventDefault()
    event.currentTarget.setPointerCapture(event.pointerId)
    startDictation(event.pointerId)
  }

  function handleMicPointerUp(event) {
    stopDictation(event.pointerId)
  }

  function handleMicKeyDown(event) {
    if ((event.key !== ' ' && event.key !== 'Enter') || event.repeat) return
    event.preventDefault()
    startDictation(KEYBOARD_PRESS)
  }

  function handleMicKeyUp(event) {
    if (event.key === ' ' || event.key === 'Enter') {
      event.preventDefault()
      stopDictation(KEYBOARD_PRESS)
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    await submitQuestion(question)
  }

  const submitQuestion = useCallback(async (nextQuestion) => {
    const normalizedQuestion = nextQuestion.trim()
    if (!normalizedQuestion || loading) return

    const nextMessages = [...messages, { role: 'user', content: normalizedQuestion }]
    dictationRequestedRef.current = false
    setMessages(nextMessages)
    setDraft('')
    resetTranscript()
    setError('')
    setLoading(true)
    if (listening) {
      await SpeechRecognition.stopListening()
    }

    const ingredients = recipe.ingredients
      .map((ingredient) => `${ingredient.name}: ${ingredient.amount}`)
      .join('\n')
    const steps = recipe.steps.map((step, index) => `${index + 1}. ${step}`).join('\n')
    const conversation = nextMessages
      .slice(-10)
      .map(({ role, content }) => `${role === 'user' ? 'Usuario' : 'Asistente'}: ${content}`)
      .join('\n')
    const prompt = [
      'Eres un asistente de cocina que acompaña al usuario mientras prepara una receta.',
      'Responde siempre en español, de forma clara, amable y práctica. Usa como contexto la receta proporcionada. Si falta un dato, dilo en vez de inventarlo; prioriza la seguridad alimentaria.',
      `Receta: ${recipe.title}`,
      `Ingredientes:\n${ingredients}`,
      `Pasos:\n${steps}`,
      `Conversación:\n${conversation}`,
      'Responde al último mensaje del usuario.',
    ].join('\n\n')

    try {
      const answer = await askRecipeAssistant(prompt)
      setMessages((current) => [...current, { role: 'assistant', content: answer }])
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'No se pudo contactar al asistente.')
    } finally {
      setLoading(false)
    }
  }, [listening, loading, messages, recipe, resetTranscript])

  useEffect(() => {
    transcriptRef.current = transcript
    if (listening) {
      hadListeningRef.current = true
      return
    }
    if (!releaseRequestedRef.current || !hadListeningRef.current) return

    const spokenText = transcriptRef.current.trim()
    releaseRequestedRef.current = false
    hadListeningRef.current = false
    if (spokenText) {
      setOpen(true)
      void submitQuestion(spokenText)
    }
  }, [listening, submitQuestion, transcript])

  return (
    <section className="recipe-assistant" data-open={open}>
      <button
        type="button"
        ref={toggleRef}
        className={`recipe-assistant__toggle ${pressed || listening ? 'recipe-assistant__toggle--listening' : ''}`}
        onClick={() => setOpen(true)}
        onPointerDown={handleMicPointerDown}
        onPointerUp={handleMicPointerUp}
        onPointerCancel={handleMicPointerUp}
        onLostPointerCapture={handleMicPointerUp}
        onKeyDown={handleMicKeyDown}
        onKeyUp={handleMicKeyUp}
        onBlur={() => stopDictation(KEYBOARD_PRESS)}
        aria-label="Abrir asistente de cocina"
        aria-expanded={open}
        aria-controls="recipe-assistant-chat"
        aria-pressed={pressed || listening}
        title={voiceUnavailable || 'Haz clic para abrir o mantén presionado para hablar'}
      >
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <rect x="9" y="3" width="6" height="12" rx="3" />
          <path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3m-4 0h8" />
        </svg>
      </button>

      {open &&
        createPortal(
          <div className="recipe-assistant__overlay">
            <button
              type="button"
              className="recipe-assistant__backdrop"
              aria-label="Cerrar asistente"
              onClick={closeChat}
            />
            <section
              className="recipe-assistant__chat"
              id="recipe-assistant-chat"
              ref={dialogRef}
              role="dialog"
              aria-modal="true"
              aria-labelledby="recipe-assistant-title"
              data-recipe-assistant-dialog
            >
              <div className="recipe-assistant__heading">
                <div>
                  <h3 id="recipe-assistant-title">Asistente de cocina</h3>
                  <p>Resuelve tus dudas sobre {recipe.title}.</p>
                </div>
                <div className="recipe-assistant__heading-actions">
                  <span className="recipe-assistant__status">En línea</span>
                  <button
                    type="button"
                    className="recipe-assistant__close"
                    onClick={closeChat}
                    aria-label="Cerrar asistente"
                  >
                    ×
                  </button>
                </div>
              </div>

              <div className="recipe-assistant__messages" role="log" aria-live="polite" aria-relevant="additions">
                {messages.length === 0 && (
                  <p className="recipe-assistant__welcome">
                    ¡Hola! Puedo ayudarte con los ingredientes, los pasos o posibles sustituciones.
                  </p>
                )}
                {messages.map((message, index) => (
                  <p
                    key={`${message.role}-${index}`}
                    className={`recipe-assistant__message recipe-assistant__message--${message.role}`}
                  >
                    {message.content}
                  </p>
                ))}
                {loading && (
                  <p className="recipe-assistant__message recipe-assistant__message--assistant" role="status">
                    Estoy pensando…
                  </p>
                )}
                <div ref={endRef} />
              </div>

              {error && <p className="recipe-assistant__error" role="alert">{error}</p>}

              <form className="recipe-assistant__form" onSubmit={handleSubmit}>
                <label className="sr-only" htmlFor="recipe-assistant-question">
                  Escribe tu pregunta
                </label>
                <textarea
                  id="recipe-assistant-question"
                  ref={inputRef}
                  value={question}
                  onChange={(event) => {
                    setDraft(event.target.value)
                    resetTranscript()
                  }}
                  placeholder="¿Cuánto tiempo debo cocinarlo?"
                  rows={2}
                  maxLength={500}
                  disabled={loading}
                />
                <button
                  type="button"
                  className={`recipe-assistant__mic ${pressed || listening ? 'recipe-assistant__mic--listening' : ''}`}
                  onPointerDown={handleMicPointerDown}
                  onPointerUp={handleMicPointerUp}
                  onPointerCancel={handleMicPointerUp}
                  onLostPointerCapture={handleMicPointerUp}
                  onKeyDown={handleMicKeyDown}
                  onKeyUp={handleMicKeyUp}
                  onBlur={() => stopDictation(KEYBOARD_PRESS)}
                  disabled={loading || Boolean(voiceUnavailable)}
                  aria-label="Mantén presionado para dictar y enviar"
                  aria-pressed={pressed || listening}
                  title={voiceUnavailable || 'Mantén presionado para dictar y enviar'}
                >
                  <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <rect x="9" y="3" width="6" height="12" rx="3" />
                    <path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3m-4 0h8" />
                  </svg>
                </button>
                <button type="submit" disabled={loading || !question}>
                  Enviar
                </button>
              </form>
              {(voiceError || voiceUnavailable || listening) && (
                <p className="recipe-assistant__voice-status" role="status">
                  {voiceError || voiceUnavailable || 'Escuchando… Suelta el micrófono para enviar.'}
                </p>
              )}
            </section>
          </div>,
          document.body,
        )}
    </section>
  )
}
