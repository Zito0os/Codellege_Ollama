import json
import re
import unicodedata
from io import BytesIO

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from PIL import Image, ImageOps
from pydantic import BaseModel
from starlette.responses import StreamingResponse
import ollama

app = FastAPI()
MAX_IMAGE_SIZE = 10 * 1024 * 1024
VISION_MODEL = "qwen2.5vl:3b"
VISION_MODEL_ADVANCED = "qwen3-vl:4b"
VISION_PROMPT = (
    "Escribe en español solo nombres de alimentos concretos que veas claramente en {parte}, "
    "separados por comas. Sé muy conservador: omite lo tapado o dudoso y no adivines. "
    "No repitas."
)
MAX_ITEMS_PER_ANALYSIS = 20

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
        ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)

class PromptRequest(BaseModel):
    prompt: str


def preparar_imagen(contenido: bytes) -> bytes:
    with Image.open(BytesIO(contenido)) as original:
        imagen = ImageOps.exif_transpose(original)
        if "A" in imagen.getbands():
            rgba = imagen.convert("RGBA")
            fondo = Image.new("RGB", rgba.size, "white")
            fondo.paste(rgba, mask=rgba.getchannel("A"))
            imagen = fondo
        else:
            imagen = imagen.convert("RGB")

    salida = BytesIO()
    imagen.save(salida, format="JPEG", quality=90)
    return salida.getvalue()


def crear_recortes_verificacion(contenido: bytes) -> list[bytes]:
    """Divide imágenes alargadas en tres zonas para verificar alimentos pequeños."""
    with Image.open(BytesIO(contenido)) as original:
        imagen = original.convert("RGB")

    ancho, alto = imagen.size
    min_dim = min(ancho, alto)
    max_dim = max(ancho, alto)
    
    if min_dim == 0 or max_dim / min_dim < 1.25:
        return []

    solape = max(2, round(alto * 0.025))
    limites = [round(alto * indice / 3) for indice in range(4)]
    recortes = []
    for indice in range(3):
        arriba = max(0, limites[indice] - (solape if indice else 0))
        abajo = min(alto, limites[indice + 1] + (solape if indice < 2 else 0))
        recorte = imagen.crop((0, arriba, ancho, abajo))
        if min(recorte.size) < 400:
            recorte = recorte.resize(
                (recorte.width * 3, recorte.height * 3),
                Image.Resampling.LANCZOS,
            )
        salida = BytesIO()
        recorte.save(salida, format="JPEG", quality=94)
        recortes.append(salida.getvalue())

    if ancho > alto * 1.25:
        recorte = imagen.crop((round(ancho * 0.28), 0, round(ancho * 0.63), alto))
        if min(recorte.size) < 400:
            recorte = recorte.resize(
                (recorte.width * 3, recorte.height * 3),
                Image.Resampling.LANCZOS,
            )
        salida = BytesIO()
        recorte.save(salida, format="JPEG", quality=94)
        recortes.append(salida.getvalue())

    return recortes


