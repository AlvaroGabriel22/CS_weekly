/**
 * Guia de primeiro acesso — tour com SPOTLIGHT animado (sem dependências).
 *
 * Como funciona:
 * - O fundo escurece e um recorte arredondado "viaja" suavemente até o
 *   elemento em foco (transição CSS em top/left/width/height do recorte,
 *   desenhado com um box-shadow gigante).
 * - Cada passo aponta para um alvo `[data-tour="..."]`; se o passo pertence a
 *   outra rota, o tour navega e espera o elemento aparecer (com timeout —
 *   passos cujo alvo não existir são pulados, nunca travam o usuário).
 * - PRIMEIRO ACESSO (mandatory): sem botão de fechar/pular; ao concluir,
 *   grava a flag no backend. REPLAY: pode fechar a qualquer momento.
 */
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { createPortal } from 'react-dom'
import { useLocation, useNavigate } from 'react-router-dom'
import { X } from 'lucide-react'
import api from '@/lib/api'
import { useI18n } from '@/i18n'
import { TOUR } from '@/i18n/messages/tour'

import { PREPARES, TOUR_STEPS } from './tourSteps'
import { TourContext, useTour } from './tourContext'

interface Rect {
  top: number
  left: number
  width: number
  height: number
}

const PAD = 8
const FIND_TIMEOUT_MS = 3000

function targetRect(el: Element): Rect {
  const r = el.getBoundingClientRect()
  return {
    top: r.top - PAD,
    left: r.left - PAD,
    width: r.width + PAD * 2,
    height: r.height + PAD * 2,
  }
}

/** Espera o alvo existir e estar visível (rota pode estar carregando). */
function waitForTarget(target: string, timeoutMs: number): Promise<Element | null> {
  return new Promise(resolve => {
    const startedAt = Date.now()
    const tick = () => {
      const el = document.querySelector(`[data-tour="${target}"]`)
      if (el && (el as HTMLElement).offsetParent !== null) return resolve(el)
      if (Date.now() - startedAt > timeoutMs) return resolve(null)
      requestAnimationFrame(tick)
    }
    tick()
  })
}

