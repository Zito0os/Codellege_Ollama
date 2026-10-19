from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from ollama import chat

from recipe_llm import generate_recipes_with_ollama

app = FastAPI()
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
