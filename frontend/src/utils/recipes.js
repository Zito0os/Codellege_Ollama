import { normalizeKey as normalize } from './normalize'

/** Reparte N slots entre tipos (útil si el caller quiere planificar antojos). */
export function distributeTypes(types, total = 4) {
  const clean = [...new Set(types.map((t) => t.trim()).filter(Boolean))].slice(0, 4)
  const list = clean.length ? clean : ['rápida']
  const counts = Array(list.length).fill(0)
  for (let i = 0; i < total; i += 1) {
    counts[i % list.length] += 1
  }
  return list.map((type, i) => ({ type, count: counts[i] }))
}

/** Resta del inventario los ingredientes que la receta usó (por nombre). */
export function subtractIngredients(pantry, recipeIngredients) {
  const used = new Set(recipeIngredients.map((i) => normalize(i.name)))
  return pantry
    .map((item) => {
      if (!used.has(normalize(item.name))) return item

      let qty = item.qty != null ? parseFloat(String(item.qty).replace(',', '.')) : NaN
      let unit = item.unit || ''
      if (Number.isNaN(qty)) {
        const match = String(item.amount || '').match(/^(\d+(?:[.,]\d+)?)\s*(.*)$/)
        if (!match) return null
        qty = parseFloat(match[1].replace(',', '.'))
        unit = match[2] || unit || 'piezas'
      }

      const step = unit === 'kg' || unit === 'L' ? 0.1 : 1
      const next = Math.round((qty - step) * 10) / 10
      if (next <= 0) return null
      return {
        ...item,
        qty: String(next),
        unit: unit || 'piezas',
        amount: `${next} ${unit || 'piezas'}`,
      }
    })
    .filter(Boolean)
}
