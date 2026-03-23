import { useState } from 'react'
import axios from 'axios'
import Markdown from 'react-markdown'

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
            const response = await axios.post(`${API_URL}/generate-pptx`, {
                contenu: pipelineResult.contenu_final_markdown,
                specialite: formParams?.specialite || '',
                module: formParams?.module || '',
                chapitre: formParams?.chapitre || '',
                niveau: formParams?.niveau || '',
            }, { timeout: 60000, responseType: 'blob' })

            const url = URL.createObjectURL(new Blob([response.data]))
            const a = document.createElement('a')
            a.href = url
            a.download = `${(formParams?.chapitre || 'cours').replace(/\s+/g, '_').toLowerCase()}.pptx`
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
                        if (data.event === 'quiz_complete') {
                            const blob = new Blob([data.contenu_gift], { type: 'text/plain;charset=utf-8' })
                            const url = URL.createObjectURL(blob)
                            const a = document.createElement('a')
                            a.href = url
                            a.download = `quiz_${(formParams?.chapitre || 'cours').replace(/\s+/g, '_').toLowerCase()}.gift`
                            document.body.appendChild(a)
                            a.click()
                            document.body.removeChild(a)
                            URL.revokeObjectURL(url)
                        } else if (data.event === 'agent_error' || data.event === 'fatal_error') {
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

function SlidePreview({ slides }) {
    if (slides.length === 0) {
        return <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Aucune slide disponible.</p>
    }

    const layoutColors = {
        'bullets': '#6366f1',
        'two-column': '#8b5cf6',
        'schema': '#06b6d4',
        'stat-callout': '#f59e0b',
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {slides.map((slide) => (
                <div key={slide.index} style={{
                    display: 'flex', alignItems: 'center', gap: '12px',
                    padding: '10px 12px',
                    background: 'var(--bg-secondary)',
                    borderRadius: '8px',
                    border: '1px solid var(--border-subtle)',
                }}>
                    <span style={{
                        fontSize: '11px', fontWeight: '600',
                        color: 'var(--text-muted)',
                        minWidth: '24px',
                    }}>
                        {String(slide.index + 1).padStart(2, '0')}
                    </span>
                    <span style={{
                        fontSize: '11px', fontWeight: '600',
                        padding: '2px 8px', borderRadius: '4px',
                        background: `${layoutColors[slide.layout] || '#6366f1'}20`,
                        color: layoutColors[slide.layout] || '#6366f1',
                        minWidth: '90px', textAlign: 'center',
                    }}>
                        {slide.layout}
                    </span>
                    <span className="text-sm" style={{ color: 'var(--text-primary)', flex: 1 }}>
                        {slide.titre}
                    </span>
                </div>
            ))}
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
