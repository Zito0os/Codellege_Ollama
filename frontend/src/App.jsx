import { useEffect, useRef, useState } from 'react'
import './App.css'

const DEFAULT_LOCATION = 'Monterrey, N.L.'

const modes = [
  { id: 'vehicle', number: '01', title: '¿Cuál es tu carro?', description: 'Identifícalo y conoce sus datos clave.', heading: 'Empecemos por conocer tu auto', prompt: 'Dime marca, modelo y año para identificarlo mejor.', button: 'Identificar auto' },
  { id: 'repair', number: '02', title: 'Reparar mi carro', description: 'Entiende una falla y qué revisar.', heading: 'Cuéntame qué le sucede', prompt: 'Describe el ruido, testigo o síntoma que notas.', button: 'Consultar reparación' },
  { id: 'install', number: '03', title: 'Cómo instalar algo', description: 'Sigue pasos para una instalación.', heading: '¿Qué quieres instalar?', prompt: 'Indica la pieza o accesorio y te guío paso a paso.', button: 'Ver guía de instalación' },
  { id: 'parts', number: '04', title: 'Piezas compatibles', description: 'Busca piezas para tu modelo de auto.', heading: 'Encuentra piezas para tu auto', prompt: 'Dime qué pieza buscas y los datos de tu vehículo.', button: 'Buscar compatibilidad' },
]

function buildNearbyMapUrl(mode, location, place, coordinates) {
  if (place) {
    return `https://maps.google.com/maps?q=${place.latitude},${place.longitude}&z=17&output=embed`
  }

  const placeType = mode === 'repair' ? 'talleres mecánicos' : 'refaccionarias'
  if (coordinates) {
    const query = `${placeType} cerca de ${coordinates.latitude},${coordinates.longitude}`
    return `https://maps.google.com/maps?q=${encodeURIComponent(query)}&z=13&output=embed`
  }

  const query = `${placeType} cerca de ${location}`
  return `https://maps.google.com/maps?q=${encodeURIComponent(query)}&z=13&output=embed`
}

