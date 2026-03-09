import { useState, useEffect } from 'react'

const NIVEAUX = [
    { value: 'L1', label: 'L1 — 1ʳᵉ année Licence' },
    { value: 'L2', label: 'L2 — 2ᵉ année Licence' },
    { value: 'L3', label: 'L3 — 3ᵉ année Licence' },
    { value: 'M1', label: 'M1 — 1ʳᵉ année Master' },
    { value: 'M2', label: 'M2 — 2ᵉ année Master' },
]

export default function CourseForm({ onSubmit, isLoading, initialData }) {
    const [formData, setFormData] = useState({
        specialite: '',
        niveau: 'L3',
        module: '',
        chapitre: '',
        moteur: 'mistral',
    })

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value })
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

    const isFormValid = formData.specialite && formData.module && formData.chapitre

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
                    <input
                        type="text"
                        id="specialite"
                        name="specialite"
                        className="form-input"
                        placeholder="Ex : Informatique, Droit, Médecine..."
                        value={formData.specialite}
                        onChange={handleChange}
                        required
                    />
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
                    >
                        {NIVEAUX.map(n => (
                            <option key={n.value} value={n.value}>{n.label}</option>
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
