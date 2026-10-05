export default function Ambient({ children }) {
  return (
    <div className="ambient">
      <div className="ambient__shape ambient__shape--a" data-float aria-hidden="true" />
      <div className="ambient__shape ambient__shape--b" data-float aria-hidden="true" />
      <div className="ambient__shape ambient__shape--c" data-float aria-hidden="true" />
      <div className="ambient__grain" aria-hidden="true" />
      <div className="ambient__content">{children}</div>
    </div>
  )
}
