import json
import os
import re
import shutil
import subprocess
import time
import unicodedata
from io import BytesIO

from fastapi import APIRouter, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from PIL import Image, ImageOps
from pydantic import BaseModel
from starlette.responses import StreamingResponse
import ollama

from image_optimizer import PreparedImage, prepare_image

app = FastAPI()
router = APIRouter()
MAX_IMAGE_SIZE = 10 * 1024 * 1024
MAX_IMAGE_DIMENSION = 1280
VISION_MODEL = "llama3.2-vision:11b"
VISION_PROMPT = (
    "Eres un sistema de inventario visual de alimentos. Examina únicamente lo que se ve "
    "en la foto: recorre el refrigerador de arriba abajo y cada estante de izquierda a "
    "derecha; inspecciona también los cajones. Devuelve nombres concretos de alimentos "
    "en español, sin repetir un tipo aunque haya varias piezas. No uses categorías "
    "generales como fruta, verdura, carne o lácteo. No infieras el contenido de recipientes "
    "opacos ni alimentos que suelen guardarse en un refrigerador. Omite lo que no puedas "
    "identificar visualmente con confianza. No añadas explicaciones ni inventes alimentos."
)
MAX_ITEMS_PER_ANALYSIS = 20
VISION_FORMAT = {
    "type": "object",
    "properties": {
        "alimentos": {
            "type": "array",
            "items": {"type": "string", "maxLength": 32},
            "maxItems": MAX_ITEMS_PER_ANALYSIS,
        }
    },
    "required": ["alimentos"],
    "additionalProperties": False,
}

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

    imagen.thumbnail(
        (MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION),
        Image.Resampling.LANCZOS,
    )
    salida = BytesIO()
    imagen.save(salida, format="JPEG", quality=88)
    return salida.getvalue()


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
        "avocado": "aguacate",
        "avocados": "aguacate",
        "banana": "platano",
        "bananas": "platano",
        "platanos": "platano",
        "broccoli": "brocoli",
        "cauliflower": "coliflor",
        "cauliflowers": "coliflor",
        "cauliflor": "coliflor",
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
        "carrota": "zanahoria",
        "carrotas": "zanahoria",
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
        "green onion": "cebolla",
        "green onions": "cebolla",
        "scallion": "cebollin",
        "scallions": "cebollin",
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
        "milk": "leche",
        "whole milk": "leche",
        "egg": "huevo",
        "eggs": "huevo",
        "cheese": "queso",
        "butter": "mantequilla",
        "yogurt": "yogur",
        "yoghurt": "yogur",
        "grape": "uva",
        "grapes": "uva",
        "green grapes": "uva",
        "blueberry": "arandano",
        "blueberries": "arandano",
        "corn": "maiz",
        "sweetcorn": "maiz",
        "maize": "maiz",
        "potato": "papa",
        "potatoes": "papa",
        "cucumber": "pepino",
        "cucumbers": "pepino",
        "bread": "pan",
        "fish": "pescado",
        "sausage": "salchicha",
        "sausages": "salchicha",
        "ham": "jamon",
        "peach": "durazno",
        "peaches": "durazno",
        "orange juice": "jugo de naranja",
        "jam": "mermelada",
        "marmalade": "mermelada",
        "marmelada": "mermelada",
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


def formatear_resultado(alimentos: list[str]) -> str:
    if not alimentos:
        return (
            "Alimentos identificables con certeza: ninguno.\n"
            "No se pudieron corroborar otros elementos con suficiente claridad. "
            "Los objetos pequeños, tapados o dudosos se omiten; prueba con una foto "
            "más cercana y nítida."
        )
    nombres = {
        "arandano": "arándano",
        "aguacate": "aguacate",
        "berenjena": "berenjena",
        "brocoli": "brócoli",
        "calabacin": "calabacín",
        "champinon": "champiñón",
        "cebollin": "cebollín",
        "coliflor": "coliflor",
        "durazno": "durazno",
        "fresa": "fresa",
        "jamon": "jamón",
        "maiz": "maíz",
        "naranja": "naranja",
        "papa": "papa",
        "pina": "piña",
        "platano": "plátano",
        "repollo": "repollo",
        "salmon": "salmón",
        "zanahoria": "zanahoria",
        "uva": "uva",
    }
    return (
        "Alimentos identificables con certeza:\n"
        + "\n".join(f"- {nombres.get(alimento, alimento)}" for alimento in alimentos)
        + "\n\nNo identificable con certeza: cualquier otro elemento dudoso se omite; "
        "no se infieren ingredientes ocultos."
    )


