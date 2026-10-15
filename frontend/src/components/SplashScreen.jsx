import { useEffect } from 'react'
import logo from '../assets/logo.png'

export default function SplashScreen({ onFinish }) {
  useEffect(() => {
    const timeout = window.setTimeout(onFinish, 1400)
    return () => window.clearTimeout(timeout)
  }, [onFinish])

  return (
    <div className="splash-screen" role="status" aria-label="Cargando 10go hambre">
      <img
        className="splash-screen__logo"
        src={logo}
        alt="10go Hambre"
        width="360"
        height="240"
      />
    </div>
  )
}
