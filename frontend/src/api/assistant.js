const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

export async function askRecipeAssistant(prompt) {
  const response = await fetch(`${API_BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  })

  let data
  try {
    data = await response.json()
  } catch (error) {
    if (response.ok) {
      throw new Error('La API devolvió una respuesta no válida.', { cause: error })
    }
    data = null
  }

  if (!response.ok) {
    const detail = data?.detail
    throw new Error(typeof detail === 'string' ? detail : 'No se pudo contactar al asistente.')
  }

  if (typeof data?.answer !== 'string' || !data.answer.trim()) {
    throw new Error('El asistente no devolvió una respuesta.')
  }

  return data.answer.trim()
}
