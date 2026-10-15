import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Ambient from './components/Ambient'
import Brand from './components/Brand'
import Compose from './components/Compose'
import Guardados, { GuardadosDrawer, GuardadosTrigger } from './components/Guardados'
import HistoryDrawer from './components/HistoryDrawer'
import Onboarding from './components/Onboarding'
import RecipeDetail from './components/RecipeDetail'
import { Results } from './components/Results'
import StepRail from './components/StepRail'
import StepStage, { stepDirection } from './components/StepStage'
import SplashScreen from './components/SplashScreen'
import Toast from './components/Toast'
import { useAmbientMotion } from './hooks/useMotion'
import { generateRecipes, subtractIngredients } from './utils/recipes'
import {
  getHistory,
  getIngredients,
  getTools,
  pushHistory,
  setIngredients,
  setTools,
} from './utils/storage'

export default function App() {
  return (
    <Guardados>
      {(guardados) => <AppContent guardados={guardados} />}
    </Guardados>
  )
}

function AppContent({ guardados }) {
  const rootRef = useRef(null)
  useAmbientMotion(rootRef)

  const [showSplash, setShowSplash] = useState(true)
  const [tools, setToolsState] = useState(() => getTools())
  const [ingredients, setIngredientsState] = useState(() => getIngredients())
  const [step, setStepState] = useState(() => (getTools()?.length ? 'compose' : 'onboarding'))
  const [stepDir, setStepDir] = useState(1)
  const [recipes, setRecipes] = useState([])
  const [lastQuery, setLastQuery] = useState(null)
  const [history, setHistory] = useState(() => getHistory())
  const [active, setActive] = useState(null)
  const [usedId, setUsedId] = useState(null)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [lockedIds, setLockedIds] = useState(() => new Set())
  const [generating, setGenerating] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [toast, setToast] = useState('')
  const stepRef = useRef(step)
  const { recipes: saved, open: savedOpen, setOpen: setSavedOpen, toggleSaved } = guardados
  const savedIds = useMemo(() => {
    const ids = new Set(lockedIds)
    saved.forEach((recipe) => ids.add(recipe.id))
    return ids
  }, [lockedIds, saved])

  const goToStep = useCallback((next) => {
    setStepDir(stepDirection(stepRef.current, next))
    stepRef.current = next
    setStepState(next)
  }, [])
  const finishSplash = useCallback(() => setShowSplash(false), [])

  useEffect(() => {
    document.title = '10go hambre'
  }, [])

  const clearToast = useCallback(() => setToast(''), [])

  function persistIngredients(next) {
    setIngredientsState(next)
    setIngredients(next)
  }

  function handleOnboarding(chosenTools) {
    setTools(chosenTools)
    setToolsState(chosenTools)
    setToast('Herramientas guardadas en este dispositivo')
    setHistory(
      pushHistory({
        id: `h-${Date.now()}`,
        at: Date.now(),
        label: 'Onboarding de herramientas',
      }),
    )
  }

  function handleGenerate({ types, note }) {
    setGenerating(true)
    window.setTimeout(() => {
      const batch = generateRecipes({
        ingredients,
        types,
        tools: tools || [],
      })
      setRecipes(batch)
      setLastQuery({ types, note })
      setUsedId(null)
      setLockedIds(new Set())
      goToStep('results')
      setGenerating(false)
      setToast('Listo: 4 propuestas nuevas')
      setHistory(
        pushHistory({
          id: `h-${Date.now()}`,
          at: Date.now(),
          label: `Generó 4 recetas · ${types.join(', ')}`,
        }),
      )
    }, 450)
  }

  function handleRegenerate() {
    if (!lastQuery) return
    const protectedRecipes = recipes.filter((r) => lockedIds.has(r.id))
    const need = 4 - protectedRecipes.length
    if (need <= 0) {
      setToast('Todas están guardadas: quita alguna para regenerar')
      return
    }

    setRegenerating(true)
    window.setTimeout(() => {
      const fresh = generateRecipes({
        ingredients,
        types: lastQuery.types,
        tools: tools || [],
      }).slice(0, need)

      setRecipes([...protectedRecipes, ...fresh].slice(0, 4))
      setRegenerating(false)
      setToast(
        protectedRecipes.length
          ? `Regeneradas ${need}. ${protectedRecipes.length} guardada(s) intactas`
          : 'Nuevas 4 ideas listas',
      )
      setHistory(
        pushHistory({
          id: `h-${Date.now()}`,
          at: Date.now(),
          label: 'Regeneró ideas (guardadas intactas)',
        }),
      )
    }, 400)
  }

  function handleSave(recipe) {
    const added = toggleSaved(recipe)
    if (!added) {
      setLockedIds((prev) => {
        const next = new Set(prev)
        next.delete(recipe.id)
        return next
      })
      setToast('Receta quitada de guardadas')
      return
    }
    setLockedIds((prev) => new Set(prev).add(recipe.id))
    setToast('Guardada: no se borrará al regenerar')
    setHistory(
      pushHistory({
        id: `h-${Date.now()}`,
        at: Date.now(),
        label: 'Guardó receta',
        recipe,
      }),
    )
  }

  function handleUse(recipe) {
    const nextPantry = subtractIngredients(ingredients, recipe.ingredients)
    persistIngredients(nextPantry)
    setUsedId(recipe.id)
    setToast(`Usaste “${recipe.title}”. Inventario actualizado.`)
    setHistory(
      pushHistory({
        id: `h-${Date.now()}`,
        at: Date.now(),
        label: 'Usó receta · inventario actualizado',
        recipe,
      }),
    )
    setActive(null)
  }

  return (
    <div className="app" ref={rootRef}>
      <Ambient>
        
        <div className="shell">
          <div >    <GuardadosTrigger
                  count={saved.length}
                  open={savedOpen}
                  onOpen={() => setSavedOpen(true)}
                />
                </div>
          <header className="topbar">
                
            <Brand small />
            {step !== 'onboarding' && (
              <div className="topbar__tools">
                <p className="topbar__note">Sin cuentas · todo queda aquí</p>
                
              </div>
            )}
          </header>

          <StepRail current={step} />

          <div className="step-viewport">
            <StepStage step={step} direction={stepDir} key={step}>
              {step === 'onboarding' && (
                <Onboarding onComplete={handleOnboarding} initialTools={tools || []} />
              )}

              {step === 'compose' && (
                <Compose
                  tools={tools || []}
                  ingredients={ingredients}
                  onIngredientsChange={persistIngredients}
                  onGenerate={handleGenerate}
                  onEditTools={() => goToStep('onboarding')}
                  historyCount={history.length}
                  onOpenHistory={() => setHistoryOpen(true)}
                  generating={generating}
                />
              )}

              {step === 'results' && (
                <Results
                  recipes={recipes}
                  savedIds={savedIds}
                  usedId={usedId}
                  onOpen={setActive}
                  onSave={handleSave}
                  onUse={handleUse}
                  onRegenerate={handleRegenerate}
                  onBack={() => goToStep('compose')}
                  onDone={() => {
                    setUsedId(null)
                    setRecipes([])
                    setLastQuery(null)
                    setLockedIds(new Set())
                    goToStep('compose')
                    setToast('Listo. Inventario actualizado para la próxima.')
                  }}
                  regenerating={regenerating}
                />
              )}
            </StepStage>
          </div>
        </div>
      </Ambient>

      <RecipeDetail
        recipe={active}
        onClose={() => setActive(null)}
        onSave={handleSave}
        onUse={handleUse}
        saved={active ? savedIds.has(active.id) : false}
        used={active ? usedId === active.id : false}
      />

      <HistoryDrawer
        open={historyOpen}
        items={history}
        onClose={() => setHistoryOpen(false)}
        onOpenRecipe={(recipe) => {
          if (recipe) setActive(recipe)
          setHistoryOpen(false)
        }}
      />

      <GuardadosDrawer
        open={savedOpen}
        recipes={saved}
        savedIds={savedIds}
        usedId={usedId}
        onClose={() => setSavedOpen(false)}
        onOpenRecipe={(recipe) => {
          setActive(recipe)
        }}
        onSave={handleSave}
        onUse={handleUse}
      />
 
      <Toast message={toast} onDone={clearToast} raised={step === 'results'} />
      {showSplash && <SplashScreen onFinish={finishSplash} />}
    </div>
  )
}
