// Variables globales
let ws = null;
let isConnected = false;
let isListening = false;
let currentTheme = 'light';
let debugVisible = false;
let stats = {
    messages: 0,
    tokens: 0,
    totalTime: 0,
    ttsEfficiency: 100
};

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    initializeWebSocket();
    loadSettings();
    updateUI();
    initializeSliders();  // Nouvelle fonction
});

// Initialiser les sliders avec mise à jour temps réel
function initializeSliders() {
    // Slider vitesse de parole
    const voiceSpeed = document.getElementById('voice-speed');
    const voiceSpeedValue = document.getElementById('voice-speed-value');
    if (voiceSpeed && voiceSpeedValue) {
        voiceSpeed.addEventListener('input', function() {
            voiceSpeedValue.textContent = this.value + 'x';
        });
    }
    
    // Slider volume
    const voiceVolume = document.getElementById('voice-volume');
    const voiceVolumeValue = document.getElementById('voice-volume-value');
    if (voiceVolume && voiceVolumeValue) {
        voiceVolume.addEventListener('input', function() {
            voiceVolumeValue.textContent = this.value + '%';
        });
    }
    
    // Slider sensibilité audio
    const audioSensitivity = document.getElementById('audio-sensitivity');
    const audioSensitivityValue = document.getElementById('audio-sensitivity-value');
    if (audioSensitivity && audioSensitivityValue) {
        audioSensitivity.addEventListener('input', function() {
            audioSensitivityValue.textContent = this.value;
        });
    }
    
    // Slider température LLM
    const llmTemperature = document.getElementById('llm-temperature');
    const llmTemperatureValue = document.getElementById('llm-temperature-value');
    if (llmTemperature && llmTemperatureValue) {
        llmTemperature.addEventListener('input', function() {
            llmTemperatureValue.textContent = this.value;
        });
    }
}

// WebSocket
function initializeWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = function() {
        isConnected = true;
        updateConnectionStatus();
        addLogEntry('Connexion WebSocket établie', 'success');
        
        // Charger immédiatement la configuration actuelle
        loadCurrentConfig();
    };
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
    
    ws.onclose = function() {
        isConnected = false;
        updateConnectionStatus();
        addLogEntry('Connexion WebSocket fermée', 'warning');
        
        // Tentative de reconnexion
        setTimeout(() => {
            if (!isConnected) {
                addLogEntry('Tentative de reconnexion...', 'info');
                initializeWebSocket();
            }
        }, 3000);
    };
    
    ws.onerror = function(error) {
        addLogEntry(`Erreur WebSocket: ${error}`, 'error');
    };
}

function handleWebSocketMessage(data) {
    switch(data.type) {
        case 'status':
            // Message de statut système (initialisation)
            if (data.personality) {
                updatePersonality(data.personality);
                // Message de bienvenue une fois initialisé
                addSystemMessage(`✅ ${data.personality} est prêt !`);
            }
            break;
            
        case 'llm_token':
            appendToCurrentResponse(data.content);
            break;
            
        case 'tts_queued':
            if (data.metadata.success) {
                addLogEntry(`TTS: Phrase ajoutée (${data.metadata.length} chars)`, 'info');
            } else {
                addLogEntry('TTS: Queue pleine, phrase ignorée', 'warning');
                updateTTSEfficiency(false);
            }
            break;
            
        case 'first_token':
            addLogEntry(`Premier token LLM: ${data.metadata.ttft.toFixed(2)}s`, 'info');
            break;
            
        case 'llm_complete':
            finishCurrentResponse();
            updateStats(data.metadata);
            break;
            
        case 'transcription':
            // 🔧 FIX: Ne plus ajouter le message ici pour éviter la duplication
            // addUserMessage(data.content);  ← SUPPRIMER CETTE LIGNE
            
            // Mettre le texte dans l'input et envoyer
            setInputValue(data.content);
            
            // Traiter automatiquement
            sendMessage();
            break;
            
        case 'listening_start':
            setListeningState(true);
            break;
            
        case 'listening_end':
            setListeningState(false);
            break;
            
        case 'config_updated':
            // Nouveau: Retour des paramètres appliqués
            if (data.success) {
                addLogEntry(`✅ ${data.message}`, 'success');
                // Recharger la config affichée
                loadCurrentSettings();
            } else {
                addLogEntry(`❌ Erreur paramètres: ${data.message}`, 'error');
            }
            break;
            
        case 'message_processing_start':
            // Nouveau: Message en cours de traitement
            startNewAssistantResponse();
            break;
            
        case 'error':
            // Logs d'erreur uniquement dans debug, pas dans conversation
            addLogEntry(`Erreur: ${data.content}`, 'error');
            break;
            
        case 'pong':
            // Keep-alive response
            break;
    }
}

