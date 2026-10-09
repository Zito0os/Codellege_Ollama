import json
import math
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from ollama import chat
from typing import Literal, Optional

app = FastAPI()
nearby_cache = {}
NEARBY_RADIUS_METERS = 5_000
NEARBY_PER_CATEGORY = 5
NEARBY_CACHE_VERSION = 2
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


class NearbyPlacesRequest(BaseModel):
    mode: Literal["repair", "install"]
    location: str
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class ReverseLocationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


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
        "respuesta fiable o no conoces la información no continues con la respuesta. "
        "No uses markdown con asteriscos ni listas tipo '*'. Presenta la información en texto plano "
        "y ordenado, con títulos cortos y listas con numeración o guiones simples. "
        "Ejemplo: 'Características generales:\n1. Clase: ...\n2. Modelo: ...\n\nDiagnóstico:'"
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


@app.post("/nearby-places")
def find_nearby_places(request: NearbyPlacesRequest):
    user_agent = "AutoGuia/1.0 (nearby automotive business lookup)"
    if (request.latitude is None) != (request.longitude is None):
        raise HTTPException(status_code=422, detail="Debes enviar latitud y longitud juntas.")

    if request.latitude is not None and request.longitude is not None:
        latitude = request.latitude
        longitude = request.longitude
    else:
        try:
            geocode_url = "https://nominatim.openstreetmap.org/search?" + urlencode({
                "q": request.location,
                "format": "jsonv2",
                "limit": 1,
            })
            geocode_request = Request(geocode_url, headers={"User-Agent": user_agent})
            with urlopen(geocode_request, timeout=15) as response:
                locations = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise HTTPException(status_code=502, detail="No se pudo localizar esa dirección.") from error
        except (URLError, TimeoutError) as error:
            raise HTTPException(status_code=502, detail="No se pudo conectar con el servicio de ubicación.") from error

        if not locations:
            raise HTTPException(status_code=404, detail="No encontramos esa ubicación. Prueba con una dirección o colonia más específica.")

        latitude = float(locations[0]["lat"])
        longitude = float(locations[0]["lon"])
    cache_key = (
        NEARBY_CACHE_VERSION,
        request.mode,
        round(latitude, 4),
        round(longitude, 4),
        NEARBY_RADIUS_METERS,
        NEARBY_PER_CATEGORY,
    )
    cached_result = nearby_cache.get(cache_key)
    if cached_result and cached_result["expires_at"] > time.time():
        return cached_result["result"]

    # Talleres + autopartes (AutoZone, etc.) + vulcanizadoras / llanteras
    overpass_query = (
        f"[out:json][timeout:20];"
        f"("
        f'nwr(around:{NEARBY_RADIUS_METERS},{latitude},{longitude})["shop"="car_repair"];'
        f'nwr(around:{NEARBY_RADIUS_METERS},{latitude},{longitude})["craft"="car_repair"];'
        f'nwr(around:{NEARBY_RADIUS_METERS},{latitude},{longitude})["shop"="car_parts"];'
        f'nwr(around:{NEARBY_RADIUS_METERS},{latitude},{longitude})["shop"="tyres"];'
        f");"
        "out center tags;"
    )
    data = None
    upstream_errors = []
    for endpoint in ("https://overpass-api.de/api/interpreter",):
        overpass_request = Request(
            endpoint,
            data=urlencode({"data": overpass_query}).encode("utf-8"),
            headers={"User-Agent": user_agent, "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urlopen(overpass_request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
            break
        except HTTPError as error:
            upstream_errors.append(error.code)
            print(f"Error de Overpass en {endpoint}: HTTP {error.code} {error.reason}")
        except (URLError, TimeoutError) as error:
            upstream_errors.append(type(error).__name__)
            print(f"Error de conexión Overpass en {endpoint}: {error}")

    source = "OpenStreetMap"
    if data is None:
        elements = []
        seen_places = set()
        search_terms = (
            "taller",
            "mecánico",
            "autozone",
            "refaccionaria",
            "autopartes",
            "vulcanizadora",
            "llantera",
        )
        accepted_values = {"car_repair", "car_parts", "car", "tyres"}
        for search_term in search_terms:
            photon_url = "https://photon.komoot.io/api/?" + urlencode({
                "q": search_term,
                "lat": latitude,
                "lon": longitude,
                "limit": 100,
            })
            photon_request = Request(photon_url, headers={"User-Agent": user_agent})
            try:
                with urlopen(photon_request, timeout=15) as response:
                    photon_data = json.loads(response.read().decode("utf-8"))
            except (HTTPError, URLError, TimeoutError) as error:
                print(f"Error de respaldo Photon para '{search_term}': {error}")
                continue

            for feature in photon_data.get("features", []):
                properties = feature.get("properties", {})
                point = feature.get("geometry", {}).get("coordinates", [])
                if len(point) < 2 or not properties.get("name"):
                    continue
                osm_key = properties.get("osm_key")
                osm_value = properties.get("osm_value")
                name = properties["name"].casefold()
                is_automotive_shop = osm_key == "shop" and osm_value in accepted_values
                is_repair_craft = osm_key == "craft" and osm_value == "car_repair"
                looks_automotive = any(
                    token in name
                    for token in (
                        "taller",
                        "mecán",
                        "mecan",
                        "autozone",
                        "refaccion",
                        "autoparte",
                        "vulcaniz",
                        "llanta",
                        "tyre",
                        "tire",
                    )
                )
                if not (is_automotive_shop or is_repair_craft or looks_automotive):
                    continue
                identity = (properties.get("osm_type"), properties.get("osm_id"))
                if identity == (None, None):
                    identity = (name, round(point[1], 5), round(point[0], 5))
                if identity in seen_places:
                    continue
                seen_places.add(identity)
                tags = {"name": properties["name"]}
                if osm_key and osm_value:
                    tags[osm_key] = osm_value
                for source_key, target_key in (
                    ("street", "addr:street"),
                    ("housenumber", "addr:housenumber"),
                    ("district", "addr:suburb"),
                    ("city", "addr:city"),
                ):
                    if properties.get(source_key):
                        tags[target_key] = properties[source_key]
                osm_id = properties.get("osm_id", len(elements))
                elements.append({
                    "type": properties.get("osm_type", "photon"),
                    "id": osm_id,
                    "tags": tags,
                    "lon": point[0],
                    "lat": point[1],
                })
        data = {"elements": elements}
        source = "OpenStreetMap (Photon)"

    def distance_meters(place_latitude: float, place_longitude: float) -> float:
        earth_radius = 6_371_000
        lat1 = math.radians(latitude)
        lat2 = math.radians(place_latitude)
        delta_lat = math.radians(place_latitude - latitude)
        delta_lon = math.radians(place_longitude - longitude)
        haversine = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
        return earth_radius * 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))

    def classify_place(tags: dict) -> str:
        shop = (tags.get("shop") or "").casefold()
        craft = (tags.get("craft") or "").casefold()
        label = " ".join(
            filter(None, (tags.get("name"), tags.get("brand"), tags.get("operator")))
        ).casefold()

        if shop == "tyres" or any(token in label for token in ("vulcaniz", "llantera", "llanta", "tyre", "tire")):
            return "vulcanizadora"
        if shop == "car_parts" or any(
            token in label
            for token in (
                "autozone",
                "auto zone",
                "refaccion",
                "autoparte",
                "auto parte",
                "oreilly",
                "o'reilly",
                "napa auto",
            )
        ):
            return "autopartes"
        if shop == "car_repair" or craft == "car_repair" or any(
            token in label for token in ("taller", "mecán", "mecan", "service auto", "autoservicio")
        ):
            return "taller"
        if shop == "car":
            return "autopartes"
        return "taller"

    category_labels = {
        "taller": "Taller",
        "autopartes": "Autopartes",
        "vulcanizadora": "Vulcanizadora",
    }

    places = []
    for element in data.get("elements", []):
        tags = element.get("tags", {})
        if not (tags.get("name") or tags.get("brand")):
            continue
        place_lat = element.get("lat", element.get("center", {}).get("lat"))
        place_lon = element.get("lon", element.get("center", {}).get("lon"))
        if place_lat is None or place_lon is None:
            continue
        category = classify_place(tags)
        name = tags.get("name") or tags.get("brand") or "Negocio automotriz"
        address = ", ".join(filter(None, (
            tags.get("addr:full"),
            " ".join(filter(None, (tags.get("addr:street"), tags.get("addr:housenumber")))),
            tags.get("addr:suburb"),
            tags.get("addr:city"),
        ))) or f"Ubicación {place_lat:.6f}, {place_lon:.6f}"
        distance = round(distance_meters(float(place_lat), float(place_lon)))
        if distance > NEARBY_RADIUS_METERS:
            continue
        map_query = f"{name}, {address} {place_lat},{place_lon}"
        places.append({
            "id": f"{element['type']}-{element['id']}",
            "name": name,
            "address": address,
            "latitude": float(place_lat),
            "longitude": float(place_lon),
            "distanceMeters": distance,
            "category": category,
            "categoryLabel": category_labels[category],
            "href": "https://www.google.com/maps/search/?api=1&" + urlencode({"query": map_query}),
        })

    # 5 más cercanos de cada categoría (taller, autopartes, vulcanizadora)
    selected = []
    seen_ids = set()
    for category in ("taller", "autopartes", "vulcanizadora"):
        group = [place for place in places if place["category"] == category]
        group.sort(key=lambda place: place["distanceMeters"])
        for place in group[:NEARBY_PER_CATEGORY]:
            if place["id"] in seen_ids:
                continue
            seen_ids.add(place["id"])
            selected.append(place)

    selected.sort(key=lambda place: (place["category"], place["distanceMeters"]))
    result = {
        "places": selected,
        "source": source,
        "counts": {
            "taller": sum(1 for place in selected if place["category"] == "taller"),
            "autopartes": sum(1 for place in selected if place["category"] == "autopartes"),
            "vulcanizadora": sum(1 for place in selected if place["category"] == "vulcanizadora"),
        },
    }
    nearby_cache[cache_key] = {"expires_at": time.time() + 300, "result": result}
    return result


@app.post("/reverse-location")
def reverse_location(request: ReverseLocationRequest):
    reverse_url = "https://nominatim.openstreetmap.org/reverse?" + urlencode({
        "lat": request.latitude,
        "lon": request.longitude,
        "format": "jsonv2",
    })
    reverse_request = Request(reverse_url, headers={"User-Agent": "AutoGuia/1.0 (location display)"})
    try:
        with urlopen(reverse_request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as error:
        raise HTTPException(status_code=502, detail="No se pudo obtener el nombre de la dirección.") from error
    return {"displayName": data.get("display_name", "Ubicación actual")}


    