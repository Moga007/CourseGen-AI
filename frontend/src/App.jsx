import { useState } from 'react'
import Header from './components/Header'
import CourseForm from './components/CourseForm'
import CourseDisplay from './components/CourseDisplay'
import LoadingSpinner from './components/LoadingSpinner'
import HistorySection from './components/HistorySection'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  // ── Mode Classic ─────────────────────────────────────────────────────────
  const [courseData, setCourseData] = useState(null)
  const [lastFormData, setLastFormData] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [replayData, setReplayData] = useState(null)
  const [streamingContent, setStreamingContent] = useState('')
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0)

  // ── Mode Multi-Agents V2 ──────────────────────────────────────────────────
  const [isV2Mode, setIsV2Mode] = useState(false)
  const [pipelineAgents, setPipelineAgents] = useState([
    { name: 'pedagogique', label: 'Agent Pédagogique', status: 'pending' },
    { name: 'redacteur',   label: 'Agent Rédacteur',   status: 'pending' },
    { name: 'designer',    label: 'Agent Designer',    status: 'pending' },
    { name: 'qualite',     label: 'Agent Qualité',     status: 'pending' },
  ])
  const [pipelineV2Data, setPipelineV2Data] = useState(null)
  const [v2ResumeToken, setV2ResumeToken] = useState(null)

  const handleGenerate = async (formData) => {
    setIsLoading(true)
    setError(null)
    setCourseData(null)
    setStreamingContent('')
    setLastFormData(formData)

    try {
      const response = await fetch(`${API_URL}/generate/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Erreur lors de la génération.')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let accumulated = ''
      let buffer = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        // Accumule les bytes reçus (les chunks SSE peuvent arriver fragmentés)
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() // garde la ligne incomplète pour le prochain tour

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.chunk !== undefined) {
              if (accumulated === '') setIsLoading(false) // cache le spinner dès le 1er token
              accumulated += data.chunk
              setStreamingContent(accumulated)
            } else if (data.done) {
              setCourseData({ contenu: accumulated, moteur_utilise: data.moteur_utilise })
              setStreamingContent('')
              setHistoryRefreshKey(prev => prev + 1)
            } else if (data.error) {
              setError(data.error)
            }
          } catch { /* ligne SSE malformée — on ignore */ }
        }
      }
    } catch (err) {
      if (err.name === 'TypeError') {
        setError('Impossible de contacter le serveur. Vérifiez que le backend est lancé (python main.py).')
      } else {
        setError(err.message || 'Une erreur inattendue est survenue. Veuillez réessayer.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleReplay = (formData) => {
    // Si l'entrée d'historique vient du pipeline V2, on bascule automatiquement en mode V2
    if (formData.isV2) {
      setIsV2Mode(true)
      setCourseData(null)
      setPipelineV2Data(null)
    }
    setReplayData(formData)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleGenerateV2 = async (formData) => {
    setIsLoading(true)
    setError(null)
    setPipelineV2Data(null)
    setLastFormData(formData)

    // Réinitialise tous les agents à "pending"
    setPipelineAgents([
      { name: 'pedagogique', label: 'Agent Pédagogique', status: 'pending' },
      { name: 'redacteur',   label: 'Agent Rédacteur',   status: 'pending' },
      { name: 'designer',    label: 'Agent Designer',    status: 'pending' },
      { name: 'qualite',     label: 'Agent Qualité',     status: 'pending' },
    ])

    const body = v2ResumeToken
      ? { ...formData, resume_from: v2ResumeToken.resume_from, previous_results: v2ResumeToken.context_snapshot }
      : formData

    try {
      const response = await fetch(`${API_URL}/generate-v2/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Erreur lors de la génération V2.')
      }

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
            const event = JSON.parse(line.slice(6))

            if (event.event === 'agent_start') {
              setPipelineAgents(prev => prev.map(a =>
                a.name === event.agent ? { ...a, status: 'running' } : a
              ))
            } else if (event.event === 'agent_success') {
              setPipelineAgents(prev => prev.map(a =>
                a.name === event.agent ? { ...a, status: 'success', duration: event.duration } : a
              ))
            } else if (event.event === 'agent_error') {
              setPipelineAgents(prev => prev.map(a =>
                a.name === event.agent ? { ...a, status: 'error', error: event.error } : a
              ))
              if (event.resume_token) setV2ResumeToken(event.resume_token)
              setError(`L'${event.agent} a échoué : ${event.error}`)
              setIsLoading(false)
            } else if (event.event === 'pipeline_complete') {
              setPipelineV2Data(event)
              setIsLoading(false)
            } else if (event.event === 'fatal_error') {
              setError(event.error)
              setIsLoading(false)
            }
          } catch { /* ligne SSE malformée */ }
        }
      }
    } catch (err) {
      setError(err.name === 'TypeError'
        ? 'Impossible de contacter le serveur. Vérifiez que le backend est lancé.'
        : err.message || 'Une erreur inattendue est survenue.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleRetryFromAgent = (agentName) => {
    if (v2ResumeToken && lastFormData) {
      handleGenerateV2(lastFormData)
    }
  }

  const handleToggleMode = (mode) => {
    setIsV2Mode(mode)
    setCourseData(null)
    setPipelineV2Data(null)
    setStreamingContent('')
    setError(null)
    setV2ResumeToken(null)
  }

  return (
    <div className="min-h-screen">
      <Header />

      <main className="max-w-5xl mx-auto px-4 mt-4 space-y-8">
        {/* Form */}
        <CourseForm
          onSubmit={isV2Mode ? handleGenerateV2 : handleGenerate}
          isLoading={isLoading}
          initialData={replayData}
          isV2Mode={isV2Mode}
          onToggleMode={handleToggleMode}
        />

        {/* Pipeline V2 — progression des agents */}
        {isV2Mode && (isLoading || pipelineAgents.some(a => a.status !== 'pending')) && (
          <div className="glass-card p-6 animate-fade-in-up">
            <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
              Pipeline Multi-Agents
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {pipelineAgents.map((agent, i) => {
                const colors = { pending: 'var(--text-muted)', running: 'var(--accent-primary-light)', success: '#4ade80', error: '#f87171', retrying: '#facc15' }
                const icons  = { pending: '○', success: '✓', error: '✗', retrying: '↻' }
                return (
                  <div key={agent.name} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    {/* Icône statut */}
                    <div style={{ width: '20px', textAlign: 'center', color: colors[agent.status] || colors.pending, fontSize: '14px' }}>
                      {agent.status === 'running'
                        ? <span className="loading-spinner" style={{ display: 'inline-block', width: '14px', height: '14px', border: '2px solid var(--accent-primary-light)', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                        : icons[agent.status] || '○'}
                    </div>
                    {/* Label */}
                    <span style={{ fontSize: '13px', fontWeight: agent.status === 'running' ? '600' : '400', color: agent.status === 'pending' ? 'var(--text-muted)' : 'var(--text-primary)', flex: 1 }}>
                      {agent.label}
                    </span>
                    {/* Durée */}
                    {agent.status === 'success' && agent.duration && (
                      <span style={{ fontSize: '11px', color: '#4ade80' }}>{agent.duration}s</span>
                    )}
                    {/* Barre de progression */}
                    <div style={{ width: '80px', height: '4px', background: 'var(--bg-primary)', borderRadius: '2px', overflow: 'hidden' }}>
                      <div style={{
                        height: '100%', borderRadius: '2px',
                        width: agent.status === 'success' ? '100%' : agent.status === 'running' ? '60%' : '0%',
                        background: colors[agent.status] || 'transparent',
                        transition: 'width 0.4s ease',
                      }} />
                    </div>
                  </div>
                )
              })}
            </div>
            {/* Résumé global */}
            <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ flex: 1, height: '6px', background: 'var(--bg-primary)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{
                    height: '100%', borderRadius: '3px',
                    width: `${pipelineAgents.filter(a => a.status === 'success').length * 25}%`,
                    background: 'linear-gradient(90deg, var(--accent-primary), var(--accent-primary-light))',
                    transition: 'width 0.4s ease',
                  }} />
                </div>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                  {pipelineAgents.filter(a => a.status === 'success').length} / 4 agents
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Résultat V2 */}
        {isV2Mode && pipelineV2Data && !isLoading && (
          <div className="glass-card p-6 animate-fade-in-up">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h2 style={{ color: 'var(--text-primary)', fontWeight: '600' }}>
                Cours généré — Pipeline Multi-Agents
              </h2>
              {pipelineV2Data.validation && (
                <span style={{ fontSize: '12px', padding: '4px 10px', borderRadius: '20px', background: 'rgba(74,222,128,0.15)', color: '#4ade80', border: '1px solid rgba(74,222,128,0.3)' }}>
                  Score qualité : {pipelineV2Data.validation.score_global}/100
                </span>
              )}
            </div>
            <CourseDisplay
              contenu={pipelineV2Data.contenu_final_markdown}
              moteurUtilise="multi-agents"
              formParams={lastFormData}
            />
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="error-message animate-fade-in-up">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
            {error}
          </div>
        )}

        {/* Loading — visible jusqu'au 1er token reçu */}
        {isLoading && (
          <div className="glass-card">
            <LoadingSpinner moteur={lastFormData?.moteur} />
          </div>
        )}

        {/* Streaming en cours — affiche le contenu au fur et à mesure */}
        {streamingContent && (
          <CourseDisplay
            contenu={streamingContent}
            moteurUtilise={lastFormData?.moteur}
            formParams={lastFormData}
            isStreaming={true}
          />
        )}

        {/* Course Result — affiché une fois le streaming terminé */}
        {courseData && !isLoading && !streamingContent && (
          <CourseDisplay
            contenu={courseData.contenu}
            moteurUtilise={courseData.moteur_utilise}
            formParams={lastFormData}
          />
        )}

        {/* Footer */}
        {!courseData && !isLoading && !error && (
          <div className="text-center py-12 animate-fade-in-up-delay">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-4"
              style={{ background: 'var(--accent-glow)', border: '1px solid var(--border-subtle)' }}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--accent-primary-light)' }}>
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
              Prêt à générer
            </h3>
            <p className="text-sm max-w-md mx-auto" style={{ color: 'var(--text-muted)' }}>
              Remplissez le formulaire ci-dessus pour générer automatiquement
              un cours académique structuré et de qualité.
            </p>
          </div>
        )}

        {/* History */}
        <HistorySection onReplay={handleReplay} refreshKey={historyRefreshKey} />
      </main>

      {/* Footer */}
      <footer style={{
        marginTop: '64px',
        borderTop: '1px solid var(--border-subtle)',
        background: 'rgba(15, 15, 30, 0.9)',
        backdropFilter: 'blur(12px)',
        padding: '24px 16px',
      }}>
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">

          {/* Logo + nom */}
          <div className="flex items-center gap-3">
            <img src="/logo-iesig.png" alt="IESIG" style={{ height: '36px', width: 'auto' }} />
            <div>
              <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                IESIG
              </p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Institut d'Enseignement Supérieur en Informatique et Gestion
              </p>
            </div>
          </div>

          {/* Copyright */}
          <div className="text-center sm:text-right">
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              © 2026 IESIG — Tous droits réservés
            </p>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)', opacity: 0.7 }}>
              Développé par <span style={{ color: 'var(--accent-primary-light)', fontWeight: '500' }}>Mohamed CHENNI</span>
            </p>
          </div>

        </div>
      </footer>
    </div>
  )
}

export default App
