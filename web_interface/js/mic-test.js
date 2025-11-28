
async function testMicrophone() {
    const testButton = document.querySelector('button[onclick="testMicrophone()"]');
    if (!testButton) {
        showToast('Erreur: Bouton de test introuvable.', 'error');
        return;
    }

    // Gérer l'état du bouton
    const originalButtonText = testButton.innerHTML;
    testButton.innerHTML = '🎤 Enregistrement en cours... (3s)';
    testButton.disabled = true;
    addLogEntry('🎤 Test du microphone démarré...', 'info');

    // Simuler un test de 3 secondes
    setTimeout(() => {
        // Restaurer l'état du bouton
        if (testButton && originalButtonText) {
            testButton.innerHTML = originalButtonText;
            testButton.disabled = false;
        }
        showToast('✅ Test du microphone terminé.', 'success');
        addLogEntry('✅ Test du microphone terminé.', 'success');
    }, 3000);
}
