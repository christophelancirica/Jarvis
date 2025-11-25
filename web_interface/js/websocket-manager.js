/**
 * websocket-manager.js - Gestion de la communication WebSocket
 * 🔌 Thalamus - Centre de communication et routage des messages
 * 🚀 OPTIMISÉ: Map routing O(1) au lieu de switch O(n)
 */

// 🚀 Map de routage optimisé (initialisation unique)
const messageRoutes = new Map();

// 📊 Métriques de performance WebSocket
let routingMetrics = {
    totalMessages: 0,
    routingTimeSum: 0,
    unknownTypes: 0,
    mostFrequent: new Map()
};

/**
 * 🚀 Initialise le Map de routage (performance O(1))
 */
function initializeMessageRoutes() {
    // Handlers ordonnés par fréquence (d'après tes logs: llm_token = le plus fréquent)
    messageRoutes.set('llm_token', handleLLMToken);
    messageRoutes.set('tts_queued', handleTTSQueued);
    messageRoutes.set('first_token', handleFirstToken);
    messageRoutes.set('llm_complete', handleLLMComplete);
    messageRoutes.set('transcription', handleTranscription);
    messageRoutes.set('status', handleStatusMessage);
    messageRoutes.set('listening_start', handleListeningStart);
    messageRoutes.set('listening_end', handleListeningEnd);
    messageRoutes.set('config_updated', handleConfigUpdated);
    messageRoutes.set('message_processing_start', () => startNewAssistantResponse());
    messageRoutes.set('error', (data) => addLogEntry(`❌ Erreur: ${data.content}`, 'error'));
    messageRoutes.set('pong', () => { /* Keep-alive response - rien à faire */ });
    
    addLogEntry('🚀 Map routing initialisé (11 routes)', 'info');
}

/**
 * Initialise la connexion WebSocket
 */
function initializeWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    addLogEntry(`🔌 Connexion WebSocket: ${wsUrl}`, 'info');
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = handleWebSocketOpen;
    ws.onmessage = handleWebSocketMessage;
    ws.onclose = handleWebSocketClose;
    ws.onerror = handleWebSocketError;
}

/**
 * Gère l'ouverture de la connexion WebSocket
 */
function handleWebSocketOpen() {
    isConnected = true;
    updateConnectionStatus();
    addLogEntry('✅ Connexion WebSocket établie', 'success');
    
    // Charger la configuration actuelle depuis le serveur
    loadCurrentConfig();
    
    // Émettre un événement de connexion
    document.dispatchEvent(new CustomEvent('websocketConnected'));
}

/**
 * Gère les messages reçus via WebSocket
 * @param {MessageEvent} event - Événement message WebSocket
 */
function handleWebSocketMessage(event) {
    try {
        const data = JSON.parse(event.data);
        routeWebSocketMessage(data);
    } catch (error) {
        addLogEntry(`❌ Erreur parsing message WebSocket: ${error.message}`, 'error');
    }
}

/**
 * 🚀 OPTIMISÉ - Route les messages WebSocket avec Map O(1)
 * @param {Object} data - Données du message
 */
function routeWebSocketMessage(data) {
    const startTime = performance.now();
    
    // Métriques
    routingMetrics.totalMessages++;
    const count = routingMetrics.mostFrequent.get(data.type) || 0;
    routingMetrics.mostFrequent.set(data.type, count + 1);
    
    // 🚀 Routage O(1) avec Map
    const handler = messageRoutes.get(data.type);
    
    if (handler) {
        // Exécution directe du handler
        handler(data);
    } else {
        // Type inconnu
        routingMetrics.unknownTypes++;
        addLogEntry(`⚠️ Type de message WebSocket inconnu: ${data.type}`, 'warning');
    }
    
    // Métriques de performance
    const routingTime = performance.now() - startTime;
    routingMetrics.routingTimeSum += routingTime;
    
    // Log périodique des performances (tous les 100 messages)
    if (routingMetrics.totalMessages % 100 === 0) {
        logRoutingMetrics();
    }
}

/**
 * 📊 Affiche les métriques de routage
 */
function logRoutingMetrics() {
    const avgTime = (routingMetrics.routingTimeSum / routingMetrics.totalMessages).toFixed(3);
    const top3 = [...routingMetrics.mostFrequent.entries()]
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([type, count]) => `${type}:${count}`)
        .join(', ');
    
    addLogEntry(`📊 Routing: ${routingMetrics.totalMessages} msgs, ${avgTime}ms avg, top: ${top3}`, 'info');
}

/**
 * Gère les messages de statut
 * @param {Object} data - Données du message
 */
function handleStatusMessage(data) {
    if (data.personality) {
        updatePersonality(data.personality);
        addSystemMessage(`✅ ${data.personality} est prêt !`);
    }
    
    if (data.content) {
        addSystemMessage(data.content);
    }
}

/**
 * Gère les tokens LLM en streaming
 * @param {Object} data - Données du token
 */
function handleLLMToken(data) {
    appendToCurrentResponse(data.content);
    
    // Mettre à jour les stats en temps réel
    stats.tokens++;
    if (stats.tokens % 10 === 0) {
        updateStatsDisplay();
    }
}

/**
 * Gère les événements TTS
 * @param {Object} data - Données TTS
 */
function handleTTSQueued(data) {
    if (data.metadata?.success) {
        addLogEntry(`🔊 TTS: Phrase ajoutée (${data.metadata.length} chars)`, 'info');
        updateTTSEfficiency(true);
    } else {
        addLogEntry('⚠️ TTS: Queue pleine, phrase ignorée', 'warning');
        updateTTSEfficiency(false);
    }
}

/**
 * Gère le premier token (Time To First Token)
 * @param {Object} data - Données du premier token
 */
