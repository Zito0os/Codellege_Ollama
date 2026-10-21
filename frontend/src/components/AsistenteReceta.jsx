import { useEffect, useRef, useState } from 'react'
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition'
import { askRecipeAssistant } from '../api/assistant'

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
  const inputRef = useRef(null)
  const endRef = useRef(null)
  const pendingStartRef = useRef(null)
  const dictationRequestedRef = useRef(false)
  const isSecureContext = typeof window !== 'undefined' && window.isSecureContext
  const voiceUnavailable = !isSecureContext
    ? 'El dictado requiere una conexión segura (HTTPS o localhost).'
    : !browserSupportsSpeechRecognition
      ? 'Este navegador no es compatible con el dictado por voz.'
      : isMicrophoneAvailable === false
        ? 'No se pudo acceder al micrófono. Revisa los permisos del navegador.'
        : ''
  const question = [draft.trim(), transcript.trim()].filter(Boolean).join(' ')

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

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

  async function toggleDictation() {
    if (listening || pendingStartRef.current) {
      dictationRequestedRef.current = false
      await SpeechRecognition.stopListening()
      return
    }
    if (voiceUnavailable || pendingStartRef.current) return

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
        setVoiceError('No se pudo iniciar el micrófono. Revisa los permisos del navegador.')
      })
      .finally(() => {
        if (pendingStartRef.current === startTask) {
          pendingStartRef.current = null
        }
      })
    pendingStartRef.current = startTask
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (!question || loading) return

    const nextMessages = [...messages, { role: 'user', content: question }]
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
  }

  return (
    <section className="recipe-assistant">
      <button
        type="button"
        className="recipe-assistant__toggle"
        onClick={() => {
          setOpen((current) => {
            if (current) {
              dictationRequestedRef.current = false
              void SpeechRecognition.stopListening()
            }
            return !current
          })
        }}
        aria-expanded={open}
        aria-controls="recipe-assistant-chat"
      >
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <rect x="9" y="3" width="6" height="12" rx="3" />
          <path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3m-4 0h8" />
        </svg>
        <span>{open ? 'Cerrar asistente' : 'Pregúntale al asistente'}</span>
      </button>

      {open && (
        <div className="recipe-assistant__chat" id="recipe-assistant-chat">
          <div className="recipe-assistant__heading">
            <div>
              <h3>Asistente de cocina</h3>
              <p>Resuelve tus dudas sobre {recipe.title}.</p>
            </div>
            <span className="recipe-assistant__status">En línea</span>
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
              className={`recipe-assistant__mic ${listening ? 'recipe-assistant__mic--listening' : ''}`}
              onClick={toggleDictation}
              disabled={loading || Boolean(voiceUnavailable)}
              aria-label={listening ? 'Detener dictado' : 'Dictar pregunta'}
              aria-pressed={listening}
              title={voiceUnavailable || (listening ? 'Detener dictado' : 'Dictar pregunta')}
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
              {voiceError || voiceUnavailable || 'Escuchando… Habla y vuelve a presionar el micrófono para detener.'}
            </p>
          )}
        </div>
      )}
    </section>
  )
}
