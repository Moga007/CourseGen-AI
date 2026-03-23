export default function Header() {
    return (
        <header className="w-full py-4 px-4 animate-fade-in-up"
            style={{
                borderBottom: '1px solid var(--border-subtle)',
                background: 'rgba(15, 15, 30, 0.8)',
                backdropFilter: 'blur(12px)',
                position: 'sticky',
                top: 0,
                zIndex: 50,
            }}>
            <div className="max-w-5xl mx-auto flex items-center justify-between">

                {/* Gauche : Logo IESIG + séparateur + CourseGen AI */}
                <div className="flex items-center gap-4">
                    {/* Logo IESIG */}
                    <img
                        src="/logo-iesig.png"
                        alt="IESIG"
                        style={{ height: '42px', width: 'auto', objectFit: 'contain' }}
                    />

                    {/* Séparateur vertical */}
                    <div style={{ width: '1px', height: '36px', background: 'var(--border-subtle)' }} />

                    {/* Branding CourseGen AI */}
                    <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                            style={{ background: 'var(--accent-gradient)' }}>
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
                                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
                            </svg>
                        </div>
                        <div>
                            <h1 className="text-lg font-bold leading-tight" style={{ color: 'var(--text-primary)' }}>
                                CourseGen{' '}
                                <span style={{ background: 'var(--accent-gradient)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                                    AI
                                </span>
                            </h1>
                            <p className="text-xs leading-tight" style={{ color: 'var(--text-muted)' }}>
                                Génération automatique de cours académiques
                            </p>
                        </div>
                    </div>
                </div>

                {/* Droite : badge statut */}
                <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full"
                    style={{
                        background: 'rgba(52, 211, 153, 0.1)',
                        border: '1px solid rgba(52, 211, 153, 0.2)',
                    }}>
                    <div className="w-2 h-2 rounded-full" style={{ background: 'var(--success)' }} />
                    <span className="text-xs font-medium" style={{ color: 'var(--success)' }}>
                        Système opérationnel
                    </span>
                </div>
            </div>
        </header>
    )
}
