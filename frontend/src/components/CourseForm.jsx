import { useState, useEffect } from 'react'

// Spécialités avec leurs niveaux autorisés
const SPECIALITES = [
    { value: 'GFC',  label: 'GFC — Gestion, Finance et Comptabilité',          niveaux: ['B1', 'B2', 'B3', 'M1', 'M2'] },
    { value: 'RH',   label: 'RH — Ressources Humaines et Management',           niveaux: ['B1', 'B2', 'B3', 'M1', 'M2'] },
    { value: 'IWA',  label: 'IWA — Informatique Web et Applicatif',              niveaux: ['B1', 'B2', 'B3'] },
    { value: 'DIA',  label: 'DIA — Data Science et Intelligence Artificielle',   niveaux: ['B1', 'B2', 'B3', 'M1', 'M2'] },
    { value: 'MCD',  label: 'MCD — Marketing et Communication Digitale',         niveaux: ['B1', 'B2', 'B3'] },
    { value: 'GPE',  label: 'GPE — Gestion, Projet et Entrepreneuriat',          niveaux: ['M1', 'M2'] },
]

// Labels affichés dans le select niveau
const NIVEAUX_LABELS = {
    B1: 'B1 — 1ʳᵉ année Bachelor',
    B2: 'B2 — 2ᵉ année Bachelor',
    B3: 'B3 — 3ᵉ année Bachelor',
    M1: 'M1 — 1ʳᵉ année Master',
    M2: 'M2 — 2ᵉ année Master',
}

// Groupes pour l'affichage (optgroup)
const NIVEAUX_GROUPE = { B1: 'Bachelor', B2: 'Bachelor', B3: 'Bachelor', M1: 'Master', M2: 'Master' }

export default function CourseForm({ onSubmit, isLoading, initialData }) {
    const [formData, setFormData] = useState({
        specialite: '',
        niveau: '',
        module: '',
        chapitre: '',
        moteur: 'mistral',
    })

    // Niveaux disponibles pour la spécialité sélectionnée
    const specialiteSelectionnee = SPECIALITES.find(s => s.value === formData.specialite)
    const niveauxDisponibles = specialiteSelectionnee ? specialiteSelectionnee.niveaux : []

    // Grouper les niveaux disponibles par Bachelor / Master
    const niveauxGroupes = ['Bachelor', 'Master'].map(groupe => ({
        groupe,
        options: niveauxDisponibles.filter(n => NIVEAUX_GROUPE[n] === groupe),
    })).filter(g => g.options.length > 0)

    const handleChange = (e) => {
        const { name, value } = e.target
        if (name === 'specialite') {
            const spec = SPECIALITES.find(s => s.value === value)
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
            <div className="mb-6">
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
                        required
                    >
                        <option value="" disabled>Choisir une spécialité…</option>
                        {SPECIALITES.map(s => (
                            <option key={s.value} value={s.value}>{s.label}</option>
                        ))}
                    </select>
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

            {/* Moteur IA */}
            <div className="mb-6">
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
                        className={`engine-option ${formData.moteur === 'oxlo' ? 'active' : ''}`}
                        onClick={() => setFormData({ ...formData, moteur: 'oxlo' })}
                    >
                        <span className="flex items-center justify-center gap-2">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <circle cx="12" cy="12" r="10" />
                                <path d="M8 12l2 2 4-4" />
                            </svg>
                            Oxlo (Qwen)
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