//  Fonction sendMessage 
function sendMessage() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    
    if (!message || !isConnected) return;
    
    // Ajouter le message à l'interface
    addUserMessage(message);
    
    // Envoyer via WebSocket
    ws.send(JSON.stringify({
        type: 'text_message',
        content: message
    }));
    
    // Vider l'input
    input.value = '';
    
    // Statistiques
    stats.messages++;
    updateStatsDisplay();
    
    addLogEntry(`Message envoyé: ${message.substring(0, 50)}...`, 'info');
}

function toggleVoiceInput() {
    if (!isConnected) {
        addLogEntry('Connexion requise pour l\'entrée vocale', 'error');
        return;
    }
    
    if (isListening) {
        // Ne pas permettre d'arrêter manuellement - l'écoute s'arrête automatiquement
        addLogEntry('Écoute en cours, veuillez patienter...', 'info');
        return;
    } else {
        // Démarrer l'écoute
        ws.send(JSON.stringify({
            type: 'voice_input'
        }));
        
        addLogEntry('Démarrage de l\'écoute vocale', 'info');
    }
}

function setListeningState(listening) {
    isListening = listening;
    const micButton = document.getElementById('mic-button');
    const micStatus = micButton.querySelector('.mic-status');
    
    if (listening) {
        micButton.classList.add('active');
        micStatus.textContent = 'Écoute...';
    } else {
        micButton.classList.remove('active');
        micStatus.textContent = 'Parler';
    }
}

// Gestion de l'interface de conversation
function addUserMessage(content) {
    const container = document.getElementById('dialogue-container');
    const messageDiv = createMessageBubble('user', content);
    container.appendChild(messageDiv);
    scrollToBottom();
}

function addSystemMessage(content, type = 'info') {
    const container = document.getElementById('dialogue-container');
    const messageDiv = createMessageBubble('system', content);
    container.appendChild(messageDiv);
    scrollToBottom();
}

function startNewAssistantResponse() {
    const container = document.getElementById('dialogue-container');
    const messageDiv = createMessageBubble('assistant', '');
    messageDiv.id = 'current-response';
    container.appendChild(messageDiv);
    scrollToBottom();
}

function appendToCurrentResponse(token) {
    const currentResponse = document.getElementById('current-response');
    if (currentResponse) {
        const content = currentResponse.querySelector('.message-content');
        if (content) {
            content.textContent += token;
            scrollToBottom();
            
            // Compter les tokens
            stats.tokens++;
            if (stats.tokens % 10 === 0) {
                updateStatsDisplay();
            }
        }
    }
}

function finishCurrentResponse() {
    const currentResponse = document.getElementById('current-response');
    if (currentResponse) {
        currentResponse.removeAttribute('id');
        addTimeStamp(currentResponse);
        scrollToBottom();
    }
}

function createMessageBubble(type, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message-bubble ${type}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;
    
    messageDiv.appendChild(contentDiv);
    
    return messageDiv;
}

function addTimeStamp(messageDiv) {
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = new Date().toLocaleTimeString();
    messageDiv.appendChild(timeDiv);
}

function scrollToBottom() {
    const container = document.getElementById('dialogue-container');
    container.scrollTop = container.scrollHeight;
}

function clearConversation() {
    if (confirm('Effacer toute la conversation ?')) {
        const container = document.getElementById('dialogue-container');
        container.innerHTML = `
            <div class="welcome-message">
                <div class="message-bubble system">
                    <div class="message-content">
                        <p>Conversation effacée</p>
                    </div>
                </div>
            </div>
        `;
        
        addLogEntry('Conversation effacée', 'info');
    }
}

// Gestion des paramètres et modales
function openSettings() {
    const modal = document.getElementById('settings-modal');
    modal.classList.add('show');
    loadCurrentSettings();
}

function closeSettings() {
    const modal = document.getElementById('settings-modal');
    modal.classList.remove('show');
}

