import { useState } from 'react'
import Markdown from 'react-markdown'

export default function CourseDisplay({ contenu, moteurUtilise }) {
    const [copied, setCopied] = useState(false)

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

                <div className="flex gap-2">
                    <button onClick={handleCopy} className="btn-secondary copy-btn">
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
                                Copier
                            </>
                        )}
                    </button>
                </div>
            </div>

            {/* Markdown content */}
            <div className="course-content">
                <Markdown>{contenu}</Markdown>
            </div>
        </div>
    )
}
