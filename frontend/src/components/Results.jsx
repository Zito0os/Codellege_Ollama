import { useReveal } from '../hooks/useMotion'

export default function RecipeCard({ recipe, saved, used, onOpen, onSave, onUse }) {
  return (
    <article className={`recipe-card ${used ? 'recipe-card--used' : ''} ${saved ? 'recipe-card--saved' : ''}`}>
      <button type="button" className="recipe-card__hit" onClick={() => onOpen(recipe)}>
        <div className="recipe-card__media">
          <img src={recipe.image} alt="" loading="lazy" width="480" height="280" />
          <span className="recipe-card__cuisine">{recipe.cuisine}</span>
        </div>
        <div className="recipe-card__body">
          <h3>{recipe.title}</h3>
          <div className="meta">
            <span>{recipe.time}</span>
            <span>{recipe.difficulty}</span>
          </div>
        </div>
      </button>
      <div className="recipe-card__bar">
        <button type="button" className="btn btn--soft" onClick={() => onSave(recipe)}>
          {saved ? 'Guardada' : 'Guardar'}
        </button>
        <button type="button" className="btn btn--soft btn--solid" onClick={() => onUse(recipe)} disabled={used}>
          {used ? 'Usada' : 'Usar'}
        </button>
      </div>
    </article>
  )
}

export function Results({
  recipes,
  savedIds,
  usedId,
  onOpen,
  onSave,
  onUse,
  onRegenerate,
  onBack,
  onDone,
  regenerating,
}) {
  const ref = useReveal([recipes.map((r) => r.id).join('|')])
  const canFinish = Boolean(usedId)

  return (
    <section className="results results--fit" ref={ref}>
      <header className="results__head">
        <h1 className="display display--md">Ideas</h1>
        <div className="compose__actions">
          <button type="button" className="btn btn--soft" onClick={onBack}>
            Volver
          </button>
          <button
            type="button"
            className="btn btn--soft btn--solid"
            onClick={onRegenerate}
            disabled={regenerating}
            aria-busy={regenerating}
          >
            {regenerating ? '…' : 'Regenerar'}
          </button>
        </div>
      </header>

      <div className="results__grid results__grid--compact">
        {recipes.map((recipe) => (
          <div key={recipe.id} className="grid-item">
            <RecipeCard
              recipe={recipe}
              saved={savedIds.has(recipe.id)}
              used={usedId === recipe.id}
              onOpen={onOpen}
              onSave={onSave}
              onUse={onUse}
            />
          </div>
        ))}
      </div>

      <div className="results__footer">
        <div className="compose__cta-blur" aria-hidden="true" />
        <div className="compose__cta-inner compose__cta-inner--compact">
          <button
            type="button"
            className="btn btn--primary btn--generate"
            onClick={onDone}
            disabled={!canFinish}
            title={canFinish ? 'Terminar y volver al refrigerador' : 'Primero usa una receta'}
          >
            Listo
          </button>
          {!canFinish && (
            <p className="results__hint-mini">Activa Listo cuando uses una receta</p>
          )}
        </div>
      </div>
    </section>
  )
}