function showHelp() {
    const modal = document.getElementById('help-modal');
    modal.classList.add('show');
}

function closeHelp() {
    const modal = document.getElementById('help-modal');
    modal.classList.remove('show');
}

function switchSettingsTab(tabName) {
    // Cacher tous les onglets
    document.querySelectorAll('.settings-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Désactiver tous les boutons
    document.querySelectorAll('.settings-tabs .tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Activer l'onglet sélectionné
    document.getElementById(`settings-${tabName}`).classList.add('active');
    event.target.classList.add('active');
}

function switchDebugTab(tabName) {
    // Cacher tous les onglets debug
    document.querySelectorAll('.debug-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Désactiver tous les boutons
    document.querySelectorAll('.debug-tabs .tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Activer l'onglet sélectionné
    document.getElementById(`debug-${tabName}`).classList.add('active');
    event.target.classList.add('active');
}

// Gestion des thèmes
function toggleTheme() {
    const themes = ['light', 'dark', 'jarvis'];
    const currentIndex = themes.indexOf(currentTheme);
    const nextIndex = (currentIndex + 1) % themes.length;
    
    setTheme(themes[nextIndex]);
}

function setTheme(theme) {
    currentTheme = theme;
    document.body.className = `theme-${theme}`;
    
    const themeIcon = document.getElementById('theme-icon');
    const themeText = document.getElementById('theme-text');
    
    // Configuration des thèmes (facilement modifiable)
    const themeConfig = {
        'light': {
            icon: '🌙',
            text: 'Mode Sombre',  // ← Personnalisable ici
            next: 'Passer en mode sombre'
        },
        'dark': {
            icon: '🤖', 
            text: 'Mode Jarvis',  // ← Personnalisable ici
            next: 'Passer en mode Jarvis'
        },
        'jarvis': {
            icon: '☀️',
            text: 'Mode Clair',   // ← Personnalisable ici  
            next: 'Passer en mode clair'
        }
    };
    
    const config = themeConfig[theme];
    if (config) {
        themeIcon.textContent = config.icon;
        themeText.textContent = config.text;
        
        // Mettre à jour le titre du bouton pour l'accessibilité
        const themeButton = themeText.closest('.nav-btn');
        if (themeButton) {
            themeButton.title = config.next;
        }
    }
    
    saveSettings();
    addLogEntry(`Thème changé: ${config?.text || theme}`, 'info');
}

// Debug et logs
function toggleDebug() {
    debugVisible = !debugVisible;
    const debugSection = document.getElementById('debug-section');
    const mainContent = document.querySelector('.main-content');
    
    if (debugVisible) {
        debugSection.classList.remove('hidden');
        mainContent.classList.remove('debug-hidden');
    } else {
        debugSection.classList.add('hidden');
        mainContent.classList.add('debug-hidden');
    }
    
    addLogEntry(`Debug: ${debugVisible ? 'activé' : 'désactivé'}`, 'info');
}

function addLogEntry(message, type = 'info') {
    const container = document.getElementById('log-container');
    
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
    
    // Limiter le nombre de logs
    const maxLogs = 100;
    while (container.children.length > maxLogs) {
        container.removeChild(container.firstChild);
    }
    
    // Scroll automatique
    container.scrollTop = container.scrollHeight;
}

// Statistiques
function updateStats(metadata) {
    if (metadata.total_time) {
        stats.totalTime = (stats.totalTime + metadata.total_time) / 2; // Moyenne mobile
    }
    
    updateStatsDisplay();
}

function updateStatsDisplay() {
    document.getElementById('stat-messages').textContent = stats.messages;
    document.getElementById('stat-tokens').textContent = stats.tokens;
    document.getElementById('stat-avgtime').textContent = `${stats.totalTime.toFixed(1)}s`;
    document.getElementById('stat-tts-efficiency').textContent = `${stats.ttsEfficiency.toFixed(0)}%`;
}

function updateTTSEfficiency(success) {
    // Mise à jour simple de l'efficacité TTS
    if (success) {
        stats.ttsEfficiency = Math.min(100, stats.ttsEfficiency + 0.1);
    } else {
        stats.ttsEfficiency = Math.max(0, stats.ttsEfficiency - 1);
    }
}

// Configuration
function updatePersonality(personalityDisplay) {
    // Extraire le nom depuis "Assistant virtuel - Nom"
    const name = personalityDisplay.replace('Assistant virtuel - ', '');
    
    // Mettre à jour le titre de la page
    document.getElementById('page-title').textContent = `Assistant virtuel - ${name}`;
    
    // Mettre à jour le logo dans le header
    document.getElementById('assistant-name').textContent = name;
    
    // Mettre à jour l'affichage de config (si l'élément existe)
    const configElement = document.getElementById('config-personality');
    if (configElement) {
        configElement.textContent = personalityDisplay;
    }
    
    // Log du changement
    addLogEntry(`Assistant mis à jour: ${name}`, 'info');
}

function updateConnectionStatus() {
    const indicator = document.getElementById('status-indicator');
    
    if (isConnected) {
        indicator.classList.remove('offline');
        indicator.title = 'Connecté';
    } else {
        indicator.classList.add('offline');
        indicator.title = 'Déconnecté';
    }
}

// Sauvegarde/Chargement des paramètres
function saveSettings() {
    const settings = {
        theme: currentTheme,
        debugVisible: debugVisible
    };
    
    localStorage.setItem('jarvis-settings', JSON.stringify(settings));
}

function loadSettings() {
    const saved = localStorage.getItem('jarvis-settings');
    if (saved) {
        const settings = JSON.parse(saved);
        
        if (settings.theme) {
            setTheme(settings.theme);
        }
        
        if (settings.debugVisible) {
            debugVisible = settings.debugVisible;
            updateUI();
        }
    }
}

function loadCurrentConfig() {
    // Charger la config actuelle depuis l'API au démarrage
    fetch('/api/config')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.config) {
                const config = data.config;
                
                // Mettre à jour la personnalité dans l'interface
                if (config.display_name) {
                    updatePersonality(config.display_name);
                    addLogEntry(`✅ ${config.display_name} chargé`, 'success');
                } else if (config.personality) {
                    const displayName = `Assistant virtuel - ${config.personality}`;
                    updatePersonality(displayName);
                    addLogEntry(`✅ ${displayName} chargé`, 'success');
                }
                
                // Mettre à jour le thème si différent
                if (config.theme && config.theme !== currentTheme) {
                    setTheme(config.theme);
                }
                
                // Mettre à jour l'affichage de configuration
                updateConfigDisplay(config);
                
            } else {
                addLogEntry('⚠️ Config serveur non disponible', 'warning');
            }
        })
        .catch(error => {
            addLogEntry(`❌ Erreur chargement config: ${error}`, 'error');
        });
}

function loadCurrentSettings() {
    // Charger les paramètres actuels depuis le backend
    addLogEntry('Chargement paramètres depuis le serveur...', 'info');
    
    fetch('/api/config')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.config) {
                const config = data.config;
                
                // Interface
                document.getElementById('interface-theme').value = config.theme || currentTheme;
                const animationsCheckbox = document.getElementById('interface-animations');
                if (animationsCheckbox) {
                    animationsCheckbox.checked = config.interface_animations !== false;
                }
                
                // Voix et personnalité
                const personalitySelect = document.getElementById('voice-personality');
                if (personalitySelect && config.personality) {
                    personalitySelect.value = config.personality;
                }
                
                // Audio (sliders avec valeurs)
                const voiceSpeed = document.getElementById('voice-speed');
                const voiceSpeedValue = document.getElementById('voice-speed-value');
                if (voiceSpeed && config.voice_speed) {
                    voiceSpeed.value = config.voice_speed;
                    if (voiceSpeedValue) voiceSpeedValue.textContent = config.voice_speed;
                }
                
                const voiceVolume = document.getElementById('voice-volume');
                const voiceVolumeValue = document.getElementById('voice-volume-value');
                if (voiceVolume && config.voice_volume) {
                    voiceVolume.value = config.voice_volume;
                    if (voiceVolumeValue) voiceVolumeValue.textContent = config.voice_volume + '%';
                }
                
                const audioSensitivity = document.getElementById('audio-sensitivity');
                const audioSensitivityValue = document.getElementById('audio-sensitivity-value');
                if (audioSensitivity && config.audio_sensitivity) {
                    audioSensitivity.value = config.audio_sensitivity;
                    if (audioSensitivityValue) audioSensitivityValue.textContent = config.audio_sensitivity;
                }
                
                // LLM
                const llmTemperature = document.getElementById('llm-temperature');
                const llmTemperatureValue = document.getElementById('llm-temperature-value');
                if (llmTemperature && config.llm_temperature) {
                    llmTemperature.value = config.llm_temperature;
                    if (llmTemperatureValue) llmTemperatureValue.textContent = config.llm_temperature;
                }
                
                // Mettre à jour l'affichage de config
                updateConfigDisplay(config);
                
                addLogEntry('✅ Paramètres chargés depuis le serveur', 'success');
            } else {
                addLogEntry('❌ Erreur chargement config serveur', 'error');
            }
        })
        .catch(error => {
            addLogEntry(`❌ Erreur API config: ${error}`, 'error');
            console.error('Erreur chargement config:', error);
        });
}

