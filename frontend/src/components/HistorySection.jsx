import { useState, useEffect } from 'react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function HistorySection({ onReplay, refreshKey = 0 }) {
    const [historique, setHistorique] = useState([])
    const [isLoading, setIsLoading] = useState(true)
    const [expanded, setExpanded] = useState(false)

    const VISIBLE = 3

    const fetchHistorique = async () => {
        try {
            const response = await axios.get(`${API_URL}/historique`)
            setHistorique(response.data)
        } catch {
            // Silencieux — l'historique n'est pas critique
        } finally {
            setIsLoading(false)
        }
    }

    useEffect(() => {
        fetchHistorique()
    }, [refreshKey])

    const formatDate = (isoDate) => {
        const d = new Date(isoDate)
        return d.toLocaleDateString('fr-FR', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        })
    }

    const isV2Entry = (entry) => entry.moteur === 'Pipeline Multi-Agents V2'

    const handleReplay = (entry) => {
        // Map le nom du moteur affiché vers la valeur du formulaire
        let moteur = 'mistral'
        if (entry.moteur.toLowerCase().includes('claude')) moteur = 'claude'
        else if (entry.moteur.toLowerCase().includes('groq') || entry.moteur.toLowerCase().includes('llama')) moteur = 'groq'
        else if (entry.moteur.toLowerCase().includes('gemini') || entry.moteur.toLowerCase().includes('google')) moteur = 'gemini'

        onReplay({
            specialite: entry.specialite,
            niveau: entry.niveau,
            module: entry.module,
            chapitre: entry.chapitre,
            moteur,
            // Indique à App.jsx de basculer en mode V2 si l'entrée vient du pipeline
            isV2: isV2Entry(entry),
        })

        // Scroll vers le haut pour voir le formulaire rempli
        window.scrollTo({ top: 0, behavior: 'smooth' })
    }

    if (isLoading) return null
    if (historique.length === 0) return null

    return (
        <div className="glass-card p-6 sm:p-8 animate-fade-in-up-delay">
            {/* Header */}
            <div className="mb-5 flex items-center justify-between">
                <h2 className="text-lg font-semibold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--accent-primary-light)' }}>
                        <circle cx="12" cy="12" r="10" />
                        <polyline points="12,6 12,12 16,14" />
                    </svg>
                    Historique des générations
                </h2>
                <span className="text-xs px-2 py-1 rounded-full"
                    style={{ background: 'var(--accent-glow)', color: 'var(--accent-primary-light)', border: '1px solid var(--border-subtle)' }}>
                    {historique.length} cours
                </span>
            </div>

            {/* Table */}
            <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                    <thead>
                        <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                            {['Date', 'Spécialité', 'Niveau', 'Module', 'Chapitre', 'Moteur IA', 'Durée', ''].map((col, i) => (
                                <th key={i} style={{
                                    padding: '10px 12px',
                                    textAlign: 'left',
                                    color: 'var(--text-muted)',
                                    fontWeight: 600,
                                    fontSize: '0.75rem',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.05em',
                                    whiteSpace: 'nowrap',
                                }}>{col}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {(expanded ? historique : historique.slice(0, VISIBLE)).map((entry) => (
                            <tr key={entry.id}
                                style={{ borderBottom: '1px solid var(--border-subtle)', transition: 'background 0.2s' }}
                                onMouseEnter={e => e.currentTarget.style.background = 'rgba(99, 102, 241, 0.05)'}
                                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                            >
                                <td style={{ padding: '12px', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                                    {formatDate(entry.date)}
                                </td>
                                <td style={{ padding: '12px', color: 'var(--text-primary)', fontWeight: 500 }}>
                                    {entry.specialite}
                                </td>
                                <td style={{ padding: '12px' }}>
                                    <span style={{
                                        background: 'var(--accent-glow)',
                                        color: 'var(--accent-primary-light)',
                                        padding: '2px 8px',
                                        borderRadius: '6px',
                                        fontSize: '0.8rem',
                                        fontWeight: 600,
                                    }}>{entry.niveau}</span>
                                </td>
                                <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>
                                    {entry.module}
                                </td>
                                <td style={{ padding: '12px', color: 'var(--text-secondary)', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    {entry.chapitre}
                                </td>
                                <td style={{ padding: '12px', whiteSpace: 'nowrap' }}>
                                    <span style={{
                                        background: isV2Entry(entry) ? 'rgba(139, 92, 246, 0.15)' :
                                            entry.moteur.includes('Groq') ? 'rgba(251, 191, 36, 0.1)' :
                                            entry.moteur.includes('Claude') ? 'rgba(248, 113, 113, 0.1)' :
                                            entry.moteur.includes('Gemini') || entry.moteur.includes('Google') ? 'rgba(52, 211, 153, 0.1)' :
                                                'rgba(99, 102, 241, 0.1)',
                                        color: isV2Entry(entry) ? '#a78bfa' :
                                            entry.moteur.includes('Groq') ? 'var(--warning)' :
                                            entry.moteur.includes('Claude') ? 'var(--error)' :
                                            entry.moteur.includes('Gemini') || entry.moteur.includes('Google') ? 'var(--success)' :
                                                'var(--accent-primary-light)',
                                        padding: '2px 8px',
                                        borderRadius: '6px',
                                        fontSize: '0.8rem',
                                        fontWeight: 500,
                                    }}>{entry.moteur}</span>
                                </td>
                                <td style={{ padding: '12px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                                    {entry.duree_secondes}s
                                </td>
                                <td style={{ padding: '12px' }}>
                                    <button
                                        onClick={() => handleReplay(entry)}
                                        title="Rejouer avec ces paramètres"
                                        style={{
                                            background: 'transparent',
                                            border: '1px solid var(--border-subtle)',
                                            borderRadius: '8px',
                                            padding: '6px 12px',
                                            color: 'var(--accent-primary-light)',
                                            fontSize: '0.8rem',
                                            fontWeight: 500,
                                            cursor: 'pointer',
                                            transition: 'all 0.2s',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '4px',
                                            fontFamily: 'Inter, sans-serif',
                                            whiteSpace: 'nowrap',
                                        }}
                                        onMouseEnter={e => {
                                            e.currentTarget.style.background = 'var(--accent-glow)'
                                            e.currentTarget.style.borderColor = 'var(--accent-primary)'
                                        }}
                                        onMouseLeave={e => {
                                            e.currentTarget.style.background = 'transparent'
                                            e.currentTarget.style.borderColor = 'var(--border-subtle)'
                                        }}
                                    >
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                            <polyline points="1,4 1,10 7,10" />
                                            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
                                        </svg>
                                        Rejouer
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Bouton voir tout / réduire */}
            {historique.length > VISIBLE && (
                <button
                    onClick={() => setExpanded(prev => !prev)}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        margin: '16px auto 0',
                        background: 'transparent',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '8px',
                        padding: '7px 16px',
                        color: 'var(--text-muted)',
                        fontSize: '0.8rem',
                        fontWeight: 500,
                        cursor: 'pointer',
                        fontFamily: 'Inter, sans-serif',
                        transition: 'all 0.2s',
                    }}
                    onMouseEnter={e => {
                        e.currentTarget.style.color = 'var(--accent-primary-light)'
                        e.currentTarget.style.borderColor = 'var(--accent-primary)'
                    }}
                    onMouseLeave={e => {
                        e.currentTarget.style.color = 'var(--text-muted)'
                        e.currentTarget.style.borderColor = 'var(--border-subtle)'
                    }}
                >
                    <svg
                        width="14" height="14" viewBox="0 0 24 24" fill="none"
                        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                        style={{ transition: 'transform 0.3s', transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}
                    >
                        <polyline points="6,9 12,15 18,9" />
                    </svg>
                    {expanded
                        ? `Réduire`
                        : `Voir les ${historique.length - VISIBLE} cours précédents`
                    }
                </button>
            )}
        </div>
    )
}