export function TourProvider({ children }: { children: ReactNode }) {
  const { t } = useI18n()
  const navigate = useNavigate()
  const location = useLocation()
  const [active, setActive] = useState(false)
  const [mandatory, setMandatory] = useState(false)
  const [stepIndex, setStepIndex] = useState(0)
  const [rect, setRect] = useState<Rect | null>(null)
  const [visible, setVisible] = useState(false) // fade do tooltip entre passos
  const targetElRef = useRef<Element | null>(null)
  // O tooltip só aparece quando o alvo PARA de se mover (telas têm animações
  // de entrada — medir uma vez só deixava o spotlight torto no meio delas).
  const visibleRef = useRef(false)
  visibleRef.current = visible

  const step = TOUR_STEPS[stepIndex]

  const start = useCallback((isMandatory: boolean) => {
    setMandatory(isMandatory)
    setStepIndex(0)
    setActive(true)
  }, [])

  const finish = useCallback(
    (completed: boolean) => {
      setActive(false)
      targetElRef.current = null
      if (completed && mandatory) {
        api.post('/users/me/flags/tour-completed').catch(() => {
          /* melhor esforço — se falhar, o guia reaparece no próximo login */
        })
      } else if (completed) {
        api.post('/users/me/flags/tour-completed').catch(() => {})
      }
    },
    [mandatory],
  )

  // Ao mudar de passo: navega se preciso, acha o alvo e entrega ao rastreador.
  useEffect(() => {
    if (!active || !step) return
    let cancelled = false
    setVisible(false)
    // Limpa o alvo anterior JÁ: entre passos o fundo escurece por inteiro em
    // vez de deixar o recorte antigo "fantasma" no canto da tela nova.
    targetElRef.current = null
    setRect(null)

    const run = async () => {
      if (step.route !== location.pathname) {
        navigate(step.route)
        return // o effect roda de novo quando a rota mudar
      }
      if (step.target === null) {
        if (!cancelled) setVisible(true)
        return
      }
      if (step.prepare) PREPARES[step.prepare]()
      const el = await waitForTarget(step.target, FIND_TIMEOUT_MS)
      if (cancelled) return
      if (!el) {
        // alvo indisponível (ex.: tela estreita) — pula o passo, nunca trava
        setStepIndex(i => Math.min(i + 1, TOUR_STEPS.length - 1))
        return
      }
      el.scrollIntoView({ block: 'center', behavior: 'auto' })
      targetElRef.current = el // o rastreador contínuo assume daqui
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [active, step, stepIndex, location.pathname, navigate])

  // Rastreador contínuo: segue o alvo quadro a quadro (animações de entrada,
  // painéis deslizando, resize, scroll). O tooltip aparece quando a posição
  // fica estável por ~250ms — nunca no meio do movimento.
  useEffect(() => {
    if (!active) return
    let raf = 0
    let lastKey = ''
    let stableSince = performance.now()
    const loop = (now: number) => {
      const el = targetElRef.current
      if (el && document.contains(el)) {
        const r = targetRect(el)
        const key = `${Math.round(r.top)},${Math.round(r.left)},${Math.round(r.width)},${Math.round(r.height)}`
        if (key !== lastKey) {
          lastKey = key
          stableSince = now
          setRect(r)
        } else if (!visibleRef.current && now - stableSince > 250) {
          setVisible(true)
        }
      }
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [active])

  const goNext = () => {
    if (stepIndex >= TOUR_STEPS.length - 1) finish(true)
    else setStepIndex(stepIndex + 1)
  }
  const goPrev = () => setStepIndex(Math.max(0, stepIndex - 1))

  const value = useMemo(() => ({ start, active }), [start, active])

  // ── posição do tooltip (abaixo do alvo; acima se não couber) ─────────────
  const tooltipStyle = useMemo(() => {
    const width = Math.min(360, window.innerWidth - 24)
    if (!rect) {
      return {
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width,
      } as React.CSSProperties
    }
    const below = rect.top + rect.height + 14
    const fitsBelow = below + 210 < window.innerHeight
    const top = fitsBelow ? below : Math.max(12, rect.top - 14 - 200)
    const left = Math.min(
      Math.max(12, rect.left + rect.width / 2 - width / 2),
      window.innerWidth - width - 12,
    )
    return { top, left, width } as React.CSSProperties
  }, [rect])

  const isLast = stepIndex === TOUR_STEPS.length - 1

  return (
    <TourContext.Provider value={value}>
      {children}
      {active &&
        createPortal(
          <div className="fixed inset-0 z-[200]" role="dialog" aria-modal="true">
            {/* Camada que bloqueia interação com a página durante o guia */}
            <div className="absolute inset-0" aria-hidden />

            {/* Spotlight: recorte claro + escurecimento ao redor, animado */}
            {rect ? (
              <div
                aria-hidden
                className="absolute rounded-xl transition-all duration-500 ease-in-out"
                style={{
                  top: rect.top,
                  left: rect.left,
                  width: rect.width,
                  height: rect.height,
                  boxShadow: '0 0 0 9999px rgba(3, 7, 25, 0.72)',
                  outline: '2px solid rgba(96, 165, 250, 0.9)',
                  outlineOffset: 2,
                }}
              />
            ) : (
              <div aria-hidden className="absolute inset-0 bg-[rgba(3,7,25,0.78)] transition-opacity duration-500" />
            )}

            {/* Tooltip do passo */}
            <div
              className={`absolute rounded-2xl border border-white/10 bg-white p-5 shadow-elevated transition-opacity duration-300 ${
                visible ? 'opacity-100' : 'opacity-0'
              }`}
              style={tooltipStyle}
            >
              <div className="flex items-start justify-between gap-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-brand">
                  {t(TOUR.stepOf, { n: stepIndex + 1, total: TOUR_STEPS.length })}
                </p>
                {!mandatory && (
                  <button
                    type="button"
                    onClick={() => finish(false)}
                    aria-label={t(TOUR.close)}
                    className="-mr-1 -mt-1 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                  >
                    <X className="h-4 w-4" aria-hidden />
                  </button>
                )}
              </div>
              <h2 className="mt-1 text-lg font-bold text-gray-900">{t(step.title)}</h2>
              <p className="mt-1.5 text-sm leading-relaxed text-gray-600">{t(step.body)}</p>

              {/* Progresso */}
              <div className="mt-4 flex items-center gap-1" aria-hidden>
                {TOUR_STEPS.map((_, i) => (
                  <span
                    key={i}
                    className={`h-1.5 rounded-full transition-all duration-300 ${
                      i === stepIndex ? 'w-5 bg-brand' : 'w-1.5 bg-gray-200'
                    }`}
                  />
                ))}
              </div>

              <div className="mt-4 flex items-center justify-between gap-2">
                <button
                  type="button"
                  onClick={goPrev}
                  disabled={stepIndex === 0}
                  className="rounded-lg px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-0"
                >
                  {t(TOUR.previous)}
                </button>
                <button
                  type="button"
                  onClick={goNext}
                  autoFocus
                  className="rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-700"
                >
                  {isLast ? t(TOUR.finish) : t(TOUR.next)}
                </button>
              </div>
            </div>
          </div>,
          document.body,
        )}
    </TourContext.Provider>
  )
}

/** Dispara o tour automaticamente no PRIMEIRO acesso (flag do backend). */
export function TourAutoStart() {
  const { start, active } = useTour()
  const asked = useRef(false)

  useEffect(() => {
    if (asked.current || active) return
    asked.current = true
    api
      .get('/users/me/flags')
      .then(res => {
        if (!res.data?.tour_completed) start(true)
      })
      .catch(() => {
        /* sem flag = não bloqueia o uso */
      })
  }, [start, active])

  return null
}
