"""Generate recipe proposals with local Ollama (llama3.2:3b)."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from ollama import chat

MODEL = "llama3.2:3b"

# Placeholder images keyed by normalized cuisine / craving hint.
IMAGE_BY_HINT: dict[str, str] = {
    "italiana": "https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?auto=format&fit=crop&w=1200&q=80",
    "pasta": "https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?auto=format&fit=crop&w=1200&q=80",
    "rapida": "https://images.unsplash.com/photo-1525351484163-7529414344d8?auto=format&fit=crop&w=1200&q=80",
    "desayuno": "https://images.unsplash.com/photo-1525351484163-7529414344d8?auto=format&fit=crop&w=1200&q=80",
    "oriental": "https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=1200&q=80",
    "asiatica": "https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=1200&q=80",
    "china": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?auto=format&fit=crop&w=1200&q=80",
    "sopa": "https://images.unsplash.com/photo-1547592166-23ac45744acd?auto=format&fit=crop&w=1200&q=80",
    "mexicana": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?auto=format&fit=crop&w=1200&q=80",
    "tacos": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?auto=format&fit=crop&w=1200&q=80",
    "saludable": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=1200&q=80",
    "bowl": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=1200&q=80",
    "veggie": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=1200&q=80",
    "ensalada": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=900&q=80",
    "india": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?auto=format&fit=crop&w=1200&q=80",
    "francesa": "https://images.unsplash.com/photo-1612929633738-8fe44f7ec841?auto=format&fit=crop&w=1200&q=80",
    "casera": "https://images.unsplash.com/photo-1598103442097-8b704241d91a?auto=format&fit=crop&w=1200&q=80",
    "mediterranea": "https://images.unsplash.com/photo-1598103442097-8b704241d91a?auto=format&fit=crop&w=1200&q=80",
}

DEFAULT_IMAGE = (
    "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=1200&q=80"
)

# Closed set for imageTag — must match IMAGE_BY_HINT keys (plus aliases resolved later).
ALLOWED_IMAGE_TAGS = (
    "mexicana",
    "italiana",
    "oriental",
    "francesa",
    "mediterranea",
    "india",
    "saludable",
    "rapida",
    "desayuno",
    "bowl",
    "veggie",
    "tacos",
    "pasta",
    "sopa",
    "ensalada",
    "casera",
    "china",
)

SYSTEM_PROMPT = """Eres un chef de cocina casera. Respondes SIEMPRE en español de México.
Devuelves ÚNICAMENTE un JSON válido (sin markdown, sin comentarios, sin texto fuera del JSON).

Formato exacto:
{
  "recipes": [
    {
      "title": "nombre concreto del platillo",
      "cuisine": "etiqueta corta del estilo (ej. Mexicana)",
      "imageTag": "una de las etiquetas permitidas",
      "time": "N min",
      "difficulty": "Fácil|Media|Difícil",
      "steps": ["paso accionable 1", "paso 2"],
      "ingredients": [{"name": "nombre", "amount": "cantidad + unidad"}],
      "toolsUsed": ["herramienta"]
    }
  ]
}

imageTag PERMITIDOS (elige exactamente uno por receta, en minúsculas):
mexicana, italiana, oriental, francesa, mediterranea, india, saludable, rapida,
desayuno, bowl, veggie, tacos, pasta, sopa, ensalada, casera, china.

Reglas de contenido (obligatorias):
1) Genera exactamente el número de recetas pedido; cada una distinta.
2) INGREDIENTES: usa SOLO el inventario del usuario + básicos (sal, pimienta, aceite, agua, limón).
   No inventes despensa fuera del inventario. Prefiere POCOS ingredientes bien usados
   (2–6 por receta) en vez de meter todo el inventario a la fuerza.
3) COHERENCIA ingredientes ↔ pasos: TODO lo usado en pasos va en "ingredients" con cantidad.
4) CANTIDADES: realistas y con unidad útil. Evita "2 piezas" ambiguo para queso/jamón a granel;
   usa g, rebanadas o tazas cuando tenga sentido (ej. "80 g queso", "4 rebanadas jamón").
5) HERRAMIENTAS: solo las del usuario (o sartén/cuchillo/tabla).
6) ANTOJOS: encaja con al menos uno, sin forzar un platillo incompleto o absurdo.
7) imageTag acorde al platillo real. PASOS (5–7) con fuego + tiempo + acción concreta.
8) "time" debe cubrir el paso más largo (si el arroz necesita 18 min, la receta no puede ser "10 min").

