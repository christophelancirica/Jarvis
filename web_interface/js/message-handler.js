/**
 * message-handler.js - Gestion des messages et de la conversation
 * 💬 Lobes Temporaux - Traitement du langage et communication
 * 🚀 OPTIMISÉ: DocumentFragment + Batching pour streaming performance
 */

// 🚀 Variables d'optimisation streaming
let tokenBuffer = '';
let bufferFlushTimer = null;
const BATCH_SIZE = 5;          // Flush tous les 5 caractères
const BATCH_TIMEOUT = 100;     // Ou tous les 100ms minimum
const SCROLL_THRESHOLD = 50;   // Seuil pour auto-scroll

/**
 * Envoie un message utilisateur
 */
function sendMessage() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();

    if (!message) {
        addLogEntry('⚠️ Message vide ignoré', 'warning');
        return;
    }
    
    console.log('📝 Envoi message:', message); 
    
    if (!isConnected) {
        addLogEntry('❌ Connexion requise pour envoyer un message', 'error');
        return;
    }
    
    // Ajouter le message à l'interface
    addUserMessage(message);
    
    // Envoyer via WebSocket
    if (sendTextMessage(message)) {
        // Vider l'input seulement si l'envoi réussit
        input.value = '';
        
        // Mettre à jour les statistiques
        stats.messages++;
        updateStatsDisplay();
        
        addLogEntry(`📤 Message envoyé: ${message.substring(0, 50)}${message.length > 50 ? '...' : ''}`, 'info');
    }
}

/**
 * Gère l'entrée vocale
 */
function toggleVoiceInput() {
    if (!isConnected) {
        addLogEntry('❌ Connexion requise pour l\'entrée vocale', 'error');
        return;
    }
    
    if (isListening) {
        addLogEntry('👂 Écoute en cours, veuillez patienter...', 'info');
        return;
    }
    
    // Démarrer l'écoute
    if (requestVoiceInput()) {
        addLogEntry('🎤 Démarrage de l\'écoute vocale', 'info');
    }
}

/**
 * Met à jour l'état d'écoute dans l'interface
 * @param {boolean} listening - État d'écoute
 */
function setListeningState(listening) {
    isListening = listening;
    const micButton = document.getElementById('mic-button');
    const micStatus = micButton?.querySelector('.mic-status');
    
    if (!micButton || !micStatus) return;
    
    if (listening) {
        micButton.classList.add('active');
        micStatus.textContent = 'Écoute...';
    } else {
        micButton.classList.remove('active');
        micStatus.textContent = 'Parler';
    }
}

/**
 * Ajoute un message utilisateur à la conversation
 * @param {string} content - Contenu du message
 */
