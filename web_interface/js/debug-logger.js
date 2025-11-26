/**
 * debug-logger.js - Gestion du debug et des logs
 * 🔍 Système de surveillance - Monitoring et diagnostic
 */

/**
 * Bascule l'affichage du panneau de debug
 */
function toggleDebug() {
    debugVisible = !debugVisible;
    updateDebugVisibility();
    
    addLogEntry(`🔍 Debug: ${debugVisible ? 'activé' : 'désactivé'}`, 'info');
    saveSettings();
}

/**
 * Met à jour la visibilité du panneau de debug
 */
function updateDebugVisibility() {
    const debugSection = document.getElementById('debug-section');
    const mainContent = document.querySelector('.main-content');
    
    if (!debugSection || !mainContent) return;
    
    if (debugVisible) {
        debugSection.classList.remove('hidden');
        mainContent.classList.remove('debug-hidden');
    } else {
        debugSection.classList.add('hidden');
        mainContent.classList.add('debug-hidden');
    }
}

/**
 * Change d'onglet dans le panneau de debug
 * @param {string} tabName - Nom de l'onglet (logs, stats, config)
 * @param {Event} event - Événement du clic
 */
function switchDebugTab(tabName, event) {
    // Masquer tous les onglets debug
    document.querySelectorAll('.debug-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Désactiver tous les boutons
    document.querySelectorAll('.debug-tabs .tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Activer l'onglet et le bouton sélectionnés
    const targetTab = document.getElementById(`debug-${tabName}`);
    if (targetTab) {
        targetTab.classList.add('active');
        interfaceState.currentDebugTab = tabName;
    }
    
    if (event && event.target) {
        event.target.classList.add('active');
    }
    
    // Mettre à jour le contenu selon l'onglet
    switch (tabName) {
        case 'stats':
            updateStatsDisplay();
            break;
        case 'config':
            updateDebugConfigDisplay();
            break;
    }
}

/**
 * Ajoute une entrée au log
 * @param {string} message - Message du log
 * @param {string} type - Type de log (info, success, warning, error)
 */
function addLogEntry(message, type = 'info') {
    const container = document.getElementById('log-container');
    if (!container) return;
    
    const logDiv = document.createElement('div');
    logDiv.className = `log-entry ${type}`;
    
    const timeSpan = document.createElement('span');
    timeSpan.className = 'log-time';
    timeSpan.textContent = new Date().toLocaleTimeString();
    
    const messageSpan = document.createElement('span');
    messageSpan.className = 'log-message';
    messageSpan.textContent = message;
    
    logDiv.appendChild(timeSpan);
    logDiv.appendChild(messageSpan);
    container.appendChild(logDiv);
    
    // Appel au nettoyage pour limiter le nombre de logs
    cleanupLogs();
    
    // Scroll automatique vers le bas
    container.scrollTop = container.scrollHeight;
    
    // Émettre un événement pour les autres modules
    document.dispatchEvent(new CustomEvent('logAdded', {
        detail: { message, type, timestamp: new Date() }
    }));
}

/**
 * Nettoie les anciens logs du DOM pour éviter les surcharges mémoire
 */
function cleanupLogs() {
    const container = document.getElementById('log-container');
    if (!container) return;

    const maxLogs = 100; // Garde les 100 logs les plus récents
    while (container.children.length > maxLogs) {
        container.removeChild(container.firstChild);
    }
}

/**
 * Met à jour l'affichage de configuration dans le debug
 */
function updateDebugConfigDisplay() {
    // Cette fonction sera appelée quand on ouvre l'onglet config
    const elements = {
        'config-personality': 'Chargement...',
        'config-llm': 'Chargement...',
        'config-tts': 'Chargement...',
        'config-audio': 'Chargement...'
    };
    
    // Mettre à jour immédiatement avec les valeurs par défaut
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
    
    // Puis charger les vraies valeurs
    loadCurrentConfig().then(config => {
        if (config) {
            updateConfigDisplay(config);
        }
    });
}

/**
 * Exporte tous les logs en fichier
 */
function exportLogs() {
    const logEntries = document.querySelectorAll('.log-entry');
    if (logEntries.length === 0) {
        addLogEntry('⚠️ Aucun log à exporter', 'warning');
        return;
    }
    
    let logText = `Logs Jarvis - ${new Date().toLocaleString()}\n`;
    logText += `================================\n\n`;
    
    logEntries.forEach(entry => {
        const time = entry.querySelector('.log-time')?.textContent || '';
        const message = entry.querySelector('.log-message')?.textContent || '';
        const type = entry.className.split(' ').find(cls => cls !== 'log-entry') || 'info';
        
        logText += `[${time}] ${type.toUpperCase()}: ${message}\n`;
    });
    
    logText += `\n\nInformations système:\n`;
    logText += `- Thème actuel: ${currentTheme}\n`;
    logText += `- Voice visible: ${voiceVisible}\n`;
    logText += `- Camera visible: ${cameraVisible}\n`;
    logText += `- Debug visible: ${debugVisible}\n`;
    logText += `- Connexion WebSocket: ${isConnected ? 'Connectée' : 'Déconnectée'}\n`;
    logText += `- Messages: ${stats.messages}\n`;
    logText += `- Tokens: ${stats.tokens}\n`;
    
    // Créer et télécharger le fichier
    const blob = new Blob([logText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `jarvis-logs-${new Date().toISOString().split('T')[0]}.txt`;
    a.style.display = 'none';
    
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    URL.revokeObjectURL(url);
    
    addLogEntry('💾 Logs exportés', 'success');
}

/**
 * Efface tous les logs
 */
function clearLogs() {
    if (!confirm('Effacer tous les logs ?')) return;
    
    const container = document.getElementById('log-container');
    if (container) {
        container.innerHTML = `
            <div class="log-entry info">
                <span class="log-time">${new Date().toLocaleTimeString()}</span>
                <span class="log-message">Logs effacés</span>
            </div>
        `;
    }
    
    addLogEntry('🗑️ Logs précédents effacés', 'info');
}

/**
 * Filtre les logs par type
 * @param {string} filterType - Type de filtre (all, info, success, warning, error)
 */
function filterLogs(filterType) {
    const logEntries = document.querySelectorAll('.log-entry');
    
    logEntries.forEach(entry => {
        if (filterType === 'all' || entry.classList.contains(filterType)) {
            entry.style.display = 'flex';
        } else {
            entry.style.display = 'none';
        }
    });
    
    addLogEntry(`🔍 Filtrage logs: ${filterType}`, 'info');
}

/**
 * Génère un rapport de diagnostic
 */
function generateDiagnosticReport() {
    const report = {
        timestamp: new Date().toISOString(),
        jarvis: {
            version: "0.5.0", // À adapter selon votre versioning
            theme: currentTheme,
            voiceVisible: voiceVisible,
            cameraVisible: cameraVisible,
            debugVisible: debugVisible,
            connection: isConnected
        },
        stats: { ...stats },
        configuration: {
            hasThemes: !!(config.themes && Object.keys(config.themes).length > 0),
            hasVoices: !!(config.voices && Object.keys(config.voices).length > 0),
            hasModels: !!(config.models && Object.keys(config.models).length > 0),
            hasBackgrounds: !!(config.backgrounds && Object.keys(config.backgrounds).length > 0)
        },
        interface: {
            settingsModalOpen: interfaceState.settingsModalOpen,
            helpModalOpen: interfaceState.helpModalOpen,
            currentSettingsTab: interfaceState.currentSettingsTab,
            currentDebugTab: interfaceState.currentDebugTab
        },
        browser: {
            userAgent: navigator.userAgent,
            language: navigator.language,
            platform: navigator.platform,
            cookieEnabled: navigator.cookieEnabled,
            onLine: navigator.onLine
        }
    };
    
    return report;
}

/**
 * Exporte un rapport de diagnostic complet
 */
function exportDiagnosticReport() {
    const report = generateDiagnosticReport();
    
    const reportText = JSON.stringify(report, null, 2);
    
    const blob = new Blob([reportText], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `jarvis-diagnostic-${new Date().toISOString().split('T')[0]}.json`;
    a.style.display = 'none';
    
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    URL.revokeObjectURL(url);
    
    addLogEntry('🔧 Rapport de diagnostic exporté', 'success');
}

/**
 * Active/désactive le mode debug avancé
 */
function toggleAdvancedDebug() {
    const isAdvanced = localStorage.getItem('jarvis-advanced-debug') === 'true';
    const newState = !isAdvanced;
    
    localStorage.setItem('jarvis-advanced-debug', newState.toString());
    
    if (newState) {
        // Activer le debug avancé
        window.JarvisDebug = {
            config,
            stats,
            interfaceState,
            generateReport: generateDiagnosticReport,
            clearConfig: () => { config = { themes: {}, voices: {}, backgrounds: {}, models: {} }; },
            forceReconnect: initializeWebSocket
        };
        
        addLogEntry('🔧 Mode debug avancé activé (window.JarvisDebug disponible)', 'success');
    } else {
        // Désactiver le debug avancé
        if (window.JarvisDebug) {
            delete window.JarvisDebug;
        }
        
        addLogEntry('🔧 Mode debug avancé désactivé', 'info');
    }
}

/**
 * Crée des boutons de contrôle pour les logs
 */
function createLogControls() {
    const debugHeader = document.querySelector('.debug-header');
    if (!debugHeader) return;
    
    // Vérifier si les contrôles existent déjà
    if (debugHeader.querySelector('.log-controls')) return;
    
    const controlsDiv = document.createElement('div');
    controlsDiv.className = 'log-controls';
    controlsDiv.style.display = 'flex';
    controlsDiv.style.gap = '0.5rem';
    controlsDiv.style.alignItems = 'center';
    
    // Bouton export logs
    const exportBtn = document.createElement('button');
    exportBtn.textContent = '💾';
    exportBtn.title = 'Exporter les logs';
    exportBtn.className = 'control-btn';
    exportBtn.addEventListener('click', exportLogs);
    
    // Bouton clear logs
    const clearBtn = document.createElement('button');
    clearBtn.textContent = '🗑️';
    clearBtn.title = 'Effacer les logs';
    clearBtn.className = 'control-btn';
    clearBtn.addEventListener('click', clearLogs);
    
    // Bouton diagnostic
    const diagnosticBtn = document.createElement('button');
    diagnosticBtn.textContent = '🔧';
    diagnosticBtn.title = 'Export diagnostic';
    diagnosticBtn.className = 'control-btn';
    diagnosticBtn.addEventListener('click', exportDiagnosticReport);
    
    controlsDiv.appendChild(exportBtn);
    controlsDiv.appendChild(clearBtn);
    controlsDiv.appendChild(diagnosticBtn);
    
    // Insérer avant le bouton de fermeture
    const closeBtn = debugHeader.querySelector('.close-debug');
    if (closeBtn) {
        debugHeader.insertBefore(controlsDiv, closeBtn);
    } else {
        debugHeader.appendChild(controlsDiv);
    }
}

/**
 * Initialise les événements du debug
 */
function initializeDebugEvents() {
    // Bouton toggle debug principal
    const debugButton = document.querySelector('[onclick="toggleDebug()"]');
    if (debugButton) {
        debugButton.removeAttribute('onclick');
        debugButton.addEventListener('click', toggleDebug);
    }
    
    // Bouton fermeture debug
    const closeDebugButton = document.querySelector('.close-debug');
    if (closeDebugButton) {
        closeDebugButton.addEventListener('click', toggleDebug);
    }
    
    // Onglets debug
    document.querySelectorAll('.debug-tabs .tab-btn').forEach((button, index) => {
        const tabNames = ['logs', 'stats', 'config'];
        const tabName = tabNames[index];
        if (tabName) {
            button.addEventListener('click', (event) => switchDebugTab(tabName, event));
        }
    });
    
    // Raccourci clavier pour toggle debug (F12 ou Ctrl+D)
    document.addEventListener('keydown', function(event) {
        if  (event.ctrlKey && event.key === 'd') {
            event.preventDefault();
            toggleDebug();
        }
    });
    
    // Créer les contrôles de logs
    createLogControls();
    
    // Vérifier si le debug avancé était activé
    if (localStorage.getItem('jarvis-advanced-debug') === 'true') {
        toggleAdvancedDebug();
    }
}

/**
 * Initialise l'état du debug au démarrage
 */
function initializeState() {
    // Charger l'état du debug depuis les paramètres sauvegardés
    const savedSettings = loadSavedSettings();
    if (savedSettings && typeof savedSettings.voiceVisible === 'boolean') {
        voiceVisible = savedSettings.voiceVisible;
    }
    
    if (savedSettings && typeof savedSettings.cameraVisible === 'boolean') {
        cameraVisible = savedSettings.cameraVisible;
    }
    
    if (savedSettings && typeof savedSettings.debugVisible === 'boolean') {
        debugVisible = savedSettings.debugVisible;
    }
    
    if (typeof initVoices === 'function') {
        initVoices();
    }
    updateCameraVisibility();
    updateDebugVisibility();
}

// Initialiser les événements et l'état dès que le DOM est prêt
document.addEventListener('DOMContentLoaded', function() {
    initializeDebugEvents();
    initializeState();
});

// Log de démarrage
addLogEntry('🔍 Système de debug initialisé', 'info');