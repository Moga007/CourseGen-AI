import { useState, useEffect } from 'react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Labels fixes pour les niveaux (pas de config nécessaire, noms standardisés)
const NIVEAUX_LABELS = {
    B1: 'B1 — 1ʳᵉ année Bachelor',
    B2: 'B2 — 2ᵉ année Bachelor',
    B3: 'B3 — 3ᵉ année Bachelor',
    M1: 'M1 — 1ʳᵉ année Master',
    M2: 'M2 — 2ᵉ année Master',
}
const NIVEAUX_GROUPE = { B1: 'Bachelor', B2: 'Bachelor', B3: 'Bachelor', M1: 'Master', M2: 'Master' }

export default function CourseForm({ onSubmit, isLoading, initialData, isV2Mode, onToggleMode }) {
    const [specialites, setSpecialites]     = useState([])
    const [specialitesError, setSpecialitesError] = useState(false)
    const [formData, setFormData] = useState({
        specialite: '',
        niveau: '',
        module: '',
        chapitre: '',
        moteur: 'mistral',
    })

    // Chargement des spécialités depuis l'API au montage
    useEffect(() => {
        axios.get(`${API_URL}/specialites`)
            .then(r => setSpecialites(r.data))
            .catch(() => setSpecialitesError(true))
    }, [])

    // Niveaux disponibles pour la spécialité sélectionnée
    const specialiteSelectionnee = specialites.find(s => s.value === formData.specialite)
    const niveauxDisponibles = specialiteSelectionnee ? specialiteSelectionnee.niveaux : []

    // Grouper les niveaux disponibles par Bachelor / Master
    const niveauxGroupes = ['Bachelor', 'Master'].map(groupe => ({
        groupe,
        options: niveauxDisponibles.filter(n => NIVEAUX_GROUPE[n] === groupe),
    })).filter(g => g.options.length > 0)

    const handleChange = (e) => {
        const { name, value } = e.target
        if (name === 'specialite') {
            const spec = specialites.find(s => s.value === value)
            setFormData({ ...formData, specialite: value, niveau: spec ? spec.niveaux[0] : '' })
        } else {
            setFormData({ ...formData, [name]: value })
        }
    }

    const handleSubmit = (e) => {
        e.preventDefault()
        onSubmit(formData)
    }

    // Replay : remplir le formulaire quand initialData change
    useEffect(() => {
        if (initialData) {
            setFormData(initialData)
        }
    }, [initialData])

    const isFormValid = formData.specialite && formData.niveau && formData.module && formData.chapitre

    return (
        <form onSubmit={handleSubmit} className="glass-card p-6 sm:p-8 animate-fade-in-up-delay">
            {/* Header */}
            <div className="flex items-start justify-between mb-6">
                <div>
                    <h2 className="text-lg font-semibold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--accent-primary-light)' }}>
                            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                            <polyline points="14,2 14,8 20,8" />
                            <line x1="16" y1="13" x2="8" y2="13" />
                            <line x1="16" y1="17" x2="8" y2="17" />
                            <line x1="10" y1="9" x2="8" y2="9" />
                        </svg>
                        Paramètres du cours
                    </h2>
                    <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
                        Renseignez les informations pour générer votre cours
                    </p>
                </div>

                {/* Toggle Classic / Multi-Agents */}
                {onToggleMode && (
                    <div style={{
                        display: 'inline-flex',
                        background: 'var(--bg-primary)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '10px',
                        padding: '3px',
                        gap: '2px',
                        flexShrink: 0,
                    }}>
                        {[
                            { id: false, label: 'Classic' },
                            { id: true,  label: '⚡ Multi-Agents' },
                        ].map(mode => (
                            <button
                                key={String(mode.id)}
                                type="button"
                                onClick={() => onToggleMode(mode.id)}
                                style={{
                                    padding: '5px 14px',
                                    borderRadius: '7px',
                                    border: 'none',
                                    fontSize: '12px',
                                    fontWeight: isV2Mode === mode.id ? '600' : '400',
                                    background: isV2Mode === mode.id
                                        ? 'linear-gradient(135deg, var(--accent-primary), var(--accent-primary-light))'
                                        : 'transparent',
                                    color: isV2Mode === mode.id ? '#fff' : 'var(--text-muted)',
                                    cursor: 'pointer',
                                    transition: 'all 0.15s',
                                    whiteSpace: 'nowrap',
                                }}
                            >
                                {mode.label}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {/* Grid layout */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mb-6">
                {/* Spécialité */}
                <div>
                    <label htmlFor="specialite" className="form-label">Spécialité</label>
                    <select
                        id="specialite"
                        name="specialite"
                        className="form-select"
                        value={formData.specialite}
                        onChange={handleChange}
                        disabled={specialites.length === 0}
                        required
                    >
                        <option value="" disabled>
                            {specialitesError ? 'Erreur de chargement' : specialites.length === 0 ? 'Chargement…' : 'Choisir une spécialité…'}
                        </option>
                        {specialites.map(s => (
                            <option key={s.value} value={s.value}>{s.label}</option>
                        ))}
                    </select>
                    {specialitesError && (
                        <p style={{ fontSize: '0.75rem', color: 'var(--error)', marginTop: '4px' }}>
                            Impossible de charger les spécialités. Vérifiez que le backend est lancé.
                        </p>
                    )}
                </div>

                {/* Niveau */}
                <div>
                    <label htmlFor="niveau" className="form-label">Niveau</label>
                    <select
                        id="niveau"
                        name="niveau"
                        className="form-select"
                        value={formData.niveau}
                        onChange={handleChange}
                        disabled={!formData.specialite}
                    >
                        {!formData.specialite && (
                            <option value="" disabled>Choisir d'abord une spécialité</option>
                        )}
                        {niveauxGroupes.map(g => (
                            <optgroup key={g.groupe} label={g.groupe}>
                                {g.options.map(n => (
                                    <option key={n} value={n}>{NIVEAUX_LABELS[n]}</option>
                                ))}
                            </optgroup>
                        ))}
                    </select>
                </div>

                {/* Module */}
                <div>
                    <label htmlFor="module" className="form-label">Module</label>
                    <input
                        type="text"
                        id="module"
                        name="module"
                        className="form-input"
                        placeholder="Ex : Systèmes d'exploitation"
                        value={formData.module}
                        onChange={handleChange}
                        required
                    />
                </div>

                {/* Chapitre */}
                <div>
                    <label htmlFor="chapitre" className="form-label">Chapitre</label>
                    <input
                        type="text"
                        id="chapitre"
                        name="chapitre"
                        className="form-input"
                        placeholder="Ex : Gestion de la mémoire"
                        value={formData.chapitre}
                        onChange={handleChange}
                        required
                    />
                </div>
            </div>

            {/* Moteur IA — masqué en mode Multi-Agents */}
            <div className="mb-6" style={{ display: isV2Mode ? 'none' : 'block' }}>
                <label className="form-label">Moteur IA</label>
                <div className="engine-toggle">
                    <button
                        type="button"
                        className={`engine-option ${formData.moteur === 'mistral' ? 'active' : ''}`}
                        onClick={() => setFormData({ ...formData, moteur: 'mistral' })}
                    >
                        <span className="flex items-center justify-center gap-2">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <circle cx="12" cy="12" r="10" />
                                <path d="M8 12l2 2 4-4" />
                            </svg>
                            Mistral AI
                        </span>
                    </button>
                    <button
                        type="button"
                        className={`engine-option ${formData.moteur === 'claude' ? 'active' : ''}`}
                        onClick={() => setFormData({ ...formData, moteur: 'claude' })}
                    >
                        <span className="flex items-center justify-center gap-2">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <circle cx="12" cy="12" r="10" />
                                <path d="M8 12l2 2 4-4" />
                            </svg>
                            Claude (Anthropic)
                        </span>
                    </button>
                    <button
                        type="button"
                        className={`engine-option ${formData.moteur === 'groq' ? 'active' : ''}`}
                        onClick={() => setFormData({ ...formData, moteur: 'groq' })}
                    >
                        <span className="flex items-center justify-center gap-2">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <circle cx="12" cy="12" r="10" />
                                <path d="M8 12l2 2 4-4" />
                            </svg>
                            Groq (LLaMA)
                        </span>
                    </button>
                    <button
                        type="button"
                        className={`engine-option ${formData.moteur === 'gemini' ? 'active' : ''}`}
                        onClick={() => setFormData({ ...formData, moteur: 'gemini' })}
                    >
                        <span className="flex items-center justify-center gap-2">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <circle cx="12" cy="12" r="10" />
                                <path d="M12 2l3 7h7l-5.5 4 2 7L12 16l-6.5 4 2-7L2 9h7z" />
                            </svg>
                            Gemini 3 Flash
                        </span>
                    </button>
                </div>
            </div>

            {/* Submit */}
            <button
                type="submit"
                className="btn-primary w-full"
                disabled={!isFormValid || isLoading}
            >
                {isLoading ? (
                    <>
                        <div className="loading-spinner" style={{ width: '20px', height: '20px', borderWidth: '2px' }}></div>
                        Génération en cours...
                    </>
                ) : (
                    <>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M12 2L2 7l10 5 10-5-10-5z" />
                            <path d="M2 17l10 5 10-5" />
                            <path d="M2 12l10 5 10-5" />
                        </svg>
                        Générer le cours
                    </>
                )}
            </button>
        </form>
    )
}