function addUserMessage(content) {
    const container = document.getElementById('dialogue-container');
    if (!container) return;
    
    const messageDiv = createMessageBubble('user', content);
    container.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Ajoute un message système à la conversation
 * @param {string} content - Contenu du message
 * @param {string} type - Type de message (info, success, warning, error)
 */
function addSystemMessage(content, type = 'info') {
    const container = document.getElementById('dialogue-container');
    if (!container) return;
    
    const messageDiv = createMessageBubble('system', content);
    
    // Ajouter une classe pour le type si nécessaire
    if (type !== 'info') {
        messageDiv.classList.add(`system-${type}`);
    }
    
    container.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Démarre une nouvelle réponse de l'assistant
 */
function startNewAssistantResponse() {
    // Reset du buffer si nécessaire
    resetTokenBuffer();
    
    const container = document.getElementById('dialogue-container');
    if (!container) return;
    
    const messageDiv = createMessageBubble('assistant', '');
    messageDiv.id = 'current-response';
    container.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * 🚀 OPTIMISÉ - Ajoute du contenu à la réponse actuelle (streaming avec batching)
 * @param {string} token - Token à ajouter
 */
function appendToCurrentResponse(token) {
    // Accumuler dans le buffer
    tokenBuffer += token;
    
    // Flush immédiat si:
    // - Buffer dépasse la taille limite
    // - Token contient un saut de ligne (fin de phrase/paragraphe)
    // - Token contient de la ponctuation forte (. ! ?)
    if (tokenBuffer.length >= BATCH_SIZE || 
        token.includes('\n') || 
        /[.!?]/.test(token)) {
        flushTokenBuffer();
        return;
    }
    
    // Flush différé pour optimiser les petits tokens
    if (bufferFlushTimer) clearTimeout(bufferFlushTimer);
    bufferFlushTimer = setTimeout(flushTokenBuffer, BATCH_TIMEOUT);
}

/**
 * 🚀 OPTIMISÉ - Applique le buffer accumulé au DOM (batch update)
 */
function flushTokenBuffer() {
    if (!tokenBuffer) return;
    
    const currentResponse = document.getElementById('current-response');
    if (!currentResponse) {
        resetTokenBuffer();
        return;
    }
    
    const content = currentResponse.querySelector('.message-content');
    if (content) {
        // Mise à jour DOM en une seule fois (évite multiple reflows)
        content.textContent += tokenBuffer;
        
        // Scroll intelligent - seulement si l'utilisateur suit la conversation
        smartScrollToBottom();
    }
    
    // Reset buffer
    resetTokenBuffer();
}

/**
 * 🚀 OPTIMISÉ - Scroll intelligent qui évite les interruptions utilisateur
 */
function smartScrollToBottom() {
    const container = document.getElementById('dialogue-container');
    if (!container) return;
    
    // Vérifier si l'utilisateur est proche du bas (suit la conversation)
    const isNearBottom = container.scrollTop >= 
        container.scrollHeight - container.clientHeight - SCROLL_THRESHOLD;
    
    // Scroller seulement si l'utilisateur suit activement
    if (isNearBottom) {
        container.scrollTop = container.scrollHeight;
    }
}

/**
 * Reset du buffer de tokens
 */
function resetTokenBuffer() {
    tokenBuffer = '';
    if (bufferFlushTimer) {
        clearTimeout(bufferFlushTimer);
        bufferFlushTimer = null;
    }
}

/**
 * Finalise la réponse actuelle
 */
function finishCurrentResponse() {
    // Flush final du buffer pour éviter les tokens perdus
    flushTokenBuffer();
    
    const currentResponse = document.getElementById('current-response');
    if (!currentResponse) return;
    
    currentResponse.removeAttribute('id');
    addTimeStamp(currentResponse);
    scrollToBottom(); // Scroll final pour s'assurer de la visibilité complète
}

/**
 * Crée une bulle de message
 * @param {string} type - Type de message (user, assistant, system)
 * @param {string} content - Contenu du message
 * @returns {HTMLElement} Élément de message
 */
function createMessageBubble(type, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message-bubble ${type}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;
    
    messageDiv.appendChild(contentDiv);
    
    return messageDiv;
}

/**
 * Ajoute un timestamp à un message
 * @param {HTMLElement} messageDiv - Élément de message
 */
function addTimeStamp(messageDiv) {
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = new Date().toLocaleTimeString();
    messageDiv.appendChild(timeDiv);
}

/**
 * Fait défiler la conversation vers le bas (fallback classique)
 */
function scrollToBottom() {
    const container = document.getElementById('dialogue-container');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

/**
 * Efface la conversation
 */
function clearConversation() {
    // Reset du buffer avant effacement
    resetTokenBuffer();
    
    if (!confirm('Effacer toute la conversation ?')) return;
    
    const container = document.getElementById('dialogue-container');
    if (!container) return;
    
    container.innerHTML = `
        <div class="welcome-message">
            <div class="message-bubble system">
                <div class="message-content">
                    <p>🗑️ Conversation effacée</p>
                </div>
            </div>
        </div>
    `;
    
    // Réinitialiser les statistiques
    resetStats();
    updateStatsDisplay();
    
    addLogEntry('🗑️ Conversation effacée', 'info');
}

/**
 * Exporte la conversation en fichier texte
 */
function exportConversation() {
    // Flush final avant export pour s'assurer que tout est visible
    flushTokenBuffer();
    
    const messages = document.querySelectorAll('.message-bubble:not(.system)');
    if (messages.length === 0) {
        addLogEntry('⚠️ Aucun message à exporter', 'warning');
        return;
    }
    
    let exportText = `Conversation Jarvis - ${new Date().toLocaleString()}\n`;
    exportText += `================================\n\n`;
    
    messages.forEach(msg => {
        const type = msg.classList.contains('user') ? 'Vous' : 'Assistant';
        const content = msg.querySelector('.message-content')?.textContent || '';
        const time = msg.querySelector('.message-time')?.textContent || '';
        
        exportText += `[${time}] ${type}:\n${content}\n\n`;
    });
    
    exportText += `\nStatistiques de session:\n`;
    exportText += `- Messages: ${stats.messages}\n`;
    exportText += `- Tokens: ${stats.tokens}\n`;
    exportText += `- Temps moyen: ${stats.totalTime.toFixed(1)}s\n`;
    
    // Créer et télécharger le fichier
    const blob = new Blob([exportText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversation-jarvis-${new Date().toISOString().split('T')[0]}.txt`;
    a.style.display = 'none';
    
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    URL.revokeObjectURL(url);
    
    addLogEntry('💾 Conversation exportée', 'success');
}

/**
 * Met à jour la personnalité affichée
 * @param {string} personalityDisplay - Nom d'affichage de la personnalité
 */
function updatePersonality(personalityDisplay) {
    // Extraire le nom depuis "Assistant virtuel - Nom"
    const name = personalityDisplay.replace('Assistant virtuel - ', '');
    
    // Mettre à jour le titre de la page
    const assistantName = document.getElementById('assistant-name');
    if (assistantName) {
        assistantName.textContent = personalityDisplay;
    }
    
    // Mettre à jour l'affichage de config
    const configElement = document.getElementById('config-personality');
    if (configElement) {
        configElement.textContent = personalityDisplay;
    }
    
    // Mettre à jour le titre de la page
    document.title = `${name} - Assistant Vocal`;
    
    addLogEntry(`👤 Assistant mis à jour: ${name}`, 'info');
}

/**
 * Définit la valeur de l'input de message
 * @param {string} value - Valeur à définir
 */
function setInputValue(value) {
    const input = document.getElementById('message-input');
    if (input) {
        input.value = value;
    }
}

/**
 * Gère les raccourcis clavier pour l'input
 * @param {KeyboardEvent} event - Événement clavier
 */
function handleInputKeydown(event) {
    if (event.ctrlKey && event.key === 'Enter') {
        event.preventDefault();
        sendMessage();
    } 
}

/**
 * Auto-resize du textarea
 * @param {HTMLTextAreaElement} textarea - Élément textarea
 */
function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

/**
 * Initialise les événements des messages
 */
function initializeMessageEvents() {
    // Bouton d'envoi
    //const sendButton = document.getElementById('send-button');
    //if (sendButton) {
    //    sendButton.addEventListener('click', sendMessage);
    //}
    
    // Bouton microphone
    const micButton = document.getElementById('mic-button');
    if (micButton) {
        micButton.addEventListener('click', toggleVoiceInput);
    }
    
    // Input de message
    const messageInput = document.getElementById('message-input');
    if (messageInput) {
        messageInput.addEventListener('keydown', handleInputKeydown);
        
        // Auto-resize du textarea
        messageInput.addEventListener('input', function() {
            autoResizeTextarea(this);
        });
    }
    
    // Boutons de contrôle de conversation
    const clearButton = document.querySelector('[onclick="clearConversation()"]');
    if (clearButton) {
        clearButton.removeAttribute('onclick');
        clearButton.addEventListener('click', clearConversation);
    }
    
    const exportButton = document.querySelector('[onclick="exportConversation()"]');
    if (exportButton) {
        exportButton.removeAttribute('onclick');
        exportButton.addEventListener('click', exportConversation);
    }
}

// Initialiser les événements dès que le DOM est prêt
document.addEventListener('DOMContentLoaded', initializeMessageEvents);

// Raccourcis clavier globaux
document.addEventListener('keydown', function(event) {
    // Microphone avec Ctrl+M
    if (event.ctrlKey && event.key === 'm') {
        event.preventDefault();
        toggleVoiceInput();
    }
});

// 🚀 Nettoyage automatique en cas de changement de page
window.addEventListener('beforeunload', function() {
    resetTokenBuffer();
});