async def consultar_imagen(
    contenido: bytes,
    contexto_global: list[str] | None = None,
) -> list[str]:
    opciones = {
        "num_ctx": 4096,
        "num_predict": 192,
        "temperature": 0,
        "repeat_penalty": 1.1,
    }
    prompt = VISION_PROMPT
    if contexto_global is not None:
        prompt += (
            "\nLa imagen adjunta es un recorte de detalle de la misma fotografía. "
            "Examina únicamente lo que aparece dentro del recorte e identifica alimentos "
            "pequeños que pudieron pasar inadvertidos en la vista general. No enumeres "
            "alimentos que no se vean en este recorte ni infieras su contenido por el "
            "contexto del refrigerador."
        )

    respuesta = await run_in_threadpool(
        ollama.chat,
        model=VISION_MODEL,
        keep_alive="1m",
        format=VISION_FORMAT,
        options=opciones,
        messages=[{
            "role": "user",
            "content": prompt,
            "images": [contenido],
        }],
    )
    texto = (respuesta.message.content or "").strip()
    print(
        f"[Vision {'recorte' if contexto_global is not None else 'imagen completa'}] "
        f"modelo={VISION_MODEL} done={respuesta.done} reason={respuesta.done_reason} "
        f"content_chars={len(texto)} preview={texto[:180]!r}"
    )
    if not texto:
        raise RuntimeError(f"{VISION_MODEL} no devolvió una respuesta final.")
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError:
        if respuesta.done_reason == "length":
            raise RuntimeError(f"{VISION_MODEL} agotó el límite de tokens de salida.")
        return extraer_alimentos(texto)
    if (
        not isinstance(datos, dict)
        or not isinstance(datos.get("alimentos"), list)
        or not all(isinstance(alimento, str) for alimento in datos["alimentos"])
    ):
        raise RuntimeError(f"{VISION_MODEL} devolvió una respuesta estructurada inválida.")
    if respuesta.done_reason == "length":
        print(
            f"[Vision advertencia] {VISION_MODEL} alcanzó num_predict; "
            "se usarán únicamente los alimentos del JSON completo."
        )
    return extraer_alimentos(", ".join(datos["alimentos"]))