def normalizar_alimento(alimento: str) -> str:
    texto = unicodedata.normalize("NFKD", alimento.casefold())
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    texto = re.sub(r"[^a-z0-9 ]", " ", texto)
    texto = " ".join(texto.split())

    equivalencias = {
        "apple": "manzana",
        "apples": "manzana",
        "green apple": "manzana",
        "green apples": "manzana",
        "manzana verde": "manzana",
        "manzanas verdes": "manzana",
        "banana": "platano",
        "bananas": "platano",
        "platanos": "platano",
        "broccoli": "brocoli",
        "bell pepper": "pimiento",
        "bell peppers": "pimiento",
        "red bell pepper": "pimiento",
        "red bell peppers": "pimiento",
        "yellow bell pepper": "pimiento",
        "yellow bell peppers": "pimiento",
        "orange bell pepper": "pimiento",
        "orange bell peppers": "pimiento",
        "red pepper": "pimiento",
        "red peppers": "pimiento",
        "pimiento rojo": "pimiento",
        "pimientos rojos": "pimiento",
        "pimiento amarillo": "pimiento",
        "pimientos amarillos": "pimiento",
        "pimiento naranja": "pimiento",
        "pimientos naranjas": "pimiento",
        "pimientos": "pimiento",
        "paprika roja": "pimiento",
        "chicken": "pollo",
        "chicken breast": "pollo",
        "chicken breasts": "pollo",
        "pechuga de pollo": "pollo",
        "pechugas de pollo": "pollo",
        "pollo crudo": "pollo",
        "carrot": "zanahoria",
        "carrots": "zanahoria",
        "zanahoria": "zanahoria",
        "zanahorias": "zanahoria",
        "cherry tomato": "tomate",
        "cherry tomatoes": "tomate",
        "tomate cherry": "tomate",
        "tomates cherry": "tomate",
        "tomato": "tomate",
        "tomatoes": "tomate",
        "tomates rojos": "tomate",
        "mushroom": "champinon",
        "mushrooms": "champinon",
        "champinones": "champinon",
        "seta": "champinon",
        "setas": "champinon",
        "hongo": "champinon",
        "hongos": "champinon",
        "onion": "cebolla",
        "onions": "cebolla",
        "white onion": "cebolla",
        "white onions": "cebolla",
        "cebollas blancas": "cebolla",
        "cebolla roja": "cebolla",
        "cebolla morada": "cebolla",
        "salmon fillet": "salmon",
        "salmon fillets": "salmon",
        "salmon": "salmon",
        "lettuce leaves": "lechuga",
        "lettuce": "lechuga",
        "lettuces": "lechuga",
        "lechugas": "lechuga",
        "fresa": "fresa",
        "fresas": "fresa",
        "strawberry": "fresa",
        "strawberries": "fresa",
        "orange": "naranja",
        "oranges": "naranja",
        "lemon": "limon",
        "lemons": "limon",
        "limon": "limon",
        "limones": "limon",
        "naranja": "naranja",
        "naranjas": "naranja",
        "pineapple": "pina",
        "pineapples": "pina",
        "pina": "pina",
        "zucchini": "calabacin",
        "courgette": "calabacin",
        "courgettes": "calabacin",
        "calabacin": "calabacin",
        "calabacines": "calabacin",
        "eggplant": "berenjena",
        "eggplants": "berenjena",
        "berenjenas": "berenjena",
        "cabbage": "repollo",
        "cabbages": "repollo",
        "repollo": "repollo",
        "red cabbage": "repollo",
        "tomate": "tomate",
        "tomates": "tomate",
        "champinon": "champinon",
        "champinones": "champinon",
        "cogumelo": "champinon",
        "cogumelos": "champinon",
        "cebollas": "cebolla",
        "brocoli": "brocoli",
        "lechuga": "lechuga",
        "pollo": "pollo",
        "manzana": "manzana",
        "manzanas": "manzana",
        "platano": "platano",
        "manzana roja": "manzana",
        "tomates cereza": "tomate",
    }
    if texto in equivalencias:
        return equivalencias[texto]

    for prefijo, nombre in (
        ("apple ", "manzana"),
        ("banana ", "platano"),
        ("bananas ", "platano"),
        ("platanos ", "platano"),
        ("broccoli ", "brocoli"),
        ("bell pepper ", "pimiento"),
        ("bell peppers ", "pimiento"),
        ("manzana ", "manzana"),
        ("green apple ", "manzana"),
        ("green apples ", "manzana"),
        ("chicken ", "pollo"),
        ("pechuga de pollo ", "pollo"),
        ("pollo ", "pollo"),
        ("salmon ", "salmon"),
        ("cogumelo ", "champinon"),
        ("mushroom ", "champinon"),
        ("mushrooms ", "champinon"),
        ("champinones ", "champinon"),
        ("seta ", "champinon"),
        ("setas ", "champinon"),
        ("hongo ", "champinon"),
        ("hongos ", "champinon"),
        ("onion ", "cebolla"),
        ("cebolla blanca ", "cebolla"),
        ("white onion ", "cebolla"),
        ("cebolla blanca ", "cebolla"),
        ("cebolla morada ", "cebolla"),
        ("cebolla roja ", "cebolla"),
        ("salmon ", "salmon"),
        ("tomato ", "tomate"),
        ("lettuce ", "lechuga"),
        ("lechuga ", "lechuga"),
        ("pimientos ", "pimiento"),
        ("pimiento amarillo ", "pimiento"),
        ("pimiento verde ", "pimiento"),
        ("pimiento rojo ", "pimiento"),
        ("pimiento naranja ", "pimiento"),
        ("pimientos verdes ", "pimiento"),
        ("pimientos rojos ", "pimiento"),
        ("pimientos naranjas ", "pimiento"),
        ("pimientos amarillos ", "pimiento"),
        ("yellow bell pepper ", "pimiento"),
        ("orange bell pepper ", "pimiento"),
        ("red bell pepper ", "pimiento"),
        ("pimiento rojo ", "pimiento"),
        ("pimiento naranja ", "pimiento"),
        ("pimiento amarillo ", "pimiento"),
        ("pimientos rojos ", "pimiento"),
        ("pimientos naranjas ", "pimiento"),
        ("pimientos amarillos ", "pimiento"),
        ("cherry tomato ", "tomate"),
        ("cherry tomatoes ", "tomate"),
        ("tomate cherry ", "tomate"),
        ("tomates cherry ", "tomate"),
        ("tomates cherry rojos ", "tomate"),
        ("tomates cherry naranjas ", "tomate"),
        ("tomates cereza ", "tomate"),
        ("strawberry ", "fresa"),
        ("strawberries ", "fresa"),
        ("fresas rojas ", "fresa"),
        ("orange ", "naranja"),
        ("oranges ", "naranja"),
        ("naranja ", "naranja"),
        ("naranjas ", "naranja"),
        ("pineapple ", "pina"),
        ("pina ", "pina"),
        ("zucchini ", "calabacin"),
        ("calabacin ", "calabacin"),
        ("calabacín ", "calabacin"),
        ("eggplant ", "berenjena"),
        ("berenjena blanca ", "berenjena"),
        ("zanahoria ", "zanahoria"),
        ("zanahorias ", "zanahoria"),
    ):
        if texto.startswith(prefijo):
            return nombre
    return texto


