/** Normaliza texto para comparar nombres (Huevo === huevo === HUÉVO). */
export function normalizeKey(text) {
  return (text || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/\s+/g, ' ')
    .trim()
}
