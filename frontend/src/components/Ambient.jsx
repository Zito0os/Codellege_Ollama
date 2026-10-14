export default function Ambient({ children }) {
  return (
    <div className="ambient">
      <div className="ambient__shape ambient__shape--a" data-float aria-hidden="true" />
      <div className="ambient__shape ambient__shape--b" data-float aria-hidden="true" />
      <div className="ambient__shape ambient__shape--c" data-float aria-hidden="true" />
      <div className="ambient__shape ambient__shape--d" data-float aria-hidden="true" />
      <div className="ambient__shape ambient__shape--e" data-float aria-hidden="true" />
      <div className="ambient__shape ambient__shape--f" data-float aria-hidden="true" />
      <div className="ambient__shape ambient__shape--g" data-float aria-hidden="true" />
      <div className="ambient__shape ambient__shape--h" data-float aria-hidden="true" />
      <div className="ambient__shape ambient__shape--i" data-float aria-hidden="true" />

      <div className="ambient__grain" aria-hidden="true" />
      <div className="ambient__content">{children}</div>
    </div>
  )
}
