import { useState } from 'react'
import axios from 'axios'
import Header from './components/Header'
import CourseForm from './components/CourseForm'
import CourseDisplay from './components/CourseDisplay'
import LoadingSpinner from './components/LoadingSpinner'
import HistorySection from './components/HistorySection'

const API_URL = 'http://localhost:8000'

function App() {
  const [courseData, setCourseData] = useState(null)
  const [lastFormData, setLastFormData] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [replayData, setReplayData] = useState(null)

  const handleGenerate = async (formData) => {
    setIsLoading(true)
    setError(null)
    setCourseData(null)
    setLastFormData(formData)

    try {
      const response = await axios.post(`${API_URL}/generate`, formData, {
        timeout: 720000, // 12 minutes max (contenu enrichi + continuations automatiques)
      })
      setCourseData(response.data)
      // Rafraîchir l'historique
      if (window.__refreshHistorique) window.__refreshHistorique()
    } catch (err) {
      if (err.response) {
        // Server responded with error
        setError(err.response.data.detail || 'Une erreur est survenue lors de la génération.')
      } else if (err.code === 'ECONNABORTED') {
        setError('La requête a expiré. Veuillez réessayer.')
      } else if (err.code === 'ERR_NETWORK') {
        setError('Impossible de contacter le serveur. Vérifiez que le backend est lancé (python main.py).')
      } else {
        setError('Une erreur inattendue est survenue. Veuillez réessayer.')
      }
    } finally {
      setIsLoading(false)
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
        <CourseForm onSubmit={handleGenerate} isLoading={isLoading} initialData={replayData} />

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

        {/* Loading */}
        {isLoading && (
          <div className="glass-card">
            <LoadingSpinner moteur={lastFormData?.moteur} />
          </div>
        )}

        {/* Course Result */}
        {courseData && !isLoading && (
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
        <HistorySection onReplay={handleReplay} />
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
