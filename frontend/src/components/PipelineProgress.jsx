/**
 * PipelineProgress — affiche l'état de progression des agents du pipeline V2
 * Props:
 *   agents: Array<{name, label, status, duration, attempt, error}>
 *   onRetryFrom: (agentName: string) => void
 */
export default function PipelineProgress({ agents, onRetryFrom }) {
    const statusConfig = {
        pending:  { color: 'var(--text-muted)',          icon: '○', label: 'En attente' },
        running:  { color: 'var(--accent-primary-light)', icon: '◉', label: 'En cours...' },
        retrying: { color: '#f59e0b',                    icon: '↻', label: 'Nouvelle tentative...' },
        success:  { color: 'var(--success)',              icon: '✓', label: 'Terminé' },
        error:    { color: '#ef4444',                    icon: '✗', label: 'Erreur' },
        skipped:  { color: 'var(--text-muted)',          icon: '↩', label: 'Ignoré (reprise)' },
    }

    const completedCount = agents.filter(a => a.status === 'success' || a.status === 'skipped').length
    const progressPercent = agents.length > 0 ? Math.round((completedCount / agents.length) * 100) : 0

    return (
        <div className="glass-card p-6 animate-fade-in-up">
            {/* En-tête */}
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-semibold flex items-center gap-2"
                    style={{ color: 'var(--text-primary)' }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
                        stroke="currentColor" strokeWidth="2" strokeLinecap="round"
                        style={{ color: 'var(--accent-primary-light)' }}>
                        <circle cx="12" cy="12" r="3" />
                        <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" />
                    </svg>
                    Pipeline Multi-Agents V2
                </h3>
                <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                    {completedCount}/{agents.length} agents
                </span>
            </div>

            {/* Barre de progression globale */}
            <div className="mb-5" style={{
                height: '4px',
                background: 'var(--bg-secondary)',
                borderRadius: '2px',
                overflow: 'hidden',
            }}>
                <div style={{
                    height: '100%',
                    width: `${progressPercent}%`,
                    background: 'linear-gradient(90deg, var(--accent-primary), var(--accent-primary-light))',
                    borderRadius: '2px',
                    transition: 'width 0.4s ease',
                }} />
            </div>

            {/* Liste des agents */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {agents.map((agent, index) => {
                    const cfg = statusConfig[agent.status] || statusConfig.pending
                    return (
                        <div key={agent.name} style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                            {/* Icône + connecteur vertical */}
                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: '24px' }}>
                                <div style={{
                                    width: '24px', height: '24px',
                                    borderRadius: '50%',
                                    background: agent.status === 'success' || agent.status === 'skipped'
                                        ? 'rgba(34, 197, 94, 0.1)'
                                        : agent.status === 'error'
                                            ? 'rgba(239, 68, 68, 0.1)'
                                            : agent.status === 'running' || agent.status === 'retrying'
                                                ? 'rgba(139, 92, 246, 0.1)'
                                                : 'var(--bg-secondary)',
                                    border: `1px solid ${cfg.color}`,
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    fontSize: '11px', color: cfg.color,
                                    flexShrink: 0,
                                }}>
                                    {agent.status === 'running' || agent.status === 'retrying'
                                        ? <div className="loading-spinner" style={{ width: '12px', height: '12px', borderWidth: '2px' }} />
                                        : cfg.icon
                                    }
                                </div>
                                {/* Connecteur vers l'agent suivant */}
                                {index < agents.length - 1 && (
                                    <div style={{
                                        width: '1px', height: '12px',
                                        background: 'var(--border-subtle)',
                                        marginTop: '2px',
                                    }} />
                                )}
                            </div>

                            {/* Infos de l'agent */}
                            <div style={{ flex: 1, paddingBottom: index < agents.length - 1 ? '0' : '0' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                    <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                                        {agent.label}
                                    </span>
                                    <span className="text-xs" style={{ color: cfg.color }}>
                                        {agent.status === 'success' && agent.duration
                                            ? `✓ ${agent.duration}s`
                                            : agent.status === 'retrying'
                                                ? `Tentative ${agent.attempt}...`
                                                : cfg.label
                                        }
                                    </span>
                                </div>

                                {/* Message d'erreur + bouton relancer */}
                                {agent.status === 'error' && (
                                    <div style={{ marginTop: '6px' }}>
                                        <p className="text-xs" style={{
                                            color: '#ef4444',
                                            background: 'rgba(239, 68, 68, 0.08)',
                                            border: '1px solid rgba(239, 68, 68, 0.2)',
                                            borderRadius: '6px',
                                            padding: '6px 8px',
                                            marginBottom: '6px',
                                        }}>
                                            {agent.error}
                                        </p>
                                        <button
                                            onClick={() => onRetryFrom(agent.name)}
                                            className="btn-secondary"
                                            style={{ fontSize: '12px', padding: '4px 10px' }}
                                        >
                                            ↻ Relancer depuis cet agent
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