function updateConfigDisplay(config) {
    // Affichage config dans l'interface
    const elements = {
        'config-llm': config.llm_model || 'llama3.1:8b',
        'config-tts': config.tts_model || 'edge-tts', 
        'config-personality': config.display_name || config.personality || 'Samantha',
        'config-audio': config.device_index !== null ? `Device ${config.device_index}` : 'Auto',
        'config-theme': config.theme || 'light'
    };
    
    // Mettre à jour les éléments qui existent
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
    
    // Mettre à jour la personnalité dans le header si disponible
    if (config.display_name) {
        updatePersonality(config.display_name);
    }
}

function saveSettings() {
    // Récupérer tous les paramètres du modal
    const newConfig = {
        personality: document.getElementById('voice-personality').value,
        theme: document.getElementById('interface-theme').value,
        voice_speed: parseFloat(document.getElementById('voice-speed').value),
        voice_volume: parseInt(document.getElementById('voice-volume').value),
        audio_sensitivity: parseInt(document.getElementById('audio-sensitivity').value),
        llm_temperature: parseFloat(document.getElementById('llm-temperature').value),
        interface_animations: document.getElementById('interface-animations').checked
    };
    
    // Envoyer via WebSocket pour application immédiate
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'config_update',
            config: newConfig
        }));
        
        addLogEntry('Paramètres envoyés pour application', 'info');
        closeSettings();
    } else {
        addLogEntry('Connexion WebSocket requise', 'error');
    }
}