def extraer_alimentos(texto: str) -> list[str]:
    alimentos = []
    vistos = set()
    for item in re.split(r"[,;\n|]+|\s+(?:y|and)\s+", texto, flags=re.IGNORECASE):
        nombre = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", item).strip().strip(" .)")
        nombre = re.sub(
            r"^(?:frutas?|verduras?|vegetales?)\s*:\s*",
            "",
            nombre,
            flags=re.IGNORECASE,
        )
        nombre = re.sub(
            r"^(?:frutas?|verduras?|vegetales?)\s*\(",
            "",
            nombre,
            flags=re.IGNORECASE,
        )
        nombre = re.sub(
            r"^(?:fruta|verdura|vegetales?)\b.*?\bcomo\s+",
            "",
            nombre,
            flags=re.IGNORECASE,
        )
        clave = normalizar_alimento(nombre)
        categoria = clave.split(maxsplit=1)[0] if clave else ""
        if (
            not nombre
            or clave in {"fruta", "frutas", "verdura", "verduras", "vegetal", "vegetales"}
            or categoria in {"fruta", "frutas", "verdura", "verduras", "vegetal", "vegetales"}
            or clave.startswith(
                ("ningun", "ninguno", "ninguna", "none", "no hay", "no food", "no se identific")
            )
            or clave.startswith(
                (
                    "en la imagen",
                    "estos son",
                    "alimentos visibles",
                    "no se incluyen",
                    "nota ",
                    "esto es todo",
                    "la descripcion",
                    "se pueden ver",
                )
            )
            or clave in vistos
        ):
            continue
        alimentos.append(clave)
        vistos.add(clave)
        if len(alimentos) >= MAX_ITEMS_PER_ANALYSIS:
            break
    return alimentos


