from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel, Field
from ollama import chat

from Analisis_imagen import MAX_IMAGE_SIZE, router as vision_router
from image_optimizer import prepare_image
from recipe_llm import generate_recipes_with_ollama

app = FastAPI()
app.include_router(vision_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


class PromptRequest(BaseModel):
    prompt: str


class IngredientIn(BaseModel):
    name: str
    qty: str | float | int | None = None
    unit: str | None = None
    amount: str | None = None


class GenerateRecipesRequest(BaseModel):
    ingredients: list[IngredientIn] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    note: str = ""
    count: int = 4


@app.get("/")
def home():
    return {"message": "Welcome to the FastAPI application!"}


@app.post("/ask")
def ask_llama(request: PromptRequest):
    try:
        response = chat(
            model="llama3.2:3b",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un asistente útil. Responde siempre en español.",
                },
                {"role": "user", "content": request.prompt},
            ],
        )
        return {"answer": response.message.content}
    except Exception as error:
        print(f"Error de ollama: {error}")
        raise HTTPException(
            status_code=500,
            detail="Error al procesar la solicitud con el modelo de lenguaje.",
        ) from error


@app.post("/recipes/generate")
def generate_recipes(request: GenerateRecipesRequest):
    if not request.ingredients:
        raise HTTPException(status_code=400, detail="Agrega al menos un ingrediente.")
    if request.count < 1 or request.count > 8:
        raise HTTPException(status_code=400, detail="count debe estar entre 1 y 8.")

    try:
        recipes = generate_recipes_with_ollama(
            ingredients=[item.model_dump() for item in request.ingredients],
            types=request.types or ["Rápida"],
            tools=request.tools or [],
            note=request.note or "",
            count=request.count,
        )
        return {"recipes": recipes}
    except ValueError as error:
        print(f"Error de parseo/normalización: {error}")
        raise HTTPException(status_code=502, detail=str(error)) from error
    except Exception as error:
        print(f"Error de ollama (recipes): {error}")
        raise HTTPException(
            status_code=500,
            detail="No se pudieron generar recetas con Ollama. Revisa que el servicio esté activo.",
        ) from error


@app.post("/imagen/optimizar")
async def optimizar_imagen(imagen: UploadFile = File(...)):
    """Prepara una imagen con el optimizador, sin enviarla al modelo de visión."""
    if not imagen.content_type or not imagen.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Selecciona un archivo de imagen válido.")

    contenido = await imagen.read(MAX_IMAGE_SIZE + 1)
    if len(contenido) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=413, detail="La imagen debe pesar menos de 10 MB.")
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo de imagen está vacío.")

    try:
        preparada = await run_in_threadpool(prepare_image, contenido)
    except (OSError, ValueError, Image.DecompressionBombError) as error:
        raise HTTPException(
            status_code=400,
            detail="No se pudo leer la imagen. Prueba con un JPG o PNG válido.",
        ) from error

    return {
        "original": {
            "width": preparada.original_width,
            "height": preparada.original_height,
        },
        "optimized": {
            "width": preparada.full_width,
            "height": preparada.full_height,
            "bytes": len(preparada.full_image),
        },
        "inspection": {
            "width": preparada.inspection_width,
            "height": preparada.inspection_height,
        },
        "quality_score": preparada.quality_score,
        "noise_level": preparada.noise_level,
        "complement_score": preparada.complement_score,
        "uses_regions": preparada.uses_regions,
        "regions": [
            {
                "coordinates": list(region.coordinates),
                "width": region.width,
                "height": region.height,
            }
            for region in preparada.regions
        ],
    }