def _medir_recursos() -> dict[str, float | None]:
    memoria_ram_mb = None
    memoria_vram_mb = None

    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        try:
            kernel32 = ctypes.WinDLL("Kernel32.dll")
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            process = kernel32.GetCurrentProcess()
            get_memory_info = ctypes.WinDLL("Psapi.dll").GetProcessMemoryInfo
            get_memory_info.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(ProcessMemoryCounters),
                wintypes.DWORD,
            ]
            get_memory_info.restype = wintypes.BOOL
            if get_memory_info(process, ctypes.byref(counters), counters.cb):
                memoria_ram_mb = counters.WorkingSetSize / (1024 * 1024)
        except (AttributeError, OSError) as error:
            print(f"[Vision métricas] No se pudo medir RAM del proceso: {error}")

    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        try:
            resultado = subprocess.run(
                [
                    nvidia_smi,
                    "--query-gpu=memory.used",
                    "--format=csv,noheader,nounits",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=2,
            )
            memoria_vram_mb = float(resultado.stdout.splitlines()[0].strip())
        except (
            FileNotFoundError,
            IndexError,
            ValueError,
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
        ):
            print("[Vision métricas] No se pudo medir el uso global de VRAM.")

    return {"ram_mb": memoria_ram_mb, "vram_mb": memoria_vram_mb}


async def preparar_imagen_optimizada(
    contenido: bytes,
) -> tuple[PreparedImage, float, float, dict[str, float | None]]:
    inicio_total = time.perf_counter()
    recursos_antes = await run_in_threadpool(_medir_recursos)
    inicio_preprocesamiento = time.perf_counter()
    preparada: PreparedImage = await run_in_threadpool(prepare_image, contenido)
    tiempo_preprocesamiento = time.perf_counter() - inicio_preprocesamiento
    return preparada, inicio_total, tiempo_preprocesamiento, recursos_antes


async def analizar_preparada(
    preparada: PreparedImage,
    inicio_total: float,
    tiempo_preprocesamiento: float,
    recursos_antes: dict[str, float | None],
) -> list[str]:
    inicio_inferencia = time.perf_counter()
    llamadas = 0
    alimentos: list[str] = []
    try:
        llamadas += 1
        globales = await consultar_imagen(preparada.full_image)
        alimentos.extend(globales)

        if preparada.uses_regions:
            for region in preparada.regions:
                print(
                    "[Vision región] "
                    f"coordenadas={region.coordinates} "
                    f"resolucion={region.width}x{region.height}"
                )
                llamadas += 1
                alimentos.extend(
                    await consultar_imagen(region.image, contexto_global=globales)
                )
        return extraer_alimentos(", ".join(alimentos))
    finally:
        tiempo_inferencia = time.perf_counter() - inicio_inferencia
        recursos_despues = await run_in_threadpool(_medir_recursos)
        resoluciones = [
            f"global={preparada.full_width}x{preparada.full_height}"
        ]
        resoluciones.extend(
            f"crop@{region.coordinates}={region.width}x{region.height}"
            for region in preparada.regions
        )
        print(
            "[Vision métricas] "
            f"preprocesamiento={tiempo_preprocesamiento:.3f}s "
            f"inferencia={tiempo_inferencia:.3f}s "
            f"total={time.perf_counter() - inicio_total:.3f}s "
            f"llamadas_ollama={llamadas} recortes={len(preparada.regions)} "
            f"original={preparada.original_width}x{preparada.original_height} "
            f"inspeccion={preparada.inspection_width}x{preparada.inspection_height} "
            f"calidad={preparada.quality_score:.3f} ruido={preparada.noise_level:.2f} "
            f"score_complementario={preparada.complement_score:.3f} "
            f"imagenes_enviadas={resoluciones} "
            f"ram_mb={recursos_antes['ram_mb']}->{recursos_despues['ram_mb']} "
            f"vram_gpu_mb={recursos_antes['vram_mb']}->{recursos_despues['vram_mb']}"
        )


async def analizar_imagen_optimizada(contenido: bytes) -> list[str]:
    preparada, inicio_total, tiempo_preprocesamiento, recursos_antes = (
        await preparar_imagen_optimizada(contenido)
    )
    return await analizar_preparada(
        preparada, inicio_total, tiempo_preprocesamiento, recursos_antes
    )


def detalle_error_ollama(error: Exception) -> str:
    mensaje = str(error)
    if "requires more system memory" in mensaje.casefold():
        return (
            f"Ollama no tiene memoria libre suficiente para cargar {VISION_MODEL}. "
            f"{mensaje} Cierra aplicaciones para liberar memoria y vuelve a intentarlo."
        )
    return f"No se pudo analizar la imagen con {VISION_MODEL}: {mensaje}"


@app.get("/")
def home():
    return {"message": "Welcome to the FastAPI application!"}


@app.post("/ask")
def ask_llama(request: PromptRequest):
    try:
        response = ollama.chat(
            model=VISION_MODEL,
            messages=[
                {"role": "system", "content": "Eres un asistente útil. Responde siempre en español."},
                {"role": "user", "content": request.prompt}
            ]
        )
        return {"answer": response.message.content}
    except Exception as error:
        print(f"Error de ollama: {error}")
        raise HTTPException(status_code=500, detail="Error al procesar la solicitud con el modelo de lenguaje.")


@router.post("/analizar")
async def analizar(imagen: UploadFile = File(...)):
    """Endpoint para analizar una imagen con el único modelo de visión configurado."""
    if not imagen.content_type or not imagen.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Selecciona un archivo de imagen válido.")

    contenido = await imagen.read(MAX_IMAGE_SIZE + 1)
    if len(contenido) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="La imagen debe pesar menos de 10 MB.")
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo de imagen está vacío.")

    try:
        preparada, inicio_total, tiempo_preprocesamiento, recursos_antes = (
            await preparar_imagen_optimizada(contenido)
        )
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        raise HTTPException(status_code=400, detail="No se pudo leer la imagen. Prueba con un JPG o PNG válido.") from error

    try:
        alimentos = await analizar_preparada(
            preparada, inicio_total, tiempo_preprocesamiento, recursos_antes
        )
    except Exception as error:
        print(f"Error de Ollama al analizar la imagen: {error}")
        if isinstance(error, HTTPException):
            raise
        raise HTTPException(
            status_code=502,
            detail=detalle_error_ollama(error),
        ) from error

    return {"resultado": formatear_resultado(alimentos)}


@router.post("/analizar/stream")
async def analizar_stream(imagen: UploadFile = File(...)):
    """Endpoint streaming con el único modelo de visión configurado."""
    if not imagen.content_type or not imagen.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Selecciona un archivo de imagen válido.")

    contenido = await imagen.read(MAX_IMAGE_SIZE + 1)
    if len(contenido) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="La imagen debe pesar menos de 10 MB.")
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo de imagen está vacío.")

    try:
        preparada, inicio_total, tiempo_preprocesamiento, recursos_antes = (
            await preparar_imagen_optimizada(contenido)
        )
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        raise HTTPException(status_code=400, detail="No se pudo leer la imagen. Prueba con un JPG o PNG válido.") from error

    async def generar_fragmentos():
        try:
            yield json.dumps(
                {"type": "status", "message": f"Analizando con {VISION_MODEL}…"},
                ensure_ascii=False,
            ) + "\n"
            alimentos = await analizar_preparada(
                preparada, inicio_total, tiempo_preprocesamiento, recursos_antes
            )
            yield json.dumps(
                {"type": "status", "message": "Preparando el resultado…"},
                ensure_ascii=False,
            ) + "\n"
            resultado = formatear_resultado(alimentos)
            yield json.dumps({"type": "token", "content": resultado}, ensure_ascii=False) + "\n"
            yield json.dumps({"type": "done"}) + "\n"
        except Exception as error:
            print(f"Error de Ollama al analizar la imagen: {error}")
            yield json.dumps(
                {
                    "type": "error",
                    "detail": detalle_error_ollama(error),
                },
                ensure_ascii=False,
            ) + "\n"

    return StreamingResponse(
        generar_fragmentos(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


app.include_router(router)
    