export const UNITS = [
  { id: 'piezas', label: 'pzas' },
  { id: 'kg', label: 'kg' },
  { id: 'g', label: 'g' },
  { id: 'L', label: 'L' },
  { id: 'ml', label: 'ml' },
  { id: 'tazas', label: 'tazas' },
  { id: 'cda', label: 'cda' },
  { id: 'cdita', label: 'cdita' },
  { id: 'rebanadas', label: 'reb.' },
  { id: 'paquete', label: 'paq.' },
  { id: 'lata', label: 'lata' },
  { id: 'manojo', label: 'manojo' },
]

export const CUISINE_OPTIONS = [
  'Rápida',
  'Mexicana',
  'Italiana',
  'Oriental',
  'Francesa',
  'Saludable',
  'Comfort',
  'Desayuno',
  'Pasta',
  'Sopa',
  'Ensalada',
  'Tacos',
  'Bowl',
  'Asados',
  'Picante',
  'Veggie',
  'Mariscos',
  'Casera',
  'Mediterránea',
  'India',
]

export function formatAmount(item) {
  if (item.qty != null && item.unit) return `${item.qty} ${item.unit}`
  return item.amount || ''
}
