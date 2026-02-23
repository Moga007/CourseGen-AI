export default function LoadingSpinner() {
    return (
        <div className="loading-container">
            <div className="loading-spinner"></div>
            <div>
                <p className="loading-text text-center font-medium">
                    Génération du cours en cours
                    <span className="loading-dots"></span>
                </p>
                <p className="text-center text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
                    Recherche web et rédaction — cela peut prendre jusqu'à 30 secondes
                </p>
            </div>
        </div>
    )
}
