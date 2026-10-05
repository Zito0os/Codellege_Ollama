from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ollama import chat
from typing import Literal, Optional

app = FastAPI()
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
    prompt: Optional[str] = None
    car_model: Optional[str] = None
    action: Optional[Literal["repair", "find_part", "replacement_instructions"]] = None
    description: Optional[str] = None


def build_prompt(request: PromptRequest) -> str:
    if request.prompt and request.prompt.strip():
        return request.prompt.strip()

    car_model = (request.car_model or "").strip()
    description = (request.description or "").strip()
    if not car_model or not description or not request.action:
        raise HTTPException(
            status_code=422,
            detail="Proporciona car_model, action y description, o bien prompt.",
        )

    actions = {
        "repair": "diagnostica el problema y explica posibles soluciones",
        "find_part": "identifica la pieza que podría causar el problema",
        "replacement_instructions": "explica cómo cambiar la pieza relacionada con el problema",
    }
    return (
        f"Vehículo: {car_model}. Solicitud: {actions[request.action]}. "
        f"Descripción del problema: {description}. "
        "Responde en español con pasos claros. Si falta información para un diagnóstico fiable, "
        "indica qué datos hacen falta y advierte cuando sea necesario acudir a un mecánico."
    )


def build_system_prompt(action: Optional[str]) -> str:
    base = (
        "Eres un asistente especializado en diagnóstico y mantenimiento automotriz. "
        "Responde siempre en español y prioriza la seguridad. Si faltan datos para una "
        "respuesta fiable o no conoces la información no continues con la respuesta."
    )
    styles = {
        "repair": (
            " Explica el diagnóstico y las posibles soluciones en un tono amigable y sencillo, "
            "sin asumir conocimientos mecánicos."
        ),
        "find_part": (
            " Indica el nombre de la pieza, su función y los síntomas que ayudan a identificarla. "
            "Aclara que el diagnóstico puede requerir inspección y confirma compatibilidad con año, "
            "marca, modelo y versión del vehículo."
        ),
        "replacement_instructions": (
            " Usa un tono técnico y preciso. Enumera herramientas, preparación, pasos de desmontaje "
            "y montaje, y comprobaciones finales. Advierte sobre riesgos y no inventes pares de apriete "
            "ni especificaciones; indica consultar el manual de servicio cuando correspondan."
        ),
    }
    return base + styles.get(action or "", "")


@app.get("/")
def home():
    return {"message": "Welcome to the FastAPI application!"}


@app.post("/ask")
def ask_llama(request: PromptRequest):
    prompt = build_prompt(request)
    try:
        response = chat(
            model="llama3.2:3b",
            messages=[
                {"role": "system", "content": build_system_prompt(request.action)},
                {"role": "user", "content": prompt}
            ]
        )
        return {"answer": response.message.content}
    except Exception as error:
        print(f"Error de ollama: {error}")
        raise HTTPException(status_code=500, detail="Error al procesar la solicitud con el modelo de lenguaje.")


    