def consolidar_alimentos(
    resultado_completo: list[str],
    resultados_recortes: list[list[str]],
    minimo_recortes: int = 1,
) -> list[str]:
    confirmaciones = {}
    for resultado in resultados_recortes:
        for alimento in set(resultado):
            confirmaciones[alimento] = confirmaciones.get(alimento, 0) + 1
    return [
        alimento
        for alimento in resultado_completo
        if confirmaciones.get(alimento, 0) >= minimo_recortes
    ]


def formatear_resultado(alimentos: list[str]) -> str:
    if not alimentos:
        return (
            "Alimentos identificables con certeza: ninguno.\n"
            "No se pudieron corroborar otros elementos con suficiente claridad. "
            "Los objetos pequeños, tapados o dudosos se omiten; prueba con una foto "
            "más cercana y nítida."
        )
    nombres = {
        "berenjena": "berenjena",
        "brocoli": "brócoli",
        "calabacin": "calabacín",
        "champinon": "champiñón",
        "fresa": "fresa",
        "naranja": "naranja",
        "pina": "piña",
        "platano": "plátano",
        "repollo": "repollo",
        "salmon": "salmón",
        "zanahoria": "zanahoria",
    }
    return (
        "Alimentos identificables con certeza:\n"
        + "\n".join(f"- {nombres.get(alimento, alimento)}" for alimento in alimentos)
        + "\n\nNo identificable con certeza: cualquier otro elemento dudoso se omite; "
        "no se infieren ingredientes ocultos."
    )


async def consultar_recorte(contenido: bytes, parte: str, modelo: str | None = None) -> list[str]:
    modelo_actual = modelo or VISION_MODEL
    imagen_completa = parte == "la imagen completa"
    if modelo_actual == VISION_MODEL_ADVANCED:
        opciones = {
            "num_ctx": 16384 if imagen_completa else 8192,
            "num_predict": 6144 if imagen_completa else 2048,
            "temperature": 0,
            "repeat_penalty": 1.15,
        }
    else:
        opciones = {
            "num_ctx": 4096,
            "num_predict": 256,
            "temperature": 0,
            "repeat_penalty": 1.3,
        }

    respuesta = await run_in_threadpool(
        ollama.chat,
        model=modelo_actual,
        options=opciones,
        messages=[{
            "role": "user",
            "content": VISION_PROMPT.format(parte=parte),
            "images": [contenido],
        }],
    )
    texto = (respuesta.message.content or "").strip()
    print(
        f"[Vision {parte}] modelo={modelo_actual} done={respuesta.done} reason={respuesta.done_reason} "
        f"content_chars={len(texto)} preview={texto[:180]!r}"
    )
    if respuesta.done_reason == "length":
        raise RuntimeError(
            f"{modelo_actual} agotó el presupuesto de generación al analizar {parte}."
        )
    if not texto:
        raise RuntimeError(f"{modelo_actual} no devolvió una respuesta final para {parte}.")
    return extraer_alimentos(texto)


async def consultar_imagen(contenido: bytes, usar_modelo_avanzado: bool = False) -> list[str]:
    """Analiza imagen: modelo base (3B) por defecto, 4B opcional si usar_modelo_avanzado=True."""
    modelo_a_usar = VISION_MODEL_ADVANCED if usar_modelo_avanzado else VISION_MODEL
    alimentos_completos = await consultar_recorte(contenido, "la imagen completa", modelo=modelo_a_usar)
    recortes = await run_in_threadpool(crear_recortes_verificacion, contenido)
    if not recortes:
        return alimentos_completos

    resultados_recortes = []
    for indice, recorte in enumerate(recortes, start=1):
        parte = "la zona central" if indice == 4 else f"la zona {indice}"
        resultados_recortes.append(
            await consultar_recorte(recorte, f"{parte} de la imagen", modelo=modelo_a_usar)
        )
    with Image.open(BytesIO(contenido)) as imagen:
        minimo_recortes = 2 if min(imagen.size) < 320 else 1
    confirmados = consolidar_alimentos(
        alimentos_completos,
        resultados_recortes,
        minimo_recortes=minimo_recortes,
    )
    print(
        f"[Vision consenso] modelo={modelo_a_usar} imagen={len(alimentos_completos)} "
        f"recortes={sum(map(len, resultados_recortes))} confirmados={len(confirmados)}"
    )
    return confirmados