function handleFirstToken(data) {
    if (data.metadata?.ttft) {
        addLogEntry(`⚡ Premier token LLM: ${data.metadata.ttft.toFixed(2)}s`, 'info');
    }
}

/**
 * Gère la fin de génération LLM
 * @param {Object} data - Données de fin de génération
 */
function handleLLMComplete(data) {
    finishCurrentResponse();
    
    if (data.metadata) {
        updateStats(data.metadata);
        
        // Log des performances
        const { total_time, token_count, tokens_per_second } = data.metadata;
        if (total_time && token_count) {
            addLogEntry(`📊 Génération: ${token_count} tokens en ${total_time.toFixed(2)}s (${tokens_per_second?.toFixed(1) || 'N/A'} tok/s)`, 'info');
        }
    }
}

/**
 * Gère les transcriptions vocales
 * @param {Object} data - Données de transcription
 */
function handleTranscription(data) {
    const testMessage = document.getElementById('mic-test-message');
    
    if (testMessage) {
        // Mode test microphone
        testMessage.innerHTML = `
            <div class="message-content">
                <p>✅ Test réussi : "${data.content}"</p>
                <p style="font-size: 0.9em; opacity: 0.8;">Votre micro fonctionne parfaitement !</p>
            </div>
        `;
        addLogEntry(`🎤 Test micro OK: ${data.content}`, 'success');
    } else {
        addUserMessage(data.content);
        addLogEntry(`🎤 Transcription: ${data.content}`, 'info');
    }
}

/**
 * Gère le début d'écoute
 */
function handleListeningStart() {
    setListeningState(true);
    addLogEntry('👂 Écoute vocale démarrée', 'info');
}

/**
 * Gère la fin d'écoute
 */
function handleListeningEnd() {
    setListeningState(false);
    addLogEntry('🔇 Écoute vocale arrêtée', 'info');
}

/**
 * Gère les confirmations de mise à jour de config
 * @param {Object} data - Données de confirmation
 */
function handleConfigUpdated(data) {
    console.log('🔍 [DEBUG] Confirmation reçue:', data);
    
    if (data.success) {
        addLogEntry(`✅ ${data.message}`, 'success');
    } else {
        addLogEntry(`❌ Erreur paramètres: ${data.message}`, 'error');
    }
}

/**
 * Gère la fermeture de la connexion WebSocket
 */
function handleWebSocketClose() {
    isConnected = false;
    updateConnectionStatus();
    addLogEntry('🔌 Connexion WebSocket fermée', 'warning');
    
    // Émettre un événement de déconnexion
    document.dispatchEvent(new CustomEvent('websocketDisconnected'));
    
    // Tentative de reconnexion après 3 secondes
    setTimeout(() => {
        if (!isConnected) {
            addLogEntry('🔄 Tentative de reconnexion...', 'info');
            initializeWebSocket();
        }
    }, 3000);
}

/**
 * Gère les erreurs WebSocket
 * @param {Event} error - Événement d'erreur
 */
function handleWebSocketError(error) {
    addLogEntry(`❌ Erreur WebSocket: ${error.message || 'Erreur inconnue'}`, 'error');
    console.error('Erreur WebSocket:', error);
}

/**
 * Envoie un message via WebSocket
 * @param {Object} message - Message à envoyer
 * @returns {boolean} Succès de l'envoi
 */
function sendWebSocketMessage(message) {
    console.log('📤 [WS] Envoi message:', message); 
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        addLogEntry('❌ WebSocket non connecté', 'error');
        return false;
    }
    
    try {
        ws.send(JSON.stringify(message));
        return true;
    } catch (error) {
        addLogEntry(`❌ Erreur envoi WebSocket: ${error.message}`, 'error');
        return false;
    }
}

/**
 * Envoie un message texte
 * @param {string} content - Contenu du message
 */
function sendTextMessage(content) {
    return sendWebSocketMessage({
        type: 'text_message',
        text: content
    });
}

/**
 * Lance l'écoute vocale
 */
function requestVoiceInput() {
    return sendWebSocketMessage({
        type: 'voice_input'
    });
}

/**
 * Met à jour la configuration
 * @param {Object} config - Nouvelle configuration
 */
function updateServerConfig(config) {
    return sendWebSocketMessage({
        type: 'config_update',
        config: config
    });
}

/**
 * Met à jour l'indicateur de statut de connexion
 */
function updateConnectionStatus() {
    const indicator = document.getElementById('status-indicator');
    
    if (!indicator) return;
    
    if (isConnected) {
        indicator.classList.remove('offline');
        indicator.title = 'Connecté';
    } else {
        indicator.classList.add('offline');
        indicator.title = 'Déconnecté';
    }
}

/**
 * Démarre le système de keep-alive
 */
function startKeepAlive() {
    setInterval(() => {
        if (isConnected) {
            sendWebSocketMessage({ type: 'ping' });
        }
    }, 30000); // Ping toutes les 30 secondes
}

/**
 * 🚀 Retourne les métriques de routage actuelles
 */
function getRoutingMetrics() {
    return {
        ...routingMetrics,
        avgRoutingTime: routingMetrics.totalMessages > 0 
            ? (routingMetrics.routingTimeSum / routingMetrics.totalMessages).toFixed(3)
            : 0
    };
}

/**
 * 🚀 Reset des métriques (pour tests de performance)
 */
function resetRoutingMetrics() {
    routingMetrics = {
        totalMessages: 0,
        routingTimeSum: 0,
        unknownTypes: 0,
        mostFrequent: new Map()
    };
    addLogEntry('📊 Métriques routing reset', 'info');
}

// Initialiser le routing et le keep-alive dès le chargement
document.addEventListener('DOMContentLoaded', () => {
    initializeMessageRoutes();
    startKeepAlive();
});