Reglas de ESTRUCTURA (si no se pueden cumplir, elige OTRO platillo):
- Comida real, no proteína suelta en un plato.
- Tacos/quesadillas: requieren tortillas en inventario. Si no hay, no las propongas.
- Ensalada: requiere base verde/cruda. Jamón+queso solos NO es ensalada.
- Pasta: requiere pasta. Sandwich/torta: requiere pan. Bowl: base + ≥2 toppings.
- Sopa: líquido suficiente + al menos 2 componentes reales además de sal/agua.

Reglas de COCINA LÓGICA (sanidad — no rompas estas):
A) PROPORCIONES grano/líquido: arroz/pasta/legumbre seca necesitan ~2–3 partes de líquido
   por 1 de grano (volumen). Nunca pongas más grano que líquido (ej. 500 g arroz + 1 L leche = inválido).
   En sopas, usa poco grano (ej. 50–80 g arroz por ~1 L) o cocina el grano aparte.
B) SECUENCIA "duro primero": arroz, papa, zanahoria, carne cruda van temprano y con tiempo
   suficiente (≥15 min si es arroz crudo). NUNCA agregues arroz crudo en el último paso.
C) LÁCTEOS: no hiervas leche a fuego alto mucho rato. Preferible agua/caldo como base y
   leche al final a fuego bajo. Queso: al final, fuego bajo o apagado, solo hasta fundir
   (no ebullición larga o se corta/separa).
D) ÁCIDO + LÁCTEO: si hay limón/vinagre/tomate fuerte con leche/crema, añade el lácteo al final
   fuera del hervor fuerte (o usa espesante).
E) PROTEÍNA CRUDA: debe haber un paso claro de cocción (sellar/freír/hervir/hornear) ≥5 min.
F) Si el inventario mezcla cosas difíciles (mucho arroz + poca leche + jamón/queso), NO inventes
   una "sopa" imposible: elige un platillo simple y correcto (ej. arroz aparte + jamón/queso a la sartén).
