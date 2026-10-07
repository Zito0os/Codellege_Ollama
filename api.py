import json
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
MIN_SPLIT_DIMENSION = 640
MIN_SPLIT_HEIGHT = 400
CROP_OVERLAP_RATIO = 0.08

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


def crear_recortes(contenido: bytes) -> list[tuple[str, bytes]]:
    with Image.open(BytesIO(contenido)) as original:
        imagen = ImageOps.exif_transpose(original)
        if "A" in imagen.getbands():
            rgba = imagen.convert("RGBA")
            fondo = Image.new("RGB", rgba.size, "white")
            fondo.paste(rgba, mask=rgba.getchannel("A"))
            imagen = fondo
        else:
            imagen = imagen.convert("RGB")

    ancho, alto = imagen.size
    dividir_x = ancho >= MIN_SPLIT_DIMENSION
    dividir_y = alto >= MIN_SPLIT_HEIGHT
    if dividir_x:
        mitad_x = ancho // 2
        solape_x = round(ancho * CROP_OVERLAP_RATIO / 2)
        columnas = [(0, mitad_x + solape_x), (mitad_x - solape_x, ancho)]
    else:
        columnas = [(0, ancho)]
    if dividir_y:
        mitad_y = alto // 2
        solape_y = round(alto * CROP_OVERLAP_RATIO / 2)
        filas = [(0, mitad_y + solape_y), (mitad_y - solape_y, alto)]
    else:
        filas = [(0, alto)]

    etiquetas_x = ["izquierda", "derecha"] if dividir_x else [""]
    etiquetas_y = ["superior", "inferior"] if dividir_y else [""]
    recortes = []
    for indice_y, (arriba, abajo) in enumerate(filas):
        for indice_x, (izquierda, derecha) in enumerate(columnas):
            partes = [etiqueta for etiqueta in (etiquetas_y[indice_y], etiquetas_x[indice_x]) if etiqueta]
            etiqueta = " ".join(partes) if partes else "imagen completa"
            salida = BytesIO()
            imagen.crop((izquierda, arriba, derecha, abajo)).save(salida, format="JPEG", quality=90)
            recortes.append((etiqueta, salida.getvalue()))
    return recortes


def dividir_recorte(contenido: bytes) -> list[tuple[str, bytes]]:
    with Image.open(BytesIO(contenido)) as original:
        imagen = original.convert("RGB")

    ancho, alto = imagen.size
    if ancho >= alto:
        mitad = ancho // 2
        solape = round(ancho * CROP_OVERLAP_RATIO / 2)
        regiones = [("ampliación izquierda", (0, 0, mitad + solape, alto)),
                    ("ampliación derecha", (mitad - solape, 0, ancho, alto))]
    else:
        mitad = alto // 2
        solape = round(alto * CROP_OVERLAP_RATIO / 2)
        regiones = [("ampliación superior", (0, 0, ancho, mitad + solape)),
                    ("ampliación inferior", (0, mitad - solape, ancho, alto))]

    subrecortes = []
    for etiqueta, caja in regiones:
        recorte = imagen.crop(caja)
        ampliado = recorte.resize((recorte.width * 2, recorte.height * 2), Image.Resampling.LANCZOS)
        salida = BytesIO()
        ampliado.save(salida, format="JPEG", quality=92)
        subrecortes.append((etiqueta, salida.getvalue()))
    return subrecortes


def prompt_recorte(etiqueta: str) -> str:
    return "¿Qué alimentos ves? Responde solo con nombres separados por coma. Sin explicación."


def consolidar_observaciones(resultados: list[tuple[str, str]]) -> str:
    hallazgos: dict[str, dict[str, list[str] | str]] = {}
    for zona, texto in resultados:
        for linea in texto.replace("\n", ",").split(","):
            contenido = linea.strip().lstrip("-*• ").strip().rstrip(".;")
            if not contenido:
                continue
            clave = " ".join(contenido.split()).casefold()
            if not clave:
                continue
            if clave not in hallazgos:
                hallazgos[clave] = {"texto": contenido, "zonas": [zona]}
            elif zona not in hallazgos[clave]["zonas"]:
                hallazgos[clave]["zonas"].append(zona)

    lineas = []
    for hallazgo in hallazgos.values():
        zonas = hallazgo["zonas"]
        referencia = f" (coincide en: {', '.join(zonas)})" if len(zonas) > 1 else f" ({zonas[0]})"
        lineas.append(f"- {hallazgo['texto']}{referencia}")
    return "Alimentos identificados:\n" + "\n".join(lineas) if lineas else ""


