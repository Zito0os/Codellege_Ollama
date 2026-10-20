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

SYSTEM_PROMPT = """Eres un chef experto de 5 estrellas Michelin. Respondes SIEMPRE en español de México.
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

Supuestos del entorno (SIEMPRE verdaderos — no los pidas ni los inventes como limitación):
- El usuario TIENE AGUA potable ilimitada para cocinar (hervir, cocer, diluir, lavar).
- El usuario TIENE FUEGO / calor de cocina (estufa o equivalente): puede freír, sofreír, hervir,
  dorar y cocer a fuego bajo/medio/alto. NO digas que no puede cocinar por falta de fuego.
- Agua y fuego NO van en "ingredients" ni en "toolsUsed" (son infraestructura, no despensa).
- Sigue respetando las herramientas listadas (sartén, olla, etc.); si hay olla/sartén, úsala con fuego.

Reglas de contenido (obligatorias):
1) Genera exactamente el número de recetas pedido; cada una DISTINTA (títulos, técnica y protagonista distintos).
2) INVENTARIO ESTRICTO: usa SOLO lo que está en el inventario + sal, pimienta y aceite.
   PROHIBIDO inventar lechuga, limón, tortilla, pan, huevo, etc. si NO están en el inventario.
   Si falta una base (lechuga para ensalada, tortilla para tacos), elige OTRO platillo posible.
3) RACIÓN = 1 PERSONA ADULTA (comida de verdad, no “snack de conejo”):
   El inventario es STOCK; no lo gastes entero, pero tampoco pongas porciones ridículas.
   Guías de consumo medio por persona (ajusta a lo disponible):
   - Tomate: 2–3 piezas medianas (o ~250–300 g), no 1 solo como “comida”.
   - Lechuga: ~1/4–1/2 pieza/cabeza (o un tazón generoso ~80–120 g hojas), no “1 hoja”.
   - Arroz crudo: ~70–100 g (≈ 1/2 taza). Pasta seca: ~80–100 g.
   - Proteína (pollo/jamón/carne): ~100–150 g o 3–5 rebanadas.
   - Queso: ~40–80 g. Tortillas: 2–4 por persona.
   Si hay 21 tomates en stock, usa 2–3; NUNCA 21 ni 1 miserable.
4) PLATO EQUILIBRADO (método del plato — cuando el inventario lo permita):
   Una COMIDA debería combinar idealmente:
   - Proteína (pollo, huevo, jamón, queso, legumbre, etc. si hay)
   - Carbohidrato (arroz, pasta, tortilla, pan, papa, etc. si hay)
   - Vegetal/fruta (tomate, lechuga, verdura, etc. si hay)
   Si faltan categorías en el inventario, arma lo más completo posible sin inventar.
   No propongas como “comida” solo 1 tomate + un poco de lechuga: o la haces abundante
   y con más componentes disponibles, o elige otro platillo más sustancioso.
5) SELECCIÓN: por receta usa 3–6 alimentos del inventario (+ sal/pimienta/aceite) cuando haya stock.
   No metas TODO el inventario; sí busca cubrir proteína+carbo+vegetal si existen.
6) COHERENCIA TOTAL: todo alimento en ingredients debe usarse en steps, y todo alimento en steps
   (salvo agua) debe estar en ingredients. Si el título/platillo usa tortilla, pan o huevo,
   DEBE aparecer en ingredients Y en al menos un paso (calentar tortilla, armar taco, etc.).
7) CANTIDADES claras y generosas de adulto: "80 g queso", "4 rebanadas jamón", "2 tomates",
   "3 tortillas". Evita ambiguo y evita raciones mínimas.
8) HERRAMIENTAS: solo las del usuario (o sartén/cuchillo/tabla). Fuego ya garantizado.
9) ANTOJOS: encaja con ≥1 sin forzar platillo incompleto. imageTag acorde.
10) "time" cubre el paso más largo.

NOMBRES (español México — no confundas):
- "Tortilla" (platillo) = tortilla de huevo / omelette. Solo si HAY huevo en inventario.
- Si usas tortillas de maíz/harina para enrollar/rellenar: el título debe decir "Tacos…",
  "Quesadillas…" o "Wraps…", NUNCA "Tortilla de jamón y queso" para eso.
- Evita repetir siempre "jamón y queso" en el título; varía protagonista y técnica.

VARIACIÓN (importante):
- No abuses de jamón, queso o pollo como protagonista en todas las propuestas.
- Entre las N recetas, cambia el foco: un tomate/sofrito, un arroz, una verdura, un lácteo, etc.
- Máximo 1 receta por tanda puede tener jamón+queso como duo principal.
- Si hay varios ingredientes, prioriza usar distintos protagonistas en cada receta.

PASOS PRECISOS (5–7) — prohibido lo vago:
Mal: "Cocina el pollo 5 minutos."
Bien: "En sartén a fuego medio-alto, dora el pollo en trozos de 2 cm con 1 cda de aceite,
  3–4 min por lado hasta dorar y jugo claro; no debe quedar rosado dentro."
Cada paso debe incluir cuando aplique: corte/tamaño, fuego (bajo/medio/alto), tiempo,
señal de punto (dorado, transparente, al dente, jugo claro), y qué hacer después.

Reglas de ESTRUCTURA (si no se cumplen, OTRO platillo):
- Comida real, no proteína suelta.
- Tacos/quesadillas: requieren tortillas en inventario + pasos de calentar/armar.
- Ensalada: requiere base verde YA en inventario (lechuga/espinaca/etc.). Sin eso, NO ensalada
  y NO inventes lechuga. Alternativas: pico de gallo si hay tomate/cebolla, salteado, etc.
- Pasta: requiere pasta. Sandwich/torta: pan. Bowl: base + ≥2 toppings.
- Sopa: líquido suficiente + ≥2 componentes reales.

Reglas de COCINA LÓGICA:
A) Grano/líquido ~2–3:1. Nunca más grano que líquido. En sopa, poco grano o cocinado aparte.
B) Duro primero (arroz/papa/carne cruda temprano con tiempo real). Arroz crudo ≠ último paso.
C) Lácteos/queso al final a fuego bajo; no hervir leche rato largo.
D) Ácido + lácteo: lácteo al final fuera de hervor fuerte.
E) Proteína cruda: paso de cocción claro ≥5 min con señal de cocción.
F) Si el inventario no da para un platillo coherente, cambia de idea; no fuerces sopas/tacos imposibles.
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
        f"Inventario (STOCK disponible; NO inventes nada fuera; básicos solo sal/pimienta/aceite):\n"
        f"{_format_pantry(ingredients)}\n"
        "Entorno: hay agua y fuego/estufa. No los listes.\n"
        "RACIÓN: 1 adulto con hambre normal (porciones medias: 2–3 tomates, no 1 ni 21).\n"
        "Busca plato equilibrado: proteína + carbohidrato + vegetal si el inventario los tiene.\n"
        "Varía protagonistas entre recetas; no repitas siempre jamón/queso/pollo.\n"
        "Nombres: 'tortilla' = omelette de huevo; para tortillas de maíz usa 'tacos/quesadillas'.\n"
        "Pasos muy concretos (corte, fuego, tiempo, punto de cocción). Todo ingrediente del platillo en steps.\n"
        f"imageTag de: {tags_text}\n"
        "Solo JSON."
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