"""


def _normalize_key(value: str) -> str:
    raw = (value or "").strip().lower()
    replacements = (
        ("á", "a"),
        ("é", "e"),
        ("í", "i"),
        ("ó", "o"),
        ("ú", "u"),
        ("ü", "u"),
        ("ñ", "n"),
    )
    for src, dst in replacements:
        raw = raw.replace(src, dst)
    return raw


def _format_pantry(ingredients: list[dict[str, Any]]) -> str:
    lines = []
    for item in ingredients:
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        qty = item.get("qty")
        unit = item.get("unit")
        amount = item.get("amount")
        if qty is not None and unit:
            lines.append(f"- {name}: {qty} {unit}")
        elif amount:
            lines.append(f"- {name}: {amount}")
        else:
            lines.append(f"- {name}")
    return "\n".join(lines) if lines else "- (sin inventario listado)"


def build_user_prompt(
    *,
    ingredients: list[dict[str, Any]],
    types: list[str],
    tools: list[str],
    note: str,
    count: int,
) -> str:
    types_text = ", ".join(types) if types else "Rápida"
    tools_text = ", ".join(tools) if tools else "sartén, cuchillo, tabla"
    note_text = note.strip() if note and note.strip() else "(ninguna)"
    tags_text = ", ".join(ALLOWED_IMAGE_TAGS)
    return (
        f"Genera exactamente {count} recetas distintas y cocinables hoy.\n"
        f"Antojos/tipos pedidos: {types_text}\n"
        f"Herramientas disponibles: {tools_text}\n"
        f"Nota del usuario: {note_text}\n"
        f"Inventario disponible (NO inventes fuera de esta lista + sal/pimienta/aceite/agua/limón):\n"
        f"{_format_pantry(ingredients)}\n"
        f"Para cada receta elige un imageTag de: {tags_text}\n"
        "Recuerda: proporciones grano/líquido sanas; duro primero; queso/leche al final a fuego bajo.\n"
        "No tacos sin tortillas, no ensalada sin base verde, no sopas con ratios imposibles.\n"
        "Usa solo lo necesario del inventario (no lo tires todo en cada receta). Solo JSON."
    )


def extract_json_object(text: str) -> dict[str, Any]:
    """Parse model output that may include markdown fences or extra text."""
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("Respuesta vacía del modelo")

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned, re.IGNORECASE)
    if fence:
        cleaned = fence.group(1).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("No se encontró JSON en la respuesta") from None
        data = json.loads(cleaned[start : end + 1])

    if not isinstance(data, dict):
        raise ValueError("El JSON raíz debe ser un objeto")
    return data


def resolve_image_tag(*candidates: str) -> str | None:
    """Map free text / model tag to a known IMAGE_BY_HINT key."""
    aliases = {
        "asiatica": "oriental",
        "asiatico": "oriental",
        "comfort": "casera",
        "confort": "casera",
        "picante": "mexicana",
        "mariscos": "mediterranea",
        "asados": "casera",
        "asado": "casera",
        "curry": "india",
    }
    for raw in candidates:
        key = _normalize_key(raw)
        if not key:
            continue
        key = aliases.get(key, key)
        if key in IMAGE_BY_HINT:
            return key
        for hint in IMAGE_BY_HINT:
            if hint in key or key in hint:
                return hint
    return None


def pick_image(image_tag: str, cuisine: str, types: list[str]) -> str:
    # Prefer explicit imageTag from the model, then cuisine, then user cravings.
    resolved = resolve_image_tag(image_tag, cuisine, *types)
    if resolved:
        return IMAGE_BY_HINT[resolved]
    return DEFAULT_IMAGE


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_ingredients(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list) or not raw:
        return [{"name": "Ingredientes base", "amount": "al gusto"}]

    out: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, dict):
            name = str(item.get("name") or "").strip()
            amount = str(item.get("amount") or "al gusto").strip() or "al gusto"
            if name:
                out.append({"name": name, "amount": amount})
        elif isinstance(item, str) and item.strip():
            out.append({"name": item.strip(), "amount": "al gusto"})
    return out or [{"name": "Ingredientes base", "amount": "al gusto"}]


def normalize_recipes(
    raw_recipes: Any,
    *,
    types: list[str],
    tools: list[str],
    count: int,
) -> list[dict[str, Any]]:
    if not isinstance(raw_recipes, list):
        raise ValueError("El campo recipes debe ser una lista")

    difficulty_ok = {"fácil", "facil", "media", "difícil", "dificil"}
    normalized: list[dict[str, Any]] = []

    for index, item in enumerate(raw_recipes[:count]):
        if not isinstance(item, dict):
            continue

        title = str(item.get("title") or f"Receta {index + 1}").strip()
        fallback_cuisine = types[index % len(types)] if types else "Casera"
        cuisine = str(item.get("cuisine") or fallback_cuisine).strip()
        image_tag = str(item.get("imageTag") or item.get("image_tag") or "").strip()
        time = str(item.get("time") or "25 min").strip()
        difficulty_raw = str(item.get("difficulty") or "Fácil").strip()
        difficulty_key = _normalize_key(difficulty_raw)
        if difficulty_key not in difficulty_ok:
            difficulty = "Fácil"
        elif "facil" in difficulty_key:
            difficulty = "Fácil"
        elif "dificil" in difficulty_key:
            difficulty = "Difícil"
        else:
            difficulty = "Media"

        steps = _as_str_list(item.get("steps"))
        if len(steps) < 4:
            steps = steps + [
                "Prueba y ajusta sal.",
                "Sirve de inmediato en plato caliente.",
            ]
        steps = steps[:7]

        tools_used = _as_str_list(item.get("toolsUsed")) or list(tools[:3])
        recipe_id = f"ai-{uuid.uuid4().hex[:10]}"
        # Prefer this recipe's craving when model omits/misfires imageTag.
        type_hint = types[index % len(types)] if types else ""

        normalized.append(
            {
                "id": recipe_id,
                "baseId": recipe_id,
                "title": title,
                "cuisine": cuisine,
                "time": time,
                "difficulty": difficulty,
                "image": pick_image(image_tag, cuisine, [type_hint, *types]),
                "steps": steps,
                "ingredients": _normalize_ingredients(item.get("ingredients")),
                "toolsUsed": tools_used,
                "locked": False,
            }
        )

    if len(normalized) < count:
        raise ValueError(f"El modelo devolvió {len(normalized)} recetas; se pedían {count}")

    return normalized[:count]


def generate_recipes_with_ollama(
    *,
    ingredients: list[dict[str, Any]],
    types: list[str],
    tools: list[str],
    note: str = "",
    count: int = 4,
) -> list[dict[str, Any]]:
    if count < 1 or count > 8:
        raise ValueError("count debe estar entre 1 y 8")

    response = chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_user_prompt(
                    ingredients=ingredients,
                    types=types,
                    tools=tools,
                    note=note,
                    count=count,
                ),
            },
        ],
        options={"temperature": 0.35, "top_p": 0.9},
    )

    content = getattr(response.message, "content", None) or ""
    data = extract_json_object(content)
    return normalize_recipes(
        data.get("recipes"),
        types=types,
        tools=tools,
        count=count,
    )
