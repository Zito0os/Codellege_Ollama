const API_BASE = 'http://127.0.0.1:8000'

/**
 * Ask the local FastAPI + Ollama stack for recipe proposals.
 * @param {{ ingredients: object[], types: string[], tools: string[], note?: string, count?: number }} payload
 */
export async function generateRecipesFromAI(payload) {
  const response = await fetch(`${API_BASE}/recipes/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ingredients: payload.ingredients || [],
      types: payload.types || [],
      tools: payload.tools || [],
      note: payload.note || '',
      count: payload.count ?? 4,
    }),
  })

  let data = null
  try {
    data = await response.json()
  } catch {
    data = null
  }

  if (!response.ok) {
    const detail = data?.detail
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg || String(d)).join('; ')
          : 'No se pudieron generar recetas.'
    throw new Error(message)
  }

  if (!Array.isArray(data?.recipes) || !data.recipes.length) {
    throw new Error('La API no devolvió recetas.')
  }

  return data.recipes
}
