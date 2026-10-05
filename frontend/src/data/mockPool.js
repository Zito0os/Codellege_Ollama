/** Banco de recetas demo. La IA real las reemplazará. */
export const RECIPE_POOL = [
  {
    baseId: 'pasta-ajo',
    title: 'Spaghetti al ajo y aceite',
    typeHints: ['italiana', 'rapida', 'rápida', 'pasta', 'mediterranea', 'mediterránea'],
    time: '18 min',
    difficulty: 'Fácil',
    image:
      'https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?auto=format&fit=crop&w=1200&q=80',
    steps: [
      'Hierve agua con sal y cocina la pasta al dente.',
      'En una sartén, sofríe ajo en aceite a fuego medio sin quemar.',
      'Escurre la pasta y mézclala con el aceite y ajo.',
      'Ajusta sal, pimienta y un toque de chile si tienes.',
      'Sirve inmediato con un chorrito de aceite crudo.',
    ],
  },
  {
    baseId: 'huevos-revueltos',
    title: 'Huevos cremosos con hierbas',
    typeHints: ['rapida', 'rápida', 'desayuno', 'simple', 'casera'],
    time: '10 min',
    difficulty: 'Fácil',
    image:
      'https://images.unsplash.com/photo-1525351484163-7529414344d8?auto=format&fit=crop&w=1200&q=80',
    steps: [
      'Bate los huevos con una pizca de sal.',
      'Calienta mantequilla o aceite a fuego bajo.',
      'Vierte los huevos y remueve constante hasta cremosos.',
      'Retira del fuego antes de que sequen del todo.',
      'Termina con hierbas frescas o queso si hay.',
    ],
  },
  {
    baseId: 'stir-fry',
    title: 'Salteado oriental de verduras',
    typeHints: ['oriental', 'asiatica', 'asiática', 'china', 'rapida', 'rápida', 'wok'],
    time: '22 min',
    difficulty: 'Media',
    image:
      'https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=1200&q=80',
    steps: [
      'Corta verduras en trozos similares para cocción pareja.',
      'Calienta aceite muy caliente en sartén o wok.',
      'Saltea primero las verduras más firmes.',
      'Añade salsa de soya o condimento y mezcla rápido.',
      'Sirve con arroz o solo, aún crujiente.',
    ],
  },
  {
    baseId: 'sopa-tomate',
    title: 'Crema tibia de tomate',
    typeHints: ['casera', 'confort', 'sopa', 'francesa', 'mediterranea', 'mediterránea'],
    time: '35 min',
    difficulty: 'Media',
    image:
      'https://images.unsplash.com/photo-1547592166-23ac45744acd?auto=format&fit=crop&w=1200&q=80',
    steps: [
      'Sofríe cebolla hasta transparente.',
      'Añade tomate y cocina 10 minutos.',
      'Cubre con caldo o agua y hierve suave.',
      'Licúa hasta textura sedosa.',
      'Ajusta sal y sirve con un toque de crema o aceite.',
    ],
  },
  {
    baseId: 'taco-rapido',
    title: 'Tacos exprés de sartén',
    typeHints: ['mexicana', 'rapida', 'rápida', 'tacos', 'casera'],
    time: '20 min',
    difficulty: 'Fácil',
    image:
      'https://images.unsplash.com/photo-1565299585323-38d6b0865b47?auto=format&fit=crop&w=1200&q=80',
    steps: [
      'Calienta tortillas en comal o sartén.',
      'Prepara el relleno salteando proteína o verdura.',
      'Sazona con sal, limón y especias disponibles.',
      'Arma tacos y añade lo fresco que tengas.',
      'Sirve al momento para que no endurezcan.',
    ],
  },
  {
    baseId: 'bowl-quinoa',
    title: 'Bowl fresco de grano y verdura',
    typeHints: ['saludable', 'bowl', 'moderna', 'rapida', 'rápida', 'veggie'],
    time: '25 min',
    difficulty: 'Fácil',
    image:
      'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=1200&q=80',
    steps: [
      'Cocina el grano según paquete.',
      'Corta verduras crudas o pásalas por plancha breve.',
      'Prepara un aderezo simple: aceite, ácido y sal.',
      'Monta el bowl en capas.',
      'Termina con semillas o queso si hay.',
    ],
  },
  {
    baseId: 'curry-rapido',
    title: 'Curry corto de cocina de casa',
    typeHints: ['india', 'oriental', 'curry', 'especiada', 'asiatica', 'asiática'],
    time: '30 min',
    difficulty: 'Media',
    image:
      'https://images.unsplash.com/photo-1585937421612-70a008356fbe?auto=format&fit=crop&w=1200&q=80',
    steps: [
      'Sofríe cebolla y ajo hasta aromáticos.',
      'Añade especias y tuesta 30 segundos.',
      'Incorpora base (tomate o leche de coco) y verduras.',
      'Cocina a fuego medio hasta espesar.',
      'Sirve con arroz o pan plano.',
    ],
  },
  {
    baseId: 'omelette-frances',
    title: 'Omelette francés clásico',
    typeHints: ['francesa', 'frances', 'francés', 'rapida', 'rápida', 'desayuno'],
    time: '12 min',
    difficulty: 'Media',
    image:
      'https://images.unsplash.com/photo-1612929633738-8fe44f7ec841?auto=format&fit=crop&w=1200&q=80',
    steps: [
      'Bate huevos solo con sal, sin exceso de aire.',
      'Calienta mantequilla en sartén antiadherente.',
      'Vierte y remueve suave formando cuajada fina.',
      'Dobla en tercio cuando aún esté cremoso al centro.',
      'Desliza al plato y sirve de inmediato.',
    ],
  },
  {
    baseId: 'ensalada-crocante',
    title: 'Ensalada crocante de temporada',
    typeHints: ['ensalada', 'fresca', 'saludable', 'rapida', 'rápida', 'ligera'],
    time: '15 min',
    difficulty: 'Fácil',
    image:
      'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=900&q=80',
    steps: [
      'Lava y seca bien las hojas y verduras.',
      'Corta en trozos generosos y irregulares.',
      'Prepara vinagreta: aceite, ácido, sal, pimienta.',
      'Mezcla al servir para mantener crocancia.',
      'Añade proteína fría si quieres más cuerpo.',
    ],
  },
  {
    baseId: 'arroz-frito',
    title: 'Arroz frito de sobras',
    typeHints: ['oriental', 'asiatica', 'asiática', 'china', 'rapida', 'rápida'],
    time: '18 min',
    difficulty: 'Fácil',
    image:
      'https://images.unsplash.com/photo-1603133872878-684f208fb84b?auto=format&fit=crop&w=1200&q=80',
    steps: [
      'Usa arroz frío del día anterior si es posible.',
      'Saltea aromáticos y verdura picada fina.',
      'Empuja a un lado, cocina huevo si tienes.',
      'Incorpora arroz y salsa; saltea en seco.',
      'Prueba sal y sirve caliente.',
    ],
  },
  {
    baseId: 'pollo-limon',
    title: 'Pollo al limón de sartén',
    typeHints: ['casera', 'mediterranea', 'mediterránea', 'rapida', 'rápida', 'proteina'],
    time: '28 min',
    difficulty: 'Media',
    image:
      'https://images.unsplash.com/photo-1598103442097-8b704241d91a?auto=format&fit=crop&w=1200&q=80',
    steps: [
      'Sala el pollo y dóralo en sartén caliente.',
      'Reserva y en la misma sartén cocina aromáticos.',
      'Desglasa con limón y un poco de agua o caldo.',
      'Devuelve el pollo y termina a fuego medio.',
      'Sirve con verdura o arroz simple.',
    ],
  },
  {
    baseId: 'tostada-aguacate',
    title: 'Tostada de aguacate y huevo',
    typeHints: ['rapida', 'rápida', 'desayuno', 'moderna', 'simple'],
    time: '12 min',
    difficulty: 'Fácil',
    image:
      'https://images.unsplash.com/photo-1525351484163-7529414344d8?auto=format&fit=crop&w=1000&q=80',
    steps: [
      'Tuesta el pan hasta dorado.',
      'Machaca aguacate con sal y limón.',
      'Cocina el huevo al gusto.',
      'Monta tostada, aguacate y huevo.',
      'Termina con pimienta o chile en hojuelas.',
    ],
  },
]
