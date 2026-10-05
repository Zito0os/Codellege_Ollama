import logo from '../assets/logo.png'

export default function Brand({ small = false }) {
  return (
    <div className={`brand ${small ? 'brand--small' : ''}`}>
      <img
        className="brand__logo"
        src={logo}
        alt="10go Hambre"
        width={small ? 180 : 280}
        height={small ? 108 : 168}
      />
      {!small && <p className="brand__tag">Qué comer hoy, con lo que ya tienes</p>}
    </div>
  )
}
