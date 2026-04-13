import { useState } from 'react'
import axios from 'axios'
import Markdown from 'react-markdown'
import { SSE_EVENTS } from '../constants/sseEvents'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * AgentResultView — affiche le résultat complet du pipeline V2
 * Props:
 *   pipelineResult: { contenu_final_markdown, slides_json, validation, resume_executif, agents_context }
 *   formParams: { specialite, niveau, module, chapitre }
 */
export default function AgentResultView({ pipelineResult, formParams }) {
    const [activeTab, setActiveTab] = useState('cours')
    const [copied, setCopied] = useState(false)
    const [pptxLoading, setPptxLoading] = useState(false)
    const [pptxError, setPptxError] = useState(null)
    const [quizLoading, setQuizLoading] = useState(false)
    const [quizError, setQuizError] = useState(null)

    const score = pipelineResult.validation?.score_global
    const scoreColor = score >= 80 ? 'var(--success)' : score >= 60 ? '#f59e0b' : '#ef4444'

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(pipelineResult.contenu_final_markdown)
            setCopied(true)
            setTimeout(() => setCopied(false), 2500)
        } catch {
            const textarea = document.createElement('textarea')
            textarea.value = pipelineResult.contenu_final_markdown
            document.body.appendChild(textarea)
            textarea.select()
            document.execCommand('copy')
            document.body.removeChild(textarea)
            setCopied(true)
            setTimeout(() => setCopied(false), 2500)
        }
    }

    const handleGeneratePptx = async () => {
        setPptxLoading(true)
        setPptxError(null)
        try {
            // V2 : utilise le slides_json structuré de l'Agent Designer
            const hasSlides = pipelineResult.slides_json?.slides?.length > 0
            const endpoint  = hasSlides ? '/generate-v2/pptx' : '/generate-pptx'
            const payload   = hasSlides
                ? {
                    slides_json: pipelineResult.slides_json,
                    specialite:  formParams?.specialite || '',
                    module:      formParams?.module || '',
                    chapitre:    formParams?.chapitre || '',
                    niveau:      formParams?.niveau || '',
                  }
                : {
                    contenu:    pipelineResult.contenu_final_markdown,
                    specialite: formParams?.specialite || '',
                    module:     formParams?.module || '',
                    chapitre:   formParams?.chapitre || '',
                    niveau:     formParams?.niveau || '',
                  }

            const response = await axios.post(`${API_URL}${endpoint}`, payload,
                { timeout: 60000, responseType: 'blob' })

            const url = URL.createObjectURL(new Blob([response.data]))
            const a = document.createElement('a')
            a.href = url
            const slugify = s => (s || '').trim().replace(/\s+/g, '-')
            const pptxName = [formParams?.specialite, formParams?.niveau, formParams?.module, formParams?.chapitre]
                .filter(Boolean).map(slugify).join('-')
            a.download = `${pptxName || 'cours'}.pptx`
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            URL.revokeObjectURL(url)
        } catch (err) {
            setPptxError(err.response?.data?.detail || 'Erreur lors de la génération du PowerPoint.')
            setTimeout(() => setPptxError(null), 5000)
        } finally {
            setPptxLoading(false)
        }
    }

    const handleGenerateQuiz = async () => {
        setQuizLoading(true)
        setQuizError(null)
        try {
            const response = await fetch(`${API_URL}/generate-v2/quiz/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...formParams,
                    contenu_markdown: pipelineResult.contenu_final_markdown,
                }),
            })

            const reader = response.body.getReader()
            const decoder = new TextDecoder()
            let buffer = ''

            while (true) {
                const { value, done } = await reader.read()
                if (done) break
                buffer += decoder.decode(value, { stream: true })
                const lines = buffer.split('\n')
                buffer = lines.pop()

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue
                    try {
                        const data = JSON.parse(line.slice(6))
                        if (data.event === SSE_EVENTS.QUIZ_COMPLETE) {
                            const blob = new Blob([data.contenu_gift], { type: 'text/plain;charset=utf-8' })
                            const url = URL.createObjectURL(blob)
                            const a = document.createElement('a')
                            a.href = url
                            a.download = `quiz_${(formParams?.chapitre || 'cours').replace(/\s+/g, '_').toLowerCase()}.gift`
                            document.body.appendChild(a)
                            a.click()
                            document.body.removeChild(a)
                            URL.revokeObjectURL(url)
                        } else if (data.event === SSE_EVENTS.AGENT_ERROR || data.event === SSE_EVENTS.FATAL_ERROR) {
                            setQuizError(data.error || 'Erreur lors de la génération du quiz.')
                            setTimeout(() => setQuizError(null), 6000)
                        }
                    } catch { /* ligne SSE malformée */ }
                }
            }
        } catch (err) {
            setQuizError(err.message || 'Erreur lors de la génération du quiz.')
            setTimeout(() => setQuizError(null), 6000)
        } finally {
            setQuizLoading(false)
        }
    }

    const tabs = [
        { id: 'cours', label: 'Cours complet' },
        { id: 'slides', label: `Slides (${pipelineResult.slides_json?.total_slides || 0})` },
        { id: 'validation', label: 'Rapport qualité' },
    ]

    return (
        <div className="glass-card p-6 sm:p-8 animate-fade-in-up">
            {/* En-tête */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4 pb-4"
                style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <div>
                    <h2 className="text-lg font-semibold flex items-center gap-2"
                        style={{ color: 'var(--text-primary)' }}>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                            stroke="currentColor" strokeWidth="2" strokeLinecap="round"
                            style={{ color: 'var(--success)' }}>
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                            <polyline points="22,4 12,14.01 9,11.01" />
                        </svg>
                        Cours généré — Pipeline V2
                    </h2>
                    {pipelineResult.resume_executif && (
                        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)', maxWidth: '500px' }}>
                            {pipelineResult.resume_executif}
                        </p>
                    )}
                </div>

                {/* Score qualité */}
                {score !== undefined && (
                    <div style={{
                        padding: '6px 12px',
                        borderRadius: '20px',
                        background: `${scoreColor}18`,
                        border: `1px solid ${scoreColor}40`,
                        color: scoreColor,
                        fontSize: '13px',
                        fontWeight: '600',
                        whiteSpace: 'nowrap',
                    }}>
                        Score qualité : {score}/100
                    </div>
                )}
            </div>

            {/* Actions */}
            <div className="flex gap-2 flex-wrap mb-4">
                <button onClick={handleGeneratePptx} disabled={pptxLoading} className="btn-secondary">
                    {pptxLoading ? (
                        <><div className="loading-spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }} /> Génération...</>
                    ) : (
                        <><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
                            <polyline points="13,2 13,9 20,9" />
                        </svg> Export PowerPoint</>
                    )}
                </button>

                <button onClick={handleGenerateQuiz} disabled={quizLoading} className="btn-secondary">
                    {quizLoading ? (
                        <><div className="loading-spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }} /> Génération quiz...</>
                    ) : (
                        <><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                            <circle cx="12" cy="12" r="10" />
                            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                            <line x1="12" y1="17" x2="12.01" y2="17" />
                        </svg> Quiz GIFT</>
                    )}
                </button>

                <button onClick={handleCopy} className="btn-secondary copy-btn">
                    {copied ? (
                        <><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ color: 'var(--success)' }}><polyline points="20,6 9,17 4,12" /></svg>
                        <span style={{ color: 'var(--success)' }}>Copié !</span></>
                    ) : (
                        <><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                        </svg> Markdown</>
                    )}
                </button>
            </div>

            {/* Erreurs actions */}
            {(pptxError || quizError) && (
                <div className="error-message mb-4 text-xs">
                    {pptxError || quizError}
                </div>
            )}

            {/* Onglets */}
            <div className="flex gap-1 mb-4" style={{
                borderBottom: '1px solid var(--border-subtle)',
                paddingBottom: '0',
            }}>
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className="text-sm px-4 py-2"
                        style={{
                            background: 'transparent',
                            border: 'none',
                            borderBottom: activeTab === tab.id
                                ? '2px solid var(--accent-primary-light)'
                                : '2px solid transparent',
                            color: activeTab === tab.id
                                ? 'var(--accent-primary-light)'
                                : 'var(--text-muted)',
                            cursor: 'pointer',
                            fontWeight: activeTab === tab.id ? '600' : '400',
                            marginBottom: '-1px',
                            transition: 'all 0.15s',
                        }}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Contenu des onglets */}
            {activeTab === 'cours' && (
                <div className="course-content">
                    <Markdown>{pipelineResult.contenu_final_markdown}</Markdown>
                </div>
            )}

            {activeTab === 'slides' && (
                <SlidePreview slides={pipelineResult.slides_json?.slides || []} />
            )}

            {activeTab === 'validation' && (
                <ValidationReport validation={pipelineResult.validation} />
            )}
        </div>
    )
}

// ── Rendu d'une slide selon son layout ───────────────────────────────────────

function SlideCard({ slide, isCurrent }) {
    const contenu = slide.contenu || {}

    const layoutBadgeColors = {
        'bullets':      { bg: '#6366f120', color: '#818cf8' },
        'two-column':   { bg: '#8b5cf620', color: '#a78bfa' },
        'schema':       { bg: '#06b6d420', color: '#22d3ee' },
        'stat-callout': { bg: '#f59e0b20', color: '#fbbf24' },
    }
    const badge = layoutBadgeColors[slide.layout] || layoutBadgeColors['bullets']

    return (
        <div style={{
            background: 'linear-gradient(135deg, #1e1b4b 0%, #1a1035 100%)',
            border: `1px solid ${isCurrent ? 'var(--accent-primary-light)' : 'var(--border-subtle)'}`,
            borderRadius: '12px',
            padding: '24px 28px',
            minHeight: '220px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
            transition: 'border-color 0.2s',
            position: 'relative',
        }}>
            {/* Badge layout */}
            <span style={{
                position: 'absolute', top: '12px', right: '12px',
                fontSize: '10px', fontWeight: '600',
                padding: '2px 8px', borderRadius: '4px',
                background: badge.bg, color: badge.color,
            }}>
                {slide.layout}
            </span>

            {/* Titre */}
            <h3 style={{
                fontSize: '16px', fontWeight: '700',
                color: '#e0e7ff', lineHeight: '1.3',
                paddingRight: '80px',
                borderBottom: '1px solid rgba(255,255,255,0.1)',
                paddingBottom: '12px',
                margin: 0,
            }}>
                {slide.titre}
                {slide.sous_titre && (
                    <span style={{ display: 'block', fontSize: '12px', fontWeight: '400', color: '#a5b4fc', marginTop: '4px' }}>
                        {slide.sous_titre}
                    </span>
                )}
            </h3>

            {/* Contenu selon le layout */}
            <div style={{ flex: 1 }}>
                {slide.layout === 'bullets' && contenu.items && (
                    <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {contenu.items.map((item, i) => (
                            <li key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '13px', color: '#c7d2fe' }}>
                                <span style={{ color: 'var(--accent-primary-light)', marginTop: '2px', flexShrink: 0 }}>▸</span>
                                {item}
                            </li>
                        ))}
                    </ul>
                )}

                {slide.layout === 'two-column' && (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                        {[contenu.colonne_gauche, contenu.colonne_droite].map((col, i) => (
                            <div key={i} style={{
                                background: 'rgba(255,255,255,0.04)',
                                borderRadius: '8px', padding: '12px',
                                fontSize: '12px', color: '#c7d2fe',
                                lineHeight: '1.6',
                                whiteSpace: 'pre-wrap',
                            }}>
                                {col || '—'}
                            </div>
                        ))}
                    </div>
                )}

                {slide.layout === 'stat-callout' && contenu.stats && (
                    <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                        {contenu.stats.map((stat, i) => (
                            <div key={i} style={{
                                flex: '1 1 120px',
                                background: 'rgba(251,191,36,0.08)',
                                border: '1px solid rgba(251,191,36,0.25)',
                                borderRadius: '10px', padding: '14px 16px',
                                textAlign: 'center',
                            }}>
                                <div style={{ fontSize: '28px', fontWeight: '800', color: '#fbbf24', lineHeight: 1 }}>
                                    {stat.valeur}
                                </div>
                                <div style={{ fontSize: '11px', color: '#d1d5db', marginTop: '6px' }}>
                                    {stat.label}
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {slide.layout === 'schema' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {contenu.description_schema && (
                            <p style={{ fontSize: '12px', color: '#94a3b8', fontStyle: 'italic', margin: 0 }}>
                                {contenu.description_schema}
                            </p>
                        )}
                        {contenu.elements && (
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
                                {contenu.elements.map((el, i) => (
                                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        <span style={{
                                            padding: '4px 12px', borderRadius: '20px',
                                            background: 'rgba(6,182,212,0.12)',
                                            border: '1px solid rgba(6,182,212,0.3)',
                                            fontSize: '12px', color: '#22d3ee',
                                        }}>
                                            {el}
                                        </span>
                                        {i < contenu.elements.length - 1 && (
                                            <span style={{ color: '#4b5563', fontSize: '14px' }}>→</span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Note présentateur */}
            {slide.note_presentateur && (
                <div style={{
                    borderTop: '1px solid rgba(255,255,255,0.08)',
                    paddingTop: '10px',
                    fontSize: '11px', color: '#6b7280', fontStyle: 'italic',
                }}>
                    📝 {slide.note_presentateur}
                </div>
            )}
        </div>
    )
}

function SlidePreview({ slides }) {
    const [current, setCurrent] = useState(0)

    if (!slides || slides.length === 0) {
        return <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Aucune slide disponible.</p>
    }

    const slide = slides[current]

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Navigation */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                    Slide <strong style={{ color: 'var(--text-primary)' }}>{current + 1}</strong> / {slides.length}
                </span>
                <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                        onClick={() => setCurrent(c => Math.max(0, c - 1))}
                        disabled={current === 0}
                        style={{
                            width: '32px', height: '32px', borderRadius: '8px',
                            border: '1px solid var(--border-subtle)',
                            background: 'var(--bg-secondary)',
                            color: current === 0 ? 'var(--text-muted)' : 'var(--text-primary)',
                            cursor: current === 0 ? 'not-allowed' : 'pointer',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: '16px',
                        }}
                    >‹</button>
                    <button
                        onClick={() => setCurrent(c => Math.min(slides.length - 1, c + 1))}
                        disabled={current === slides.length - 1}
                        style={{
                            width: '32px', height: '32px', borderRadius: '8px',
                            border: '1px solid var(--border-subtle)',
                            background: 'var(--bg-secondary)',
                            color: current === slides.length - 1 ? 'var(--text-muted)' : 'var(--text-primary)',
                            cursor: current === slides.length - 1 ? 'not-allowed' : 'pointer',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: '16px',
                        }}
                    >›</button>
                </div>
            </div>

            {/* Slide courante */}
            <SlideCard slide={slide} isCurrent={true} />

            {/* Miniatures de navigation */}
            <div style={{
                display: 'flex', gap: '6px', flexWrap: 'wrap',
                paddingTop: '8px',
                borderTop: '1px solid var(--border-subtle)',
            }}>
                {slides.map((s, i) => (
                    <button
                        key={i}
                        onClick={() => setCurrent(i)}
                        title={s.titre}
                        style={{
                            width: '28px', height: '20px',
                            borderRadius: '4px',
                            border: `1px solid ${i === current ? 'var(--accent-primary-light)' : 'var(--border-subtle)'}`,
                            background: i === current ? 'var(--accent-primary)' : 'var(--bg-secondary)',
                            cursor: 'pointer',
                            fontSize: '9px',
                            color: i === current ? '#fff' : 'var(--text-muted)',
                            fontWeight: '600',
                        }}
                    >
                        {i + 1}
                    </button>
                ))}
            </div>
        </div>
    )
}

function ValidationReport({ validation }) {
    if (!validation) return null

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Métriques */}
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                {[
                    {
                        label: 'Score global',
                        value: `${validation.score_global}/100`,
                        ok: validation.score_global >= 70,
                    },
                    {
                        label: 'Conformité niveau',
                        value: validation.conformite_niveau ? 'Oui' : 'Non',
                        ok: validation.conformite_niveau,
                    },
                    {
                        label: 'Couverture objectifs',
                        value: validation.couverture_objectifs ? 'Oui' : 'Non',
                        ok: validation.couverture_objectifs,
                    },
                ].map(item => (
                    <div key={item.label} style={{
                        padding: '10px 16px',
                        background: item.ok ? 'rgba(34, 197, 94, 0.08)' : 'rgba(239, 68, 68, 0.08)',
                        border: `1px solid ${item.ok ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)'}`,
                        borderRadius: '8px',
                    }}>
                        <p className="text-xs" style={{ color: 'var(--text-muted)', marginBottom: '2px' }}>
                            {item.label}
                        </p>
                        <p className="text-sm font-semibold" style={{
                            color: item.ok ? 'var(--success)' : '#ef4444',
                        }}>
                            {item.value}
                        </p>
                    </div>
                ))}
            </div>

            {/* Corrections appliquées */}
            {validation.corrections_appliquees?.length > 0 && (
                <div>
                    <p className="text-sm font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
                        Corrections appliquées par l'Agent Qualité :
                    </p>
                    <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {validation.corrections_appliquees.map((correction, i) => (
                            <li key={i} className="text-sm" style={{
                                color: 'var(--text-muted)',
                                paddingLeft: '16px',
                                position: 'relative',
                            }}>
                                <span style={{
                                    position: 'absolute', left: 0,
                                    color: 'var(--accent-primary-light)',
                                }}>›</span>
                                {correction}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    )
}
