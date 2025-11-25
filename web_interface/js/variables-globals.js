/**
 * variables-globals.js - Variables globales et état de l'application Jarvis
 * 🧠 Cortex Préfrontal - État central de l'application
 */

// État de connexion
let ws = null;
let isConnected = false;
let isListening = false;

// Configuration interface
let currentTheme = 'light';
let cameraVisible = false;
let voiceVisible = false;
let currentVoiceId = 0;
let debugVisible = false;

// Statistiques de session
let stats = {
    messages: 0,
    tokens: 0,
    totalTime: 0,
    ttsEfficiency: 100
};

// Configuration chargée depuis les fichiers JSON
let config = {
    themes: {},
    voices: {},
    backgrounds: {},
    models: {}
};

// État de l'interface
let interfaceState = {
    settingsModalOpen: false,
    helpModalOpen: false,
    currentSettingsTab: 'voice',
    currentDebugTab: 'logs'
};

/**
 * Réinitialise les statistiques de session
 */
function resetStats() {
    stats = {
        messages: 0,
        tokens: 0,
        totalTime: 0,
        ttsEfficiency: 100
    };
}

/**
 * Met à jour les statistiques
 * @param {Object} metadata - Métadonnées de performance
 */
function updateStats(metadata) {
    if (metadata.total_time) {
        stats.totalTime = (stats.totalTime + metadata.total_time) / 2; // Moyenne mobile
    }
    if (metadata.token_count) {
        stats.tokens += metadata.token_count;
    }
    updateStatsDisplay();
}

/**
 * Met à jour l'affichage des statistiques
 */
function updateStatsDisplay() {
    const elements = {
        'stat-messages': stats.messages,
        'stat-tokens': stats.tokens,
        'stat-avgtime': `${stats.totalTime.toFixed(1)}s`,
        'stat-tts-efficiency': `${stats.ttsEfficiency.toFixed(0)}%`
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    });
}

/**
 * Met à jour l'efficacité TTS
 * @param {boolean} success - Succès de l'opération TTS
 */
function updateTTSEfficiency(success) {
    if (success) {
        stats.ttsEfficiency = Math.min(100, stats.ttsEfficiency + 0.1);
    } else {
        stats.ttsEfficiency = Math.max(0, stats.ttsEfficiency - 1);
    }
}

// Export des variables pour les autres modules (si utilisation de modules ES6)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ws, isConnected, isListening, currentTheme, cameraVisible, voiceVisible, debugVisible,
        stats, config, interfaceState, currentVoiceId, 
        resetStats, updateStats, updateStatsDisplay, updateTTSEfficiency
    };
}