@app.get("/")
def home():
    return {"message": "Welcome to the FastAPI application!"}


@app.post("/ask")
def ask_llama(request: PromptRequest):
    try:
        response = ollama.chat(
            model="llama3.2:3b",
            messages=[
                {"role": "system", "content": "Eres un asistente útil. Responde siempre en español."},
                {"role": "user", "content": request.prompt}
            ]
        )
        return {"answer": response.message.content}
    except Exception as error:
        print(f"Error de ollama: {error}")
        raise HTTPException(status_code=500, detail="Error al procesar la solicitud con el modelo de lenguaje.")


@app.post("/analizar")
async def analizar(imagen: UploadFile = File(...), usar_modelo_avanzado: bool = False):
    """Endpoint para analizar imagen. Parámetro usar_modelo_avanzado=true activa modelo 4B."""
    if not imagen.content_type or not imagen.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Selecciona un archivo de imagen válido.")

    contenido = await imagen.read(MAX_IMAGE_SIZE + 1)
    if len(contenido) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="La imagen debe pesar menos de 10 MB.")
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo de imagen está vacío.")

    try:
        imagen_completa = await run_in_threadpool(preparar_imagen, contenido)
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        raise HTTPException(status_code=400, detail="No se pudo leer la imagen. Prueba con un JPG o PNG válido.") from error

    try:
        modelo_actual = VISION_MODEL_ADVANCED if usar_modelo_avanzado else VISION_MODEL
        alimentos = await consultar_imagen(imagen_completa, usar_modelo_avanzado=usar_modelo_avanzado)
    except Exception as error:
        print(f"Error de Ollama al analizar la imagen: {error}")
        if isinstance(error, HTTPException):
            raise
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo analizar la imagen con {modelo_actual}. Revisa que Ollama esté activo y el modelo instalado.",
        ) from error

    return {"resultado": formatear_resultado(alimentos)}


@app.post("/analizar/stream")
async def analizar_stream(imagen: UploadFile = File(...), usar_modelo_avanzado: bool = False):
    """Endpoint streaming para analizar imagen. Parámetro usar_modelo_avanzado=true activa modelo 4B."""
    if not imagen.content_type or not imagen.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Selecciona un archivo de imagen válido.")

    contenido = await imagen.read(MAX_IMAGE_SIZE + 1)
    if len(contenido) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="La imagen debe pesar menos de 10 MB.")
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo de imagen está vacío.")

    try:
        imagen_completa = await run_in_threadpool(preparar_imagen, contenido)
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        raise HTTPException(status_code=400, detail="No se pudo leer la imagen. Prueba con un JPG o PNG válido.") from error

    async def generar_fragmentos():
        try:
            modelo_actual = VISION_MODEL_ADVANCED if usar_modelo_avanzado else VISION_MODEL
            yield json.dumps(
                {"type": "status", "message": f"Analizando con {modelo_actual}…"},
                ensure_ascii=False,
            ) + "\n"
            alimentos = await consultar_imagen(imagen_completa, usar_modelo_avanzado=usar_modelo_avanzado)
            yield json.dumps(
                {"type": "status", "message": "Preparando el resultado…"},
                ensure_ascii=False,
            ) + "\n"
            resultado = formatear_resultado(alimentos)
            yield json.dumps({"type": "token", "content": resultado}, ensure_ascii=False) + "\n"
            yield json.dumps({"type": "done"}) + "\n"
        except Exception as error:
            print(f"Error de Ollama al analizar la imagen: {error}")
            modelo_actual = VISION_MODEL_ADVANCED if usar_modelo_avanzado else VISION_MODEL
            yield json.dumps(
                {
                    "type": "error",
                    "detail": f"No se pudo analizar la imagen con {modelo_actual}. Revisa la salida de FastAPI y Ollama.",
                },
                ensure_ascii=False,
            ) + "\n"

    return StreamingResponse(
        generar_fragmentos(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
    