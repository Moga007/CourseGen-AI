/**
 * Constantes des événements SSE émis par le backend (pipeline V2).
 * Centralise les noms d'événements pour éviter les erreurs de frappe silencieuses.
 */

export const SSE_EVENTS = Object.freeze({
  // Pipeline cours V2
  AGENT_START:       'agent_start',
  AGENT_SKIPPED:     'agent_skipped',
  AGENT_SUCCESS:     'agent_success',
  AGENT_ERROR:       'agent_error',
  PIPELINE_COMPLETE: 'pipeline_complete',
  FATAL_ERROR:       'fatal_error',

  // Pipeline quiz V2
  QUIZ_COMPLETE:     'quiz_complete',
})
