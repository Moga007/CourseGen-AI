import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const PER_PAGE = 8

export default function HistorySection({ onReplay, refreshKey = 0 }) {
    const [items, setItems]             = useState([])
    const [total, setTotal]             = useState(0)
    const [pages, setPages]             = useState(1)
    const [page, setPage]               = useState(1)
    const [filterSpecialite, setFilterSpecialite] = useState('')
    const [filterMoteur, setFilterMoteur]         = useState('')
    const [filterOptions, setFilterOptions]       = useState({ specialites: [], moteurs: [] })
    const [isLoading, setIsLoading]     = useState(true)

    // Charge les options de filtre une seule fois
    useEffect(() => {
        axios.get(`${API_URL}/historique/meta`)
            .then(r => setFilterOptions(r.data))
            .catch(() => {})
    }, [])

    const fetchPage = useCallback(async (p, specialite, moteur) => {
        setIsLoading(true)
        try {
            const params = { page: p, limit: PER_PAGE }
            if (specialite) params.specialite = specialite
            if (moteur)     params.moteur     = moteur
            const r = await axios.get(`${API_URL}/historique`, { params })
            setItems(r.data.items)
            setTotal(r.data.total)
            setPages(r.data.pages)
        } catch {
            // Silencieux — non critique
        } finally {
            setIsLoading(false)
        }
    }, [])

    // Relance quand page / filtres / refreshKey changent
    useEffect(() => {
        fetchPage(page, filterSpecialite, filterMoteur)
    }, [page, filterSpecialite, filterMoteur, refreshKey, fetchPage])

    // Réinitialise à la page 1 quand un filtre change
    const handleFilterSpecialite = (v) => { setFilterSpecialite(v); setPage(1) }
    const handleFilterMoteur     = (v) => { setFilterMoteur(v);     setPage(1) }

    const formatDate = (isoDate) => {
        const d = new Date(isoDate)
        return d.toLocaleDateString('fr-FR', {
            day: '2-digit', month: '2-digit', year: 'numeric',
            hour: '2-digit', minute: '2-digit',
        })
    }

    const isV2Entry = (entry) => entry.moteur === 'Pipeline Multi-Agents V2'

    const handleReplay = (entry) => {
        let moteur = 'mistral'
        if (entry.moteur.toLowerCase().includes('claude'))                                         moteur = 'claude'
        else if (entry.moteur.toLowerCase().includes('groq') || entry.moteur.toLowerCase().includes('llama'))   moteur = 'groq'
        else if (entry.moteur.toLowerCase().includes('gemini') || entry.moteur.toLowerCase().includes('google')) moteur = 'gemini'

        onReplay({
            specialite: entry.specialite,
            niveau:     entry.niveau,
            module:     entry.module,
            chapitre:   entry.chapitre,
            moteur,
            isV2:       isV2Entry(entry),
        })
        window.scrollTo({ top: 0, behavior: 'smooth' })
    }

    const moteurColor = (entry) => {
        if (isV2Entry(entry))                                                   return { bg: 'rgba(139,92,246,0.15)',  fg: '#a78bfa' }
        if (entry.moteur.includes('Groq'))                                      return { bg: 'rgba(251,191,36,0.1)',   fg: 'var(--warning)' }
        if (entry.moteur.includes('Claude'))                                    return { bg: 'rgba(248,113,113,0.1)',  fg: 'var(--error)' }
        if (entry.moteur.includes('Gemini') || entry.moteur.includes('Google')) return { bg: 'rgba(52,211,153,0.1)',   fg: 'var(--success)' }
        return { bg: 'rgba(99,102,241,0.1)', fg: 'var(--accent-primary-light)' }
    }

    if (!isLoading && total === 0 && !filterSpecialite && !filterMoteur) return null

    const selectStyle = {
        background:   'var(--bg-input)',
        border:       '1px solid var(--border-subtle)',
        borderRadius: '8px',
        padding:      '6px 10px',
        color:        'var(--text-secondary)',
        fontSize:     '0.8rem',
        cursor:       'pointer',
        fontFamily:   'Inter, sans-serif',
        outline:      'none',
    }

    const pageBtn = (label, targetPage, disabled) => (
        <button
            key={label}
            onClick={() => !disabled && setPage(targetPage)}
            disabled={disabled}
            style={{
                minWidth:     '32px',
                height:       '32px',
                padding:      '0 8px',
                borderRadius: '6px',
                border:       `1px solid ${targetPage === page ? 'var(--accent-primary)' : 'var(--border-subtle)'}`,
                background:   targetPage === page ? 'var(--accent-glow)' : 'transparent',
                color:        targetPage === page ? 'var(--accent-primary-light)' : disabled ? 'var(--text-muted)' : 'var(--text-secondary)',
                fontSize:     '0.8rem',
                fontWeight:   targetPage === page ? 600 : 400,
                cursor:       disabled ? 'not-allowed' : 'pointer',
                opacity:      disabled ? 0.4 : 1,
                fontFamily:   'Inter, sans-serif',
                transition:   'all 0.15s',
            }}
        >{label}</button>
    )

    // Calcule les numéros de page à afficher (window de 5 autour de la page courante)
    const pageNumbers = () => {
        if (pages <= 7) return Array.from({ length: pages }, (_, i) => i + 1)
        const nums = new Set([1, pages, page - 1, page, page + 1].filter(n => n >= 1 && n <= pages))
        const sorted = [...nums].sort((a, b) => a - b)
        const result = []
        let prev = null
        for (const n of sorted) {
            if (prev !== null && n - prev > 1) result.push('…')
            result.push(n)
            prev = n
        }
        return result
    }

    return (
        <div className="glass-card p-6 sm:p-8 animate-fade-in-up-delay">
            {/* Header */}
            <div className="mb-5 flex items-center justify-between flex-wrap gap-3">
                <h2 className="text-lg font-semibold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--accent-primary-light)' }}>
                        <circle cx="12" cy="12" r="10" />
                        <polyline points="12,6 12,12 16,14" />
                    </svg>
                    Historique des générations
                </h2>
                <span className="text-xs px-2 py-1 rounded-full"
                    style={{ background: 'var(--accent-glow)', color: 'var(--accent-primary-light)', border: '1px solid var(--border-subtle)' }}>
                    {total} cours
                </span>
            </div>

            {/* Filtres */}
            <div style={{ display: 'flex', gap: '10px', marginBottom: '16px', flexWrap: 'wrap' }}>
                <select value={filterSpecialite} onChange={e => handleFilterSpecialite(e.target.value)} style={selectStyle}>
                    <option value="">Toutes les spécialités</option>
                    {filterOptions.specialites.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
                <select value={filterMoteur} onChange={e => handleFilterMoteur(e.target.value)} style={selectStyle}>
                    <option value="">Tous les moteurs</option>
                    {filterOptions.moteurs.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
                {(filterSpecialite || filterMoteur) && (
                    <button
                        onClick={() => { handleFilterSpecialite(''); handleFilterMoteur('') }}
                        style={{ ...selectStyle, border: '1px solid var(--border-active)', color: 'var(--accent-primary-light)', cursor: 'pointer' }}
                    >
                        ✕ Réinitialiser
                    </button>
                )}
            </div>

            {/* Table */}
            {isLoading ? (
                <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    Chargement…
                </div>
            ) : items.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    Aucun résultat pour ces filtres.
                </div>
            ) : (
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
                            {items.map((entry) => {
                                const { bg, fg } = moteurColor(entry)
                                return (
                                    <tr key={entry.id}
                                        style={{ borderBottom: '1px solid var(--border-subtle)', transition: 'background 0.2s' }}
                                        onMouseEnter={e => e.currentTarget.style.background = 'rgba(99,102,241,0.05)'}
                                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                                    >
                                        <td style={{ padding: '12px', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                                            {formatDate(entry.date)}
                                        </td>
                                        <td style={{ padding: '12px', color: 'var(--text-primary)', fontWeight: 500 }}>
                                            {entry.specialite}
                                        </td>
                                        <td style={{ padding: '12px' }}>
                                            <span style={{ background: 'var(--accent-glow)', color: 'var(--accent-primary-light)', padding: '2px 8px', borderRadius: '6px', fontSize: '0.8rem', fontWeight: 600 }}>
                                                {entry.niveau}
                                            </span>
                                        </td>
                                        <td style={{ padding: '12px', color: 'var(--text-secondary)' }}>
                                            {entry.module}
                                        </td>
                                        <td style={{ padding: '12px', color: 'var(--text-secondary)', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                                            title={entry.chapitre}>
                                            {entry.chapitre}
                                        </td>
                                        <td style={{ padding: '12px', whiteSpace: 'nowrap' }}>
                                            <span style={{ background: bg, color: fg, padding: '2px 8px', borderRadius: '6px', fontSize: '0.8rem', fontWeight: 500 }}>
                                                {entry.moteur}
                                            </span>
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
                                                onMouseEnter={e => { e.currentTarget.style.background = 'var(--accent-glow)'; e.currentTarget.style.borderColor = 'var(--accent-primary)' }}
                                                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'var(--border-subtle)' }}
                                            >
                                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                    <polyline points="1,4 1,10 7,10" />
                                                    <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
                                                </svg>
                                                Rejouer
                                            </button>
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Pagination */}
            {pages > 1 && (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '16px', flexWrap: 'wrap', gap: '8px' }}>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                        Page {page} / {pages} — {total} entrée{total > 1 ? 's' : ''}
                    </span>
                    <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                        {pageBtn('←', page - 1, page === 1)}
                        {pageNumbers().map((n, i) =>
                            n === '…'
                                ? <span key={`sep-${i}`} style={{ padding: '0 4px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>…</span>
                                : pageBtn(n, n, false)
                        )}
                        {pageBtn('→', page + 1, page === pages)}
                    </div>
                </div>
            )}
        </div>
    )
}