function formatAnswerText(text) {
  if (!text) return ''

  return text
    .replace(/\r\n/g, '\n')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/\n\s*\*\s*/g, '\n- ')
    .replace(/^\s*\*\s*/gm, '- ')
    .replace(/\n\s*-\s*/g, '\n- ')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function App() {
  const [activeMode, setActiveMode] = useState('vehicle')
  const [vehicle, setVehicle] = useState({ make: '', model: '', year: '' })
  const [details, setDetails] = useState('')
  const [location, setLocation] = useState('')
  const [geoCoordinates, setGeoCoordinates] = useState(null)
  const [detectedAddress, setDetectedAddress] = useState('')
  const [isLocating, setIsLocating] = useState(false)
  const [locationError, setLocationError] = useState('')
  const [lastQuestion, setLastQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [resultLocation, setResultLocation] = useState('')
  const [resultCoordinates, setResultCoordinates] = useState(null)
  const [resultMode, setResultMode] = useState('')
  const [nearbyPlaces, setNearbyPlaces] = useState([])
  const [selectedNearbyPlace, setSelectedNearbyPlace] = useState(null)
  const [nearbyRetryKey, setNearbyRetryKey] = useState(0)
  const [isLoadingNearby, setIsLoadingNearby] = useState(false)
  const [nearbyPlacesError, setNearbyPlacesError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [showResult, setShowResult] = useState(false)
  const [resultNavigation, setResultNavigation] = useState(0)
  const resultRef = useRef(null)

  const selectedMode = modes.find((mode) => mode.id === activeMode)
  const vehicleDescription = [vehicle.year, vehicle.make, vehicle.model].filter(Boolean).join(' ')
  const needsNearbyMap = activeMode === 'repair' || activeMode === 'install'
  const showNearbyMap = Boolean(answer && (resultMode === 'repair' || resultMode === 'install') && resultLocation)
  const canSubmit = activeMode === 'vehicle'
    ? Boolean(vehicle.make.trim() || vehicle.model.trim() || vehicle.year.trim())
    : activeMode === 'parts'
      ? Boolean(details.trim() && vehicle.make.trim() && vehicle.model.trim() && vehicle.year.trim())
      : Boolean(details.trim())

  useEffect(() => {
    if (resultNavigation > 0) {
      resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [resultNavigation])

  useEffect(() => {
    if (!resultMode || !resultLocation) return undefined

    const controller = new AbortController()

    fetch('http://localhost:8000/nearby-places', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: resultMode, location: resultLocation, ...(resultCoordinates || {}) }),
      signal: controller.signal,
    })
      .then(async (response) => {
        const data = await response.json()
        if (!response.ok) throw new Error(data.detail || 'No se pudieron cargar los establecimientos.')
        setNearbyPlaces(data.places || [])
        setSelectedNearbyPlace(null)
      })
      .catch((requestError) => {
        if (requestError.name !== 'AbortError') setNearbyPlacesError(requestError.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoadingNearby(false)
      })

    return () => controller.abort()
  }, [resultMode, resultLocation, resultCoordinates, nearbyRetryKey])

  function useCurrentLocation() {
    if (!navigator.geolocation) {
      setLocationError('Este navegador no permite acceder a la ubicación.')
      return
    }

    setIsLocating(true)
    setLocationError('')
    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        const coordinates = { latitude: coords.latitude, longitude: coords.longitude }
        setGeoCoordinates(coordinates)
        setDetectedAddress('Buscando nombre de la dirección…')
        setLocation('Ubicación actual')
        setIsLocating(false)
        try {
          const response = await fetch('http://localhost:8000/reverse-location', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(coordinates),
          })
          const data = await response.json()
          if (!response.ok) throw new Error(data.detail || 'No se pudo identificar la dirección.')
          setDetectedAddress(data.displayName)
        } catch {
          setDetectedAddress(`${coordinates.latitude.toFixed(5)}, ${coordinates.longitude.toFixed(5)}`)
        }
      },
      (geolocationError) => {
        const message = geolocationError.code === 1
          ? 'No se concedió el permiso. Permite la ubicación en el navegador para continuar.'
          : geolocationError.code === 2
            ? 'No se pudo determinar tu ubicación. Revisa el servicio de ubicación del dispositivo.'
            : 'La solicitud de ubicación tardó demasiado. Intenta de nuevo.'
        setLocationError(message)
        setIsLocating(false)
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 30000 },
    )
  }

  function updateVehicle(event) {
    setVehicle({ ...vehicle, [event.target.name]: event.target.value })
  }

  function selectMode(mode) {
    setActiveMode(mode)
    setDetails('')
    setLastQuestion('')
    setAnswer('')
    setResultLocation('')
    setResultCoordinates(null)
    setResultMode('')
    setIsLoadingNearby(false)
    setError('')
    setShowResult(false)
  }

  async function askAssistant(event) {
    event.preventDefault()
    if (!canSubmit || isLoading) return

    const context = vehicleDescription ? ` Vehículo: ${vehicleDescription}.` : ''
    const resolvedLocation = location.trim() || DEFAULT_LOCATION
    const submittedCoordinates = geoCoordinates
    const readableLocation = detectedAddress && !detectedAddress.startsWith('Buscando') ? detectedAddress : 'Ubicación actual'
    let question
    if (activeMode === 'vehicle') {
      question = `Ayúdame a identificar este vehículo y dame información general útil para conocerlo. Si faltan datos, pregúntamelos. Vehículo: ${vehicleDescription}.`
    } else if (activeMode === 'repair') {
      question = `Ayúdame a entender y diagnosticar esta falla. Explica qué revisar primero, posibles causas y cuándo debo detenerme y acudir a un mecánico.${context} Síntoma: ${details.trim()}`
    } else if (activeMode === 'install') {
      question = `Explícame cómo instalar esto en un vehículo con pasos claros, herramientas necesarias y advertencias de seguridad. Si la instalación puede ser peligrosa, indícalo y recomienda un profesional.${context} Quiero instalar: ${details.trim()}`
    } else {
      question = `Ayúdame a identificar qué piezas podrían ser compatibles con mi vehículo para esta necesidad: ${details.trim()}. Vehículo: ${vehicleDescription || 'todavía no especificado'}. Solicita marca, modelo, año, versión, motor o VIN si son necesarios para dar una respuesta confiable. No inventes números de parte ni asegures compatibilidad exacta si no puedes verificarla; explica qué datos confirmar en un catálogo o con un proveedor antes de comprar.`
    }

    setIsLoading(true)
    setError('')
    setAnswer('')
    setResultLocation('')
    setResultCoordinates(null)
    setResultMode('')
    if (activeMode === 'repair' || activeMode === 'install') {
      setNearbyPlaces([])
      setSelectedNearbyPlace(null)
      setNearbyPlacesError('')
      setIsLoadingNearby(true)
    }
    setLastQuestion(activeMode === 'vehicle' ? vehicleDescription : details.trim())
    setShowResult(true)
    setResultNavigation((current) => current + 1)
    try {
      const response = await fetch('http://localhost:8000/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: question }),
      })
      if (!response.ok) throw new Error('No se pudo obtener una respuesta.')
      const data = await response.json()
      setAnswer(formatAnswerText(data.answer || ''))
      if (activeMode === 'repair' || activeMode === 'install') {
        setResultLocation(submittedCoordinates ? readableLocation : resolvedLocation)
        setResultCoordinates(submittedCoordinates)
        setResultMode(activeMode)
      }
    } catch {
      setIsLoadingNearby(false)
      setError('No pudimos conectar con la IA. Comprueba que FastAPI y Ollama estén en ejecución.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="assistant-app">
      <header className="ai-header">
        <a className="ai-brand" href="#inicio" aria-label="AutoGuía, inicio">
          <span className="ai-brand-mark" aria-hidden="true"><svg viewBox="0 0 32 32"><path d="M5 17.5h22l-2.2-5.1a3 3 0 0 0-2.7-1.8H9.9a3 3 0 0 0-2.7 1.8L5 17.5Zm1.2 0v6.2h3.1v-2h13.4v2h3.1v-6.2M8.5 17.5v2.1m15-2.1v2.1" /><circle cx="10" cy="16" r=".8" /><circle cx="22" cy="16" r=".8" /></svg></span>
          <span>auto<span>guía</span></span>
        </a>
        <div className="ai-header-status"><span /> ASISTENTE AUTOMOTRIZ <i /></div>
      </header>

      <main className="ai-main" id="inicio">
        <section className="ai-intro">
          <p className="ai-eyebrow">TU COPILOTO DE TALLER <span>·</span> SIEMPRE A MANO</p>
          <h1>Entiende tu auto.<br /><em>Resuelve lo que sigue.</em></h1>
          <p className="ai-subtitle">Elige qué necesitas y lo vemos juntos, paso a paso.</p>
          <div className="garage-photo" role="img" aria-label="Detalle de un mecánico revisando un automóvil"><span>EN EL TALLER</span></div>
        </section>

        <section className="mode-section" aria-label="Elige cómo quieres que te ayude">
          <div className="mode-section-label"><span>¿QUÉ NECESITAS HOY?</span><span>01 — 04</span></div>
          <div className="mode-grid">
            {modes.map((mode) => (
              <button key={mode.id} className={`mode-card${activeMode === mode.id ? ' selected' : ''}`} onClick={() => selectMode(mode.id)} aria-pressed={activeMode === mode.id}>
                <span className="mode-number">{mode.number}</span>
                <span className="mode-title">{mode.title}</span>
                <span className="mode-description">{mode.description}</span>
                <span className="mode-arrow" aria-hidden="true">↗</span>
              </button>
            ))}
          </div>
        </section>

        <section className="chat-workspace" aria-label="Asistente de auto">
          <div className="chat-topbar">
            <div className="chat-identity"><span className="chat-avatar"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M5 17.5h22l-2.2-5.1a3 3 0 0 0-2.7-1.8H9.9a3 3 0 0 0-2.7 1.8L5 17.5Zm1.2 0v6.2h3.1v-2h13.4v2h3.1v-6.2M8.5 17.5v2.1m15-2.1v2.1" /></svg></span><span><strong>AutoGuía IA</strong><small>Asistente para tu vehículo</small></span></div>
            <span className="chat-online"><i /> EN LÍNEA</span>
          </div>

          <div className="chat-content">
            <div className="assistant-greeting">
              <span className="greeting-label">{selectedMode.number} / {selectedMode.title.toUpperCase()}</span>
              <h2>{selectedMode.heading}</h2>
              <p>{selectedMode.prompt}</p>
            </div>

            <form className="ai-form" onSubmit={askAssistant}>
              {activeMode === 'vehicle' ? (
                <div className="vehicle-fields">
                  <label>Marca<input name="make" value={vehicle.make} onChange={updateVehicle} placeholder="Ej. Toyota" autoComplete="off" /></label>
                  <label>Modelo<input name="model" value={vehicle.model} onChange={updateVehicle} placeholder="Ej. Corolla" autoComplete="off" /></label>
                  <label>Año<input name="year" value={vehicle.year} onChange={updateVehicle} placeholder="Ej. 2019" inputMode="numeric" /></label>
                </div>
              ) : (
                <>
                  <div className="vehicle-context">
                    <span className="context-label">DATOS DE TU AUTO <small>{activeMode === 'parts' ? 'NECESARIOS PARA COMPATIBILIDAD' : 'OPCIONAL, PERO ÚTIL'}</small></span>
                    <div className="vehicle-fields context-fields">
                      <label>Marca<input name="make" value={vehicle.make} onChange={updateVehicle} placeholder="Toyota" autoComplete="off" /></label>
                      <label>Modelo<input name="model" value={vehicle.model} onChange={updateVehicle} placeholder="Corolla" autoComplete="off" /></label>
                      <label>Año<input name="year" value={vehicle.year} onChange={updateVehicle} placeholder="2019" inputMode="numeric" /></label>
                    </div>
                  </div>
                  <label className="details-label" htmlFor="vehicle-details">{activeMode === 'repair' ? '¿Qué está pasando?' : activeMode === 'install' ? '¿Qué quieres instalar?' : '¿Qué pieza necesitas?'}</label>
                  <textarea id="vehicle-details" value={details} onChange={(event) => setDetails(event.target.value)} placeholder={activeMode === 'repair' ? 'Ej. Al frenar, el auto vibra y se escucha un rechinido...' : activeMode === 'install' ? 'Ej. Quiero instalar una cámara de reversa...' : 'Ej. Busco un alternador o pastillas de freno...'} rows="3" />
                  {needsNearbyMap && (
                    <div className="location-entry">
                      <label className="details-label location-label" htmlFor="user-location">
                        Ubicación <small>OPCIONAL · PUEDES ESCRIBIRLA O COMPARTIR TU UBICACIÓN</small>
                      </label>
                      <div className="location-input-row">
                      <input
                        id="user-location"
                        type="text"
                        value={location}
                        onChange={(event) => {
                          setLocation(event.target.value)
                          setGeoCoordinates(null)
                          setDetectedAddress('')
                          setLocationError('')
                        }}
                        placeholder="Ej. San Pedro Garza García, N.L."
                        autoComplete="address-level2"
                      />
                        <button className="location-button" type="button" onClick={useCurrentLocation} disabled={isLocating}>
                          {isLocating ? 'Localizando…' : geoCoordinates ? 'Actualizar ubicación' : 'Usar mi ubicación'}
                        </button>
                      </div>
                      {geoCoordinates && <small className="location-success" role="status">Usaremos tu ubicación actual para buscar lugares cercanos.</small>}
                      {geoCoordinates && detectedAddress && <small className="location-address" role="status">Ubicación detectada: {detectedAddress}</small>}
                      {locationError && <small className="location-error" role="alert">{locationError}</small>}
                    </div>
                  )}
                </>
              )}
              <div className="form-bottom"><span className="privacy-note"><span aria-hidden="true">⌑</span> Tu información solo se usa para responderte.</span><button type="submit" disabled={!canSubmit || isLoading}>{isLoading ? 'Pensando…' : selectedMode.button}<span aria-hidden="true">↗</span></button></div>
            </form>
            <p className="safety-note">La orientación de la IA es informativa. Para reparaciones de riesgo, consulta a un profesional.</p>
          </div>
        </section>

        {showResult && (
          <section className="result-section" id="resultado" ref={resultRef} aria-labelledby="result-title" aria-live="polite">
            <div className="result-heading">
              <p className="ai-eyebrow">RESULTADO DE TU CONSULTA <span>·</span> {selectedMode.title.toUpperCase()}</p>
              <h2 id="result-title">{activeMode === 'vehicle' ? 'Información de tu auto' : activeMode === 'repair' ? 'Orientación para la reparación' : activeMode === 'install' ? 'Guía de instalación' : 'Piezas que podrían ser compatibles'}</h2>
              <div className="result-question"><span>TU CONSULTA</span><p>{lastQuestion}{vehicleDescription && activeMode !== 'vehicle' ? ` · ${vehicleDescription}` : ''}</p></div>
            </div>
            <div className="result-content">
              {isLoading ? <div className="result-loading" role="status"><span className="loading-indicator" /><div><strong>Preparando tu respuesta</strong><p>La IA está revisando la información y organizando los pasos para ti.</p></div></div> : null}
              {error && <p className="result-error" role="alert">{error}</p>}
              {answer && <><div className="result-answer-label"><span>RESPUESTA DE AUTOGUÍA</span></div><div className="result-answer">{answer}</div></>}
              {showNearbyMap && (
                <div className="nearby-places">
                  <div className="nearby-places-label">
                    <span>LUGARES CERCANOS</span>
                    <small>
                      {resultMode === 'repair' ? 'Talleres mecánicos' : 'Refaccionarias'} cerca de {resultLocation}
                    </small>
                  </div>
                  <div className="nearby-map">
                    <iframe
                      title={selectedNearbyPlace ? `Mapa de ${selectedNearbyPlace.name}` : resultMode === 'repair' ? `Talleres mecánicos cerca de ${resultLocation}` : `Refaccionarias cerca de ${resultLocation}`}
                      src={buildNearbyMapUrl(resultMode, resultLocation, selectedNearbyPlace, resultCoordinates)}
                      loading="lazy"
                      referrerPolicy="no-referrer-when-downgrade"
                      allowFullScreen
                    />
                  </div>
                  {isLoadingNearby && <p className="nearby-status" role="status">Buscando establecimientos reales…</p>}
                  {nearbyPlacesError && (
                    <div className="nearby-error" role="alert">
                      <p>{nearbyPlacesError}</p>
                      <button type="button" onClick={() => {
                        setNearbyPlacesError('')
                        setNearbyPlaces([])
                        setIsLoadingNearby(true)
                        setNearbyRetryKey((current) => current + 1)
                      }}>Reintentar búsqueda</button>
                    </div>
                  )}
                  {!isLoadingNearby && !nearbyPlacesError && nearbyPlaces.length === 0 && <p className="nearby-status">No encontramos establecimientos automotrices registrados a menos de 5 km.</p>}
                  {!isLoadingNearby && !nearbyPlacesError && nearbyPlaces.length > 0 && nearbyPlaces.length < 5 && <p className="nearby-status">Encontramos {nearbyPlaces.length} establecimientos automotrices registrados a menos de 5 km.</p>}
                  <ul className="nearby-list">
                    {nearbyPlaces.slice(0, 5).map((place, index) => (
                      <li key={place.id} className={selectedNearbyPlace?.id === place.id ? 'selected' : ''}>
                        <span className="nearby-order">{String(index + 1).padStart(2, '0')}</span>
                        <div className="nearby-place-info">
                          <strong>{place.name}</strong>
                          <small>{place.address} · {place.distanceMeters < 1000 ? `${place.distanceMeters} m` : `${(place.distanceMeters / 1000).toFixed(1)} km`}</small>
                        </div>
                        <button
                          className="nearby-select"
                          type="button"
                          aria-pressed={selectedNearbyPlace?.id === place.id}
                          onClick={() => setSelectedNearbyPlace(place)}
                        >
                          {selectedNearbyPlace?.id === place.id ? 'Seleccionado' : 'Ver en mapa'}
                        </button>
                        <a className="nearby-link" href={place.href} target="_blank" rel="noreferrer">
                          Abrir en Google Maps <span aria-hidden="true">↗</span>
                        </a>
                      </li>
                    ))}
                  </ul>
                  <p className="nearby-attribution">Lugares y distancias aproximadas: <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a>.</p>
                </div>
              )}
              <button className="back-to-form" type="button" onClick={() => document.querySelector('.mode-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' })}>Volver a la consulta <span aria-hidden="true">↑</span></button>
            </div>
          </section>
        )}

        <footer className="ai-footer"><span>AUTOGUÍA <i>·</i> CONDUCE CON CONFIANZA</span><span>HECHO PARA AYUDAR, NO PARA SUSTITUIR A TU MECÁNICO.</span></footer>
      </main>
    </div>
  )
}

export default App
