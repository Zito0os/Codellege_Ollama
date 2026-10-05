import { normalizeKey } from './normalize'

const KEYS = {
  tools: 'diezgo_tools',
  ingredients: 'diezgo_ingredients',
  saved: 'diezgo_saved',
  history: 'diezgo_history',
  usedSession: 'diezgo_used_session',
}

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return fallback
    return JSON.parse(raw)
  } catch {
    return fallback
  }
}

function write(key, value) {
  localStorage.setItem(key, JSON.stringify(value))
}

function dedupeIngredients(list) {
  const seen = new Set()
  const next = []
  for (const item of list || []) {
    const key = normalizeKey(item?.name)
    if (!key || seen.has(key)) continue
    seen.add(key)
    next.push(item)
  }
  return next
}

export function getTools() {
  return read(KEYS.tools, null)
}

export function setTools(tools) {
  write(KEYS.tools, tools)
}

export function getIngredients() {
  const list = dedupeIngredients(read(KEYS.ingredients, []))
  write(KEYS.ingredients, list)
  return list
}

export function setIngredients(ingredients) {
  write(KEYS.ingredients, dedupeIngredients(ingredients))
}

export function getSavedRecipes() {
  return read(KEYS.saved, [])
}

export function setSavedRecipes(recipes) {
  write(KEYS.saved, recipes)
}

export function saveRecipe(recipe) {
  const current = getSavedRecipes()
  if (current.some((r) => r.id === recipe.id)) return current
  const next = [{ ...recipe, savedAt: Date.now() }, ...current]
  setSavedRecipes(next)
  return next
}

export function unsaveRecipe(id) {
  const next = getSavedRecipes().filter((r) => r.id !== id)
  setSavedRecipes(next)
  return next
}

export function getHistory() {
  return read(KEYS.history, [])
}

export function pushHistory(entry) {
  const next = [entry, ...getHistory()].slice(0, 40)
  write(KEYS.history, next)
  return next
}

export function clearOnboarding() {
  localStorage.removeItem(KEYS.tools)
}
