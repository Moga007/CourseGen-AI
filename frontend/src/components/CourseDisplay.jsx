import { useState } from 'react'
import axios from 'axios'
import Markdown from 'react-markdown'

const API_URL = 'http://localhost:8000'

export default function CourseDisplay({ contenu, moteurUtilise, formParams }) {
    const [copied, setCopied] = useState(false)
    const [copiedHtml, setCopiedHtml] = useState(false)
    const [slidesLoading, setSlidesLoading] = useState(false)
    const [slidesError, setSlidesError] = useState(null)

    const handleGenerateSlides = async () => {
        setSlidesLoading(true)
        setSlidesError(null)
        try {
            const response = await axios.post(`${API_URL}/generate-slides`, {
                contenu,
                specialite: formParams?.specialite || '',
                module: formParams?.module || '',
                chapitre: formParams?.chapitre || '',
            }, { timeout: 60000 })
            window.open(response.data.editor_url, '_blank')
        } catch (err) {
            const msg = err.response?.data?.detail || 'Erreur lors de la génération des slides.'
            setSlidesError(msg)
            setTimeout(() => setSlidesError(null), 5000)
        } finally {
            setSlidesLoading(false)
        }
    }

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(contenu)
            setCopied(true)
            setTimeout(() => setCopied(false), 2500)
        } catch (err) {
            // Fallback
            const textarea = document.createElement('textarea')
            textarea.value = contenu
            document.body.appendChild(textarea)
            textarea.select()
            document.execCommand('copy')
            document.body.removeChild(textarea)
            setCopied(true)
            setTimeout(() => setCopied(false), 2500)
        }
    }

    const handleCopyHtml = async () => {
        try {
            const el = document.querySelector('.course-content')
            const html = el.innerHTML
            const blob = new Blob([html], { type: 'text/html' })
            const item = new ClipboardItem({ 'text/html': blob })
            await navigator.clipboard.write([item])
            setCopiedHtml(true)
            setTimeout(() => setCopiedHtml(false), 2500)
        } catch (err) {
            // Fallback : copier le HTML en texte brut
            const el = document.querySelector('.course-content')
            const textarea = document.createElement('textarea')
            textarea.value = el.innerHTML
            document.body.appendChild(textarea)
            textarea.select()
            document.execCommand('copy')
            document.body.removeChild(textarea)
            setCopiedHtml(true)
            setTimeout(() => setCopiedHtml(false), 2500)
        }
    }

    return (
        <div className="glass-card p-6 sm:p-8 animate-fade-in-up">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-4"
                style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <div>
                    <h2 className="text-lg font-semibold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--success)' }}>
                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                            <polyline points="22,4 12,14.01 9,11.01" />
                        </svg>
                        Cours généré
                    </h2>
                    <p className="text-xs mt-1 flex items-center gap-1.5" style={{ color: 'var(--text-muted)' }}>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M12 2L2 7l10 5 10-5-10-5z" />
                            <path d="M2 17l10 5 10-5" />
                        </svg>
                        Généré par {moteurUtilise}
                    </p>
                </div>

                <div className="flex gap-2 flex-wrap">
                    {/* Bouton Générer les slides */}
                    <button
                        onClick={handleGenerateSlides}
                        disabled={slidesLoading}
                        className="btn-secondary"
                        title="Générer une présentation Beautiful.ai"
                    >
                        {slidesLoading ? (
                            <>
                                <div className="loading-spinner" style={{ width: '14px', height: '14px', borderWidth: '2px' }}></div>
                                Génération...
                            </>
                        ) : (
                            <>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <rect x="2" y="3" width="20" height="14" rx="2" />
                                    <path d="M8 21h8M12 17v4" />
                                    <path d="M7 8h10M7 12h6" />
                                </svg>
                                Générer les slides
                            </>
                        )}
                    </button>

                    {/* Bouton Copier HTML (pour LMS) */}
                    <button onClick={handleCopyHtml} className="btn-secondary copy-btn" title="Copiez le contenu formaté pour le coller dans votre LMS (Moodle, Canvas…)">
                        {copiedHtml ? (
                            <>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ color: 'var(--success)' }}>
                                    <polyline points="20,6 9,17 4,12" />
                                </svg>
                                <span style={{ color: 'var(--success)' }}>Copié !</span>
                            </>
                        ) : (
                            <>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <polyline points="16 18 22 12 16 6" />
                                    <polyline points="8 6 2 12 8 18" />
                                </svg>
                                Copier pour LMS
                            </>
                        )}
                    </button>

                    {/* Bouton Copier Markdown brut */}
                    <button onClick={handleCopy} className="btn-secondary copy-btn" title="Copier le Markdown brut">
                        {copied ? (
                            <>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" style={{ color: 'var(--success)' }}>
                                    <polyline points="20,6 9,17 4,12" />
                                </svg>
                                <span style={{ color: 'var(--success)' }}>Copié !</span>
                            </>
                        ) : (
                            <>
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                                </svg>
                                Markdown
                            </>
                        )}
                    </button>
                </div>

                {/* Erreur slides */}
                {slidesError && (
                    <div className="error-message mt-3 text-xs">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="10" />
                            <line x1="15" y1="9" x2="9" y2="15" />
                            <line x1="9" y1="9" x2="15" y2="15" />
                        </svg>
                        {slidesError}
                    </div>
                )}
            </div>

            {/* Markdown content */}
            <div className="course-content">
                <Markdown>{contenu}</Markdown>
            </div>
        </div>
    )
}
