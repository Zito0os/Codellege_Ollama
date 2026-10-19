import logo from '../assets/logo.png'

export default function Brand({ small = false, onClick }) {
  const className = `brand ${small ? 'brand--small' : ''}`
  const content = (
    <>
      <img
        className="brand__logo"
        src={logo}
        alt="10go Hambre"
        width={small ? 180 : 280}
        height={small ? 108 : 168}
      />
      {!small && <p className="brand__tag">Qué comer hoy, con lo que ya tienes</p>}
    </>
  )

  if (onClick) {
    return (
      <button
        type="button"
        className={`${className} brand--interactive`}
        onClick={onClick}
        aria-label="Volver al inicio"
      >
        {content}
      </button>
    )
  }

  return (
    <div className={className}>{content}</div>
  )
}
