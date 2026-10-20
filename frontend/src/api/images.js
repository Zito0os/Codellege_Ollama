const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

export async function analyzeIngredientsFromImage(file) {
  const formData = new FormData()
  formData.append('imagen', file)

  const response = await fetch(`${API_BASE}/analizar`, {
    method: 'POST',
    body: formData,
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
    throw new Error(
      typeof data?.detail === 'string'
        ? data.detail
        : 'No se pudo analizar la imagen.',
    )
  }

  if (typeof data?.resultado !== 'string') {
    throw new Error('La API no devolvió el resultado del análisis.')
  }

  return data.resultado
    .split('\n')
    .map((line) => line.match(/^\s*-\s+(.+?)\s*$/)?.[1])
    .filter(Boolean)
}