function testMicrophone() {
    if (!isConnected) {
        addLogEntry('Connexion WebSocket requise', 'error');
        alert('Veuillez d\'abord vous connecter à Jarvis');
        return;
    }
    
    // Informer l'utilisateur
    addLogEntry('🎤 Test du microphone: parlez maintenant...', 'info');
    
    // Créer un message de test dans l'interface
    const testMessageDiv = document.createElement('div');
    testMessageDiv.className = 'message-bubble system';
    testMessageDiv.id = 'mic-test-message';
    testMessageDiv.innerHTML = `
        <div class="message-content">
            <p>🎤 Test du microphone en cours...</p>
            <p style="font-size: 0.9em; opacity: 0.8;">Parlez maintenant pour tester votre micro</p>
        </div>
    `;
    
    const container = document.getElementById('dialogue-container');
    container.appendChild(testMessageDiv);
    scrollToBottom();
    
    // Lancer l'écoute vocale
    ws.send(JSON.stringify({
        type: 'voice_input'
    }));
    
    // Après 5 secondes, mettre à jour le message si aucune transcription
    setTimeout(() => {
        const testMsg = document.getElementById('mic-test-message');
        if (testMsg) {
            testMsg.innerHTML = `
                <div class="message-content">
                    <p>✅ Test terminé</p>
                    <p style="font-size: 0.9em; opacity: 0.8;">Si vous voyez votre transcription ci-dessus, votre micro fonctionne !</p>
                </div>
            `;
        }
    }, 5000);
}

