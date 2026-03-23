import { useState } from 'react'
import Header from './components/Header'
import CourseForm from './components/CourseForm'
import CourseDisplay from './components/CourseDisplay'
import LoadingSpinner from './components/LoadingSpinner'
import HistorySection from './components/HistorySection'
import PipelineProgress from './components/PipelineProgress'
import AgentResultView from './components/AgentResultView'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Agents initiaux du pipeline V2 (état par défaut)
const PIPELINE_AGENTS_INIT = [
  { name: 'pedagogique', label: 'Agent Pédagogique', status: 'pending' },
  { name: 'redacteur',   label: 'Agent Rédacteur',   status: 'pending' },
  { name: 'designer',    label: 'Agent Designer',     status: 'pending' },
  { name: 'qualite',     label: 'Agent Qualité',      status: 'pending' },
]

function App() {
  const [courseData, setCourseData] = useState(null)
  const [lastFormData, setLastFormData] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [replayData, setReplayData] = useState(null)
  const [streamingContent, setStreamingContent] = useState('')
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0)

  // États V2
  const [isV2Mode, setIsV2Mode] = useState(false)
  const [pipelineAgents, setPipelineAgents] = useState(PIPELINE_AGENTS_INIT)
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

  const handleGenerateV2 = async (formData, resumeToken = null) => {
    setIsLoading(true)
    setError(null)
    setPipelineV2Data(null)
    setLastFormData(formData)

    // Réinitialise ou reprend les agents
    if (resumeToken) {
      setPipelineAgents(prev => prev.map(a =>
        resumeToken.completed_agents.includes(a.name)
          ? { ...a, status: 'skipped' }
          : { ...a, status: 'pending', error: undefined, duration: undefined }
      ))
    } else {
      setPipelineAgents(PIPELINE_AGENTS_INIT)
      setV2ResumeToken(null)
    }

    const body = resumeToken
      ? { ...formData, resume_from: resumeToken.resume_from, previous_results: resumeToken.context_snapshot }
      : formData

    try {
      const response = await fetch(`${API_URL}/generate-v2/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Erreur lors du lancement du pipeline V2.')
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
                a.name === event.agent
                  ? { ...a, status: 'success', duration: event.duration, attempt: event.attempt }
                  : a
              ))
            } else if (event.event === 'agent_error') {
              setPipelineAgents(prev => prev.map(a =>
                a.name === event.agent
                  ? { ...a, status: 'error', error: event.error }
                  : a
              ))
              if (event.resume_token) {
                setV2ResumeToken(event.resume_token)
              }
            } else if (event.event === 'agent_skipped') {
              setPipelineAgents(prev => prev.map(a =>
                a.name === event.agent ? { ...a, status: 'skipped' } : a
              ))
            } else if (event.event === 'pipeline_complete') {
              setPipelineV2Data(event)
              setV2ResumeToken(null)
            } else if (event.event === 'fatal_error') {
              setError(event.error || 'Erreur fatale dans le pipeline.')
            }
          } catch { /* ligne SSE malformée */ }
        }
      }
    } catch (err) {
      if (err.name === 'TypeError') {
        setError('Impossible de contacter le serveur. Vérifiez que le backend est lancé.')
      } else {
        setError(err.message || 'Une erreur inattendue est survenue.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleRetryFromAgent = (agentName) => {
    if (v2ResumeToken && lastFormData) {
      handleGenerateV2(lastFormData, v2ResumeToken)
    }
  }

  const handleSubmit = (formData) => {
    if (isV2Mode) {
      handleGenerateV2(formData)
    } else {
      handleGenerate(formData)
    }
  }

  const handleReplay = (formData) => {
    setReplayData(formData)
  }

  return (
    <div className="min-h-screen pb-12">
      <Header />

      <main className="max-w-5xl mx-auto px-4 mt-4 space-y-8">
        {/* Form */}
        <CourseForm
          onSubmit={handleSubmit}
          isLoading={isLoading}
          initialData={replayData}
          isV2Mode={isV2Mode}
          onToggleMode={(mode) => { setIsV2Mode(mode); setCourseData(null); setPipelineV2Data(null); setError(null) }}
        />

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

        {/* Loading V1 — visible jusqu'au 1er token reçu */}
        {isLoading && !isV2Mode && (
          <div className="glass-card">
            <LoadingSpinner moteur={lastFormData?.moteur} />
          </div>
        )}

        {/* Pipeline V2 en cours */}
        {isV2Mode && (isLoading || pipelineV2Data) && (
          <PipelineProgress agents={pipelineAgents} onRetryFrom={handleRetryFromAgent} />
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

        {/* Course Result V1 — affiché une fois le streaming terminé */}
        {courseData && !isLoading && !streamingContent && !isV2Mode && (
          <CourseDisplay
            contenu={courseData.contenu}
            moteurUtilise={courseData.moteur_utilise}
            formParams={lastFormData}
          />
        )}

        {/* Résultat V2 */}
        {pipelineV2Data && !isLoading && (
          <AgentResultView pipelineResult={pipelineV2Data} formParams={lastFormData} />
        )}

        {/* Footer placeholder */}
        {!courseData && !pipelineV2Data && !isLoading && !error && (
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

      {/* Bottom bar */}
      <footer className="fixed bottom-0 left-0 right-0 py-3 px-4 text-center"
        style={{ background: 'linear-gradient(to top, var(--bg-primary), transparent)' }}>
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
          CourseGen AI v1.0 — Propulsé par Mistral AI & Claude
        </p>
      </footer>
    </div>
  )
}

export default App
