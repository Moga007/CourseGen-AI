import { useState, useEffect } from 'react'

const PHASES = [
    { label: 'Connexion au moteur IA',              target: 8,  duration: 1500  },
    { label: 'Analyse du sujet',                    target: 20, duration: 3000  },
    { label: 'Structuration du plan pédagogique',   target: 38, duration: 6000  },
    { label: 'Rédaction du contenu',                target: 72, duration: 28000 },
    { label: 'Enrichissement et exemples',          target: 88, duration: 15000 },
    { label: 'Finalisation du cours',               target: 96, duration: 10000 },
]

export default function LoadingSpinner({ moteur }) {
    const [progress, setProgress] = useState(0)
    const [phaseIndex, setPhaseIndex] = useState(0)
    const [elapsed, setElapsed] = useState(0)

    useEffect(() => {
        const startTime = Date.now()

        const timerInterval = setInterval(() => {
            setElapsed(Math.floor((Date.now() - startTime) / 1000))
        }, 1000)

        let currentProgress = 0
        let currentPhase = 0

        const progressInterval = setInterval(() => {
            if (currentPhase >= PHASES.length) return

            const phase = PHASES[currentPhase]
            const prevTarget = currentPhase > 0 ? PHASES[currentPhase - 1].target : 0
            const increment = (phase.target - prevTarget) / (phase.duration / 100)

            currentProgress = Math.min(currentProgress + increment, phase.target)
            setProgress(Math.round(currentProgress))

            if (currentProgress >= phase.target) {
                currentPhase++
                setPhaseIndex(Math.min(currentPhase, PHASES.length - 1))
            }
        }, 100)

        return () => {
            clearInterval(timerInterval)
            clearInterval(progressInterval)
        }
    }, [])

    const activePhase = PHASES[Math.min(phaseIndex, PHASES.length - 1)]

    return (
        <div style={{ padding: '32px 24px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '28px' }}>

            {/* Titre + moteur + chrono */}
            <div style={{ textAlign: 'center' }}>
                <p className="loading-text font-medium" style={{ fontSize: '15px', marginBottom: '6px' }}>
                    {activePhase.label}<span className="loading-dots"></span>
                </p>
                <p style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                    {moteur ? `${moteur} · ` : ''}{elapsed}s écoulées
                </p>
            </div>

            {/* Barre de progression */}
            <div style={{ width: '100%', maxWidth: '420px' }}>
                <div style={{
                    background: 'var(--border-subtle)',
                    borderRadius: '999px',
                    height: '6px',
                    overflow: 'hidden',
                }}>
                    <div style={{
                        width: `${progress}%`,
                        height: '100%',
                        background: 'linear-gradient(90deg, var(--accent-primary), var(--accent-primary-light, #818cf8))',
                        borderRadius: '999px',
                        transition: 'width 0.15s ease',
                    }} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '5px' }}>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Génération en cours</span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{progress}%</span>
                </div>
            </div>

            {/* Liste des étapes */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', width: '100%', maxWidth: '420px' }}>
                {PHASES.map((phase, i) => {
                    const isDone   = i < phaseIndex
                    const isActive = i === phaseIndex
                    return (
                        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            {/* Indicateur */}
                            <div style={{
                                width: '20px', height: '20px', borderRadius: '50%', flexShrink: 0,
                                background: isDone ? 'var(--success)' : isActive ? 'var(--accent-primary)' : 'var(--border-subtle)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                transition: 'background 0.4s',
                            }}>
                                {isDone ? (
                                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3.5">
                                        <polyline points="20,6 9,17 4,12" />
                                    </svg>
                                ) : isActive ? (
                                    <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'white' }} />
                                ) : null}
                            </div>
                            {/* Label */}
                            <span style={{
                                fontSize: '13px',
                                color: isDone ? 'var(--success)' : isActive ? 'var(--text-primary)' : 'var(--text-muted)',
                                transition: 'color 0.4s',
                                fontWeight: isActive ? '500' : '400',
                            }}>
                                {phase.label}
                            </span>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
