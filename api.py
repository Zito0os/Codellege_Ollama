import json

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from starlette.concurrency import iterate_in_threadpool
from starlette.responses import StreamingResponse
import ollama

app = FastAPI()
MAX_IMAGE_SIZE = 10 * 1024 * 1024

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
        respuesta = await run_in_threadpool(
            ollama.chat,
            model="qwen3-vl:4b",
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Analiza esta fotografía de un refrigerador.\n\n"
                        "Identifica únicamente los alimentos e ingredientes que puedas reconocer visualmente. "
                        "No inventes ingredientes. Devuelve una lista con nombre, cantidad aproximada y nivel "
                        "de confianza. Si un ingrediente no es suficientemente visible, indícalo como incierto. "
                        "Responde en español."
                    ),
                    "images": [contenido],
                }
            ],
        )
        return {"resultado": respuesta.message.content}
    except Exception as error:
        print(f"Error de Ollama al analizar la imagen: {error}")
        raise HTTPException(
            status_code=502,
            detail="No se pudo analizar la imagen. Comprueba que Ollama esté activo y que qwen3-vl:4b esté instalado.",
        ) from error


@app.post("/analizar/stream")
async def analizar_stream(imagen: UploadFile = File(...)):
    if not imagen.content_type or not imagen.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Selecciona un archivo de imagen válido.")

    contenido = await imagen.read(MAX_IMAGE_SIZE + 1)
    if len(contenido) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="La imagen debe pesar menos de 10 MB.")
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo de imagen está vacío.")

    async def generar_fragmentos():
        try:
            flujo = await run_in_threadpool(
                ollama.chat,
                model="qwen3-vl:4b",
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Analiza esta fotografía de un refrigerador.\n\n"
                            "Identifica únicamente los alimentos e ingredientes que puedas reconocer visualmente. "
                            "No inventes ingredientes. Devuelve una lista con nombre, cantidad aproximada y nivel "
                            "de confianza. Si un ingrediente no es suficientemente visible, indícalo como incierto. "
                            "Responde en español."
                        ),
                        "images": [contenido],
                    }
                ],
                stream=True,
            )

            async for fragmento in iterate_in_threadpool(flujo):
                texto = fragmento.message.content
                if texto:
                    yield json.dumps({"type": "token", "content": texto}, ensure_ascii=False) + "\n"
                if fragmento.done:
                    yield json.dumps({"type": "done"}) + "\n"
                    return

            yield json.dumps({"type": "done"}) + "\n"
        except Exception as error:
            print(f"Error de Ollama al analizar la imagen: {error}")
            yield json.dumps(
                {
                    "type": "error",
                    "detail": (
                        "No se pudo analizar la imagen. Comprueba que Ollama esté activo "
                        "y que qwen3-vl:4b esté instalado."
                    ),
                },
                ensure_ascii=False,
            ) + "\n"

    return StreamingResponse(
        generar_fragmentos(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
    