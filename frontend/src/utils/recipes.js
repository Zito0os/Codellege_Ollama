import { RECIPE_POOL } from '../data/mockPool'
import { normalizeKey as normalize } from './normalize'

/** Reparte 4 recetas entre N tipos (1→4, 2→2+2, 3→2+1+1, 4→1+1+1+1). */
export function distributeTypes(types, total = 4) {
  const clean = [...new Set(types.map((t) => t.trim()).filter(Boolean))].slice(0, 4)
  const list = clean.length ? clean : ['rápida']
  const counts = Array(list.length).fill(0)
  for (let i = 0; i < total; i += 1) {
    counts[i % list.length] += 1
  }
  return list.map((type, i) => ({ type, count: counts[i] }))
}

function scoreRecipe(recipe, type, ingredients) {
  const nType = normalize(type)
  const hintHit = recipe.typeHints.some((h) => {
    const nh = normalize(h)
    return nType.includes(nh) || nh.includes(nType)
  })
  const names = ingredients.map((i) => normalize(i.name))
  const titleBits = normalize(recipe.title).split(/\s+/)
  const ingredientHit = names.some((n) =>
    titleBits.some((bit) => bit.length > 3 && (n.includes(bit) || bit.includes(n))),
  )
  return (hintHit ? 5 : 0) + (ingredientHit ? 2 : 0) + Math.random()
}

function pickForType(type, ingredients, usedBaseIds) {
  const ranked = [...RECIPE_POOL]
    .filter((r) => !usedBaseIds.has(r.baseId))
    .map((r) => ({ r, score: scoreRecipe(r, type, ingredients) }))
    .sort((a, b) => b.score - a.score)

  const chosen = ranked[0]?.r || RECIPE_POOL[Math.floor(Math.random() * RECIPE_POOL.length)]
  usedBaseIds.add(chosen.baseId)
  return chosen
}

function buildIngredientList(pantry) {
  if (!pantry.length) {
    return [
      { name: 'Ingredientes base', amount: 'al gusto' },
      { name: 'Sal y pimienta', amount: 'c/n' },
    ]
  }
  const shuffled = [...pantry].sort(() => Math.random() - 0.5)
  const take = shuffled.slice(0, Math.min(5, shuffled.length))
  return take.map((item) => {
    const amount =
      item.qty != null && item.unit
        ? `${item.qty} ${item.unit}`
        : item.amount || 'al gusto'
    return { name: item.name, amount }
  })
}

export function generateRecipes({ ingredients, types, tools, protectIds = [] }) {
  const plan = distributeTypes(types)
  const usedBaseIds = new Set()
  const protectedSet = new Set(protectIds)
  const recipes = []

  for (const slot of plan) {
    for (let i = 0; i < slot.count; i += 1) {
      const base = pickForType(slot.type, ingredients, usedBaseIds)
      const id = `${base.baseId}-${slot.type}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
      recipes.push({
        id,
        baseId: base.baseId,
        title: base.title,
        cuisine: slot.type,
        time: base.time,
        difficulty: base.difficulty,
        image: base.image,
        steps: base.steps,
        ingredients: buildIngredientList(ingredients),
        toolsUsed: (tools || []).slice(0, 3),
        locked: false,
      })
    }
  }

  // Si hay protegidas (guardadas en esta tanda), el caller las fusiona afuera.
  return recipes.filter((r) => !protectedSet.has(r.id))
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