async def consultar_recorte(etiqueta: str, contenido: bytes) -> str:
    respuesta = await run_in_threadpool(
        ollama.chat,
        model=VISION_MODEL,
        think=False,
        options={"num_predict": 1024, "temperature": 0.1},
        messages=[{"role": "user", "content": prompt_recorte(etiqueta), "images": [contenido]}],
    )
    texto = (respuesta.message.content or "").strip()
    print(
        f"[Vision {etiqueta}] done={respuesta.done} reason={respuesta.done_reason} "
        f"content_chars={len(texto)} preview={texto[:180]!r}"
    )
    return texto


async def consultar_recorte_resistente(etiqueta: str, contenido: bytes) -> list[tuple[str, str]]:
    texto = await consultar_recorte(etiqueta, contenido)
    if texto:
        return [(etiqueta, texto)]

    print(f"[Vision {etiqueta}] sin texto; reintentando en dos subrecortes ampliados")
    subrecortes = await run_in_threadpool(dividir_recorte, contenido)
    resultados = []
    for subetiqueta, subrecorte in subrecortes:
        texto = await consultar_recorte(f"{etiqueta}, {subetiqueta}", subrecorte)
        if texto:
            resultados.append((f"{etiqueta}, {subetiqueta}", texto))
    return resultados


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
async def analizar(imagen: UploadFile = File(...)):
    if not imagen.content_type or not imagen.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Selecciona un archivo de imagen válido.")

    contenido = await imagen.read(MAX_IMAGE_SIZE + 1)
    if len(contenido) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="La imagen debe pesar menos de 10 MB.")
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo de imagen está vacío.")

    try:
        recortes = await run_in_threadpool(crear_recortes, contenido)
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        raise HTTPException(status_code=400, detail="No se pudo leer la imagen. Prueba con un JPG o PNG válido.") from error

    try:
        observaciones = []
        for etiqueta, recorte in recortes:
            observaciones.extend(await consultar_recorte_resistente(etiqueta, recorte))
        if not observaciones:
            raise HTTPException(status_code=502, detail="El modelo no identificó contenido en los recortes de la imagen.")
    except Exception as error:
        print(f"Error de Ollama al analizar la imagen: {error}")
        if isinstance(error, HTTPException):
            raise
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo analizar la imagen con {VISION_MODEL}. Revisa que Ollama esté activo y el modelo instalado.",
        ) from error

    resultado = consolidar_observaciones(observaciones)
    if not resultado:
        raise HTTPException(
            status_code=502,
            detail="El modelo no devolvió texto en ninguno de los recortes.",
        )
    return {"resultado": resultado}


@app.post("/analizar/stream")
async def analizar_stream(imagen: UploadFile = File(...)):
    if not imagen.content_type or not imagen.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Selecciona un archivo de imagen válido.")

    contenido = await imagen.read(MAX_IMAGE_SIZE + 1)
    if len(contenido) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="La imagen debe pesar menos de 10 MB.")
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo de imagen está vacío.")

    try:
        recortes = await run_in_threadpool(crear_recortes, contenido)
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        raise HTTPException(status_code=400, detail="No se pudo leer la imagen. Prueba con un JPG o PNG válido.") from error

    async def generar_fragmentos():
        try:
            observaciones = []
            for indice, (etiqueta, recorte) in enumerate(recortes, start=1):
                yield json.dumps(
                    {"type": "status", "message": f"Analizando zona {indice} de {len(recortes)}…"},
                    ensure_ascii=False,
                ) + "\n"
                observaciones.extend(await consultar_recorte_resistente(etiqueta, recorte))

            if not observaciones:
                yield json.dumps(
                    {
                        "type": "error",
                        "detail": "El modelo no identificó contenido en los recortes de la imagen.",
                    },
                    ensure_ascii=False,
                ) + "\n"
                return

            resultado = consolidar_observaciones(observaciones)
            if not resultado:
                yield json.dumps(
                    {"type": "error", "detail": "El modelo no devolvió texto en ninguno de los recortes."},
                    ensure_ascii=False,
                ) + "\n"
                return
            yield json.dumps(
                {"type": "status", "message": "Uniendo alimentos y quitando duplicados…"},
                ensure_ascii=False,
            ) + "\n"
            yield json.dumps({"type": "token", "content": resultado}, ensure_ascii=False) + "\n"
            yield json.dumps({"type": "done"}) + "\n"
        except Exception as error:
            print(f"Error de Ollama al analizar la imagen: {error}")
            yield json.dumps(
                {
                    "type": "error",
                    "detail": f"No se pudo analizar la imagen con {VISION_MODEL}. Revisa la salida de FastAPI y Ollama.",
                },
                ensure_ascii=False,
            ) + "\n"

    return StreamingResponse(
        generar_fragmentos(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
    