// Fonction testVoice corrigée pour vraiment tester la voix
function testVoice() {
    const personality = document.getElementById('voice-personality').value;
    const speed = document.getElementById('voice-speed').value;
    const volume = document.getElementById('voice-volume').value;
    
    addLogEntry(`🎤 Test voix: ${personality} (vitesse: ${speed}, volume: ${volume}%)`, 'info');
    
    // Envoyer un message de test via WebSocket
    if (ws && ws.readyState === WebSocket.OPEN) {
        // Message de test personnalisé selon la personnalité
        let testMessages = {
            'Jarvis': "Bonjour, je suis Jarvis, votre assistant personnel. Comment puis-je vous aider aujourd'hui?",
            'Samantha': "Bonjour, je m'appelle Samantha. Je suis ravie de vous rencontrer. Comment allez-vous?",
            'Eloise': "Salut ! Je suis Eloise, ton assistante. Prête à t'aider avec enthousiasme !",
            'Josephine': "Bonjour, Josephine à votre service. N'hésitez pas à me solliciter."
        };
        
        const testMessage = testMessages[personality] || testMessages['Samantha'];
        
        // D'abord appliquer temporairement les paramètres pour le test
        ws.send(JSON.stringify({
            type: 'config_update',
            config: {
                personality: personality,
                voice_speed: parseFloat(speed),
                voice_volume: parseInt(volume)
            }
        }));
        
        // Puis envoyer le message de test après un court délai
        setTimeout(() => {
            ws.send(JSON.stringify({
                type: 'text_message',
                content: testMessage
            }));
        }, 500);
        
    } else {
        addLogEntry('❌ WebSocket non connecté pour le test', 'error');
    }
}

function applySettings() {
    // Appliquer les paramètres sans fermer la modale
    const newConfig = {
        personality: document.getElementById('voice-personality').value,
        theme: document.getElementById('interface-theme').value,
        voice_speed: parseFloat(document.getElementById('voice-speed').value),
        voice_volume: parseInt(document.getElementById('voice-volume').value),
        audio_sensitivity: parseInt(document.getElementById('audio-sensitivity').value),
        llm_temperature: parseFloat(document.getElementById('llm-temperature').value),
        interface_animations: document.getElementById('interface-animations').checked
    };
    
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'config_update',
            config: newConfig
        }));
        
        addLogEntry('✅ Paramètres appliqués', 'success');
        
        // Mettre à jour le thème immédiatement dans l'interface
        if (newConfig.theme !== currentTheme) {
            setTheme(newConfig.theme);
        }
        
    } else {
        addLogEntry('❌ WebSocket non connecté', 'error');
    }
}

function resetSettings() {
    if (confirm('Réinitialiser tous les paramètres ?')) {
        localStorage.removeItem('jarvis-settings');
        setTheme('light');
        debugVisible = false;
        updateUI();
        addLogEntry('Paramètres réinitialisés', 'info');
    }
}

// Fonctions de test
function testVoice() {
    if (!isConnected) {
        alert('Connexion requise');
        return;
    }
    
    const testText = "Ceci est un test de la voix.";
    addLogEntry('Test de la voix...', 'info');
    
    // Envoyer un message de test
    ws.send(JSON.stringify({
        type: 'text_message',
        content: testText
    }));
}

function testMicrophone() {
    addLogEntry('Test du microphone...', 'info');
    toggleVoiceInput();
}

// Fonctions utilitaires
function handleInputKeydown(event) {
    if (event.ctrlKey && event.key === 'Enter') {
        event.preventDefault();
        sendMessage();
    }
}

function setInputValue(value) {
    document.getElementById('message-input').value = value;
}

function exportConversation() {
    const messages = document.querySelectorAll('.message-bubble:not(.system)');
    let exportText = `Conversation Jarvis - ${new Date().toLocaleString()}\n\n`;
    
    messages.forEach(msg => {
        const type = msg.classList.contains('user') ? 'Vous' : 'Jarvis';
        const content = msg.querySelector('.message-content').textContent;
        const time = msg.querySelector('.message-time')?.textContent || '';
        
        exportText += `[${time}] ${type}: ${content}\n\n`;
    });
    
    // Télécharger le fichier
    const blob = new Blob([exportText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversation-jarvis-${new Date().toISOString().split('T')[0]}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    
    addLogEntry('Conversation exportée', 'success');
}

function updateUI() {
    const debugSection = document.getElementById('debug-section');
    const mainContent = document.querySelector('.main-content');
    
    if (debugVisible) {
        debugSection.classList.remove('hidden');
        mainContent.classList.remove('debug-hidden');
    } else {
        debugSection.classList.add('hidden');
        mainContent.classList.add('debug-hidden');
    }
    
    updateConnectionStatus();
    updateStatsDisplay();
}

// Keep-alive
setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }));
    }
}, 30000);