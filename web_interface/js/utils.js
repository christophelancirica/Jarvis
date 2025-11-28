/**
 * utils.js - Fonctions utilitaires
 * 🛠️ Boîte à outils - Fonctions partagées et helpers
 */

/**
 * Sauvegarde les paramètres dans le localStorage
 */
function saveSettings() {
    const settings = {
        theme: currentTheme,
        voiceVisible: voiceVisible,
        cameraVisible: cameraVisible,
        debugVisible: debugVisible,
        lastSave: new Date().toISOString()
    };
    
    try {
        localStorage.setItem('jarvis-settings', JSON.stringify(settings));
    } catch (error) {
        addLogEntry(`⚠️ Erreur sauvegarde paramètres: ${error.message}`, 'warning');
    }
}

/**
 * Charge les paramètres depuis le localStorage
 * @returns {Object|null} Paramètres chargés ou null
 */
function loadSavedSettings() {
    try {
        const saved = localStorage.getItem('jarvis-settings');
        return saved ? JSON.parse(saved) : null;
    } catch (error) {
        addLogEntry(`⚠️ Erreur chargement paramètres: ${error.message}`, 'warning');
        return null;
    }
}

/**
 * Charge les paramètres sauvegardés et les applique
 */
function loadSettings() {
    const saved = localStorage.getItem('jarvis-settings');
    if (saved) {
        try {
            const settings = JSON.parse(saved);
            if (settings.theme) {
                setTheme(settings.theme);
            }
            voiceVisible = settings.voiceVisible || false;
            cameraVisible = settings.cameraVisible || false;
            debugVisible = settings.debugVisible || false;
        } catch (error) {
            addLogEntry(`⚠️ Erreur chargement paramètres: ${error.message}`, 'warning');
        }
    }
    
    // Charger l'arrière-plan sauvegardé
    loadSavedBackground();
}

/**
 * Met à jour l'interface utilisateur globale
 */
function updateUI() {
    updateDebugVisibility();
    updateConnectionStatus();
    updateStatsDisplay();
    updateThemeButton();
    if (typeof initVoices === 'function') {
        initVoices();
    }
}

/**
 * Formatte une durée en secondes en format lisible
 * @param {number} seconds - Durée en secondes
 * @returns {string} Durée formatée
 */
function formatDuration(seconds) {
    if (seconds < 1) {
        return `${(seconds * 1000).toFixed(0)}ms`;
    } else if (seconds < 60) {
        return `${seconds.toFixed(1)}s`;
    } else {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = (seconds % 60).toFixed(1);
        return `${minutes}m ${remainingSeconds}s`;
    }
}

/**
 * Formatte un nombre de tokens
 * @param {number} tokens - Nombre de tokens
 * @returns {string} Nombre formaté
 */
function formatTokenCount(tokens) {
    if (tokens < 1000) {
        return tokens.toString();
    } else if (tokens < 1000000) {
        return `${(tokens / 1000).toFixed(1)}K`;
    } else {
        return `${(tokens / 1000000).toFixed(1)}M`;
    }
}

/**
 * Génère un ID unique
 * @returns {string} ID unique
 */
function generateUniqueId() {
    return `jarvis-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Débounce une fonction
 * @param {Function} func - Fonction à débouncer
 * @param {number} wait - Délai en millisecondes
 * @returns {Function} Fonction debouncée
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttle une fonction
 * @param {Function} func - Fonction à throttler
 * @param {number} limit - Limite en millisecondes
 * @returns {Function} Fonction throttlée
 */
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Vérifie si un élément est visible dans le viewport
 * @param {HTMLElement} element - Élément à vérifier
 * @returns {boolean} True si visible
 */
function isElementVisible(element) {
    if (!element) return false;
    
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

/**
 * Copie du texte dans le presse-papiers
 * @param {string} text - Texte à copier
 * @returns {Promise<boolean>} Promise de succès
 */
async function copyToClipboard(text) {
    try {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(text);
            return true;
        } else {
            // Fallback pour les navigateurs plus anciens
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            
            const success = document.execCommand('copy');
            textArea.remove();
            return success;
        }
    } catch (error) {
        console.error('Erreur copie presse-papiers:', error);
        return false;
    }
}

/**
 * Valide une adresse email
 * @param {string} email - Email à valider
 * @returns {boolean} True si valide
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Valide une URL
 * @param {string} url - URL à valider
 * @returns {boolean} True si valide
 */
function isValidUrl(url) {
    try {
        new URL(url);
        return true;
    } catch {
        return false;
    }
}

/**
 * Nettoie une chaîne de caractères
 * @param {string} str - Chaîne à nettoyer
 * @returns {string} Chaîne nettoyée
 */
function sanitizeString(str) {
    if (typeof str !== 'string') return '';
    
    return str
        .trim()
        .replace(/[<>]/g, '') // Supprimer les caractères HTML de base
        .replace(/\s+/g, ' '); // Réduire les espaces multiples
}

/**
 * Formate une taille de fichier
 * @param {number} bytes - Taille en bytes
 * @returns {string} Taille formatée
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

/**
 * Obtient les informations sur le navigateur
 * @returns {Object} Informations navigateur
 */
function getBrowserInfo() {
    const ua = navigator.userAgent;
    
    let browser = 'Unknown';
    let version = 'Unknown';
    
    if (ua.indexOf('Firefox') > -1) {
        browser = 'Firefox';
        version = ua.match(/Firefox\/(\d+)/)?.[1] || 'Unknown';
    } else if (ua.indexOf('Chrome') > -1) {
        browser = 'Chrome';
        version = ua.match(/Chrome\/(\d+)/)?.[1] || 'Unknown';
    } else if (ua.indexOf('Safari') > -1) {
        browser = 'Safari';
        version = ua.match(/Version\/(\d+)/)?.[1] || 'Unknown';
    } else if (ua.indexOf('Edge') > -1) {
        browser = 'Edge';
        version = ua.match(/Edge\/(\d+)/)?.[1] || 'Unknown';
    }
    
    return {
        browser,
        version,
        userAgent: ua,
        language: navigator.language,
        platform: navigator.platform,
        cookieEnabled: navigator.cookieEnabled,
        onLine: navigator.onLine
    };
}

/**
 * Vérifie si le navigateur supporte une fonctionnalité
 * @param {string} feature - Nom de la fonctionnalité
 * @returns {boolean} True si supportée
 */
function supportsFeature(feature) {
    switch (feature) {
        case 'websockets':
            return 'WebSocket' in window;
        case 'localstorage':
            return 'localStorage' in window;
        case 'clipboard':
            return 'clipboard' in navigator;
        case 'notifications':
            return 'Notification' in window;
        case 'speechrecognition':
            return 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window;
        case 'speechsynthesis':
            return 'speechSynthesis' in window;
        default:
            return false;
    }
}

/**
 * Gère les erreurs globalement
 * @param {Error} error - Erreur à traiter
 * @param {string} context - Contexte de l'erreur
 */
function handleError(error, context = 'Application') {
    const errorMessage = `${context}: ${error.message}`;
    
    addLogEntry(errorMessage, 'error');
    console.error(`[${context}]`, error);
    
    // Optionnel: Envoyer l'erreur à un service de monitoring
    // sendErrorToMonitoring(error, context);
}

/**
 * Crée un élément DOM avec des attributs
 * @param {string} tag - Tag HTML
 * @param {Object} attributes - Attributs de l'élément
 * @param {string} textContent - Contenu texte
 * @returns {HTMLElement} Élément créé
 */
function createElement(tag, attributes = {}, textContent = '') {
    const element = document.createElement(tag);
    
    Object.entries(attributes).forEach(([key, value]) => {
        if (key === 'className') {
            element.className = value;
        } else if (key === 'style' && typeof value === 'object') {
            Object.assign(element.style, value);
        } else {
            element.setAttribute(key, value);
        }
    });
    
    if (textContent) {
        element.textContent = textContent;
    }
    
    return element;
}

/**
 * Affiche une notification toast
 * @param {string} message - Message à afficher
 * @param {string} type - Type (success, warning, error, info)
 * @param {number} duration - Durée en ms
 */
function showToast(message, type = 'info', duration = 3000) {
    // Créer le conteneur de toasts s'il n'existe pas
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = createElement('div', {
            id: 'toast-container',
            style: {
                position: 'fixed',
                top: '20px',
                right: '20px',
                zIndex: '10000',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px'
            }
        });
        document.body.appendChild(toastContainer);
    }
    
    // Créer le toast
    const toast = createElement('div', {
        className: `toast toast-${type}`,
        style: {
            padding: '12px 16px',
            borderRadius: '8px',
            color: 'white',
            fontWeight: '500',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            transform: 'translateX(100%)',
            transition: 'transform 0.3s ease',
            maxWidth: '300px',
            backgroundColor: type === 'success' ? '#10b981' :
                           type === 'warning' ? '#f59e0b' :
                           type === 'error' ? '#ef4444' : '#3b82f6'
        }
    }, message);
    
    toastContainer.appendChild(toast);
    
    // Animation d'entrée
    setTimeout(() => {
        toast.style.transform = 'translateX(0)';
    }, 10);
    
    // Suppression automatique
    setTimeout(() => {
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, duration);
}

/**
 * Gestionnaire d'erreurs globales
 */
window.addEventListener('error', function(event) {
    handleError(event.error, 'Global Error');
});

window.addEventListener('unhandledrejection', function(event) {
    handleError(new Error(event.reason), 'Unhandled Promise');
});

/**
 * Récupère la config actuelle du serveur
 */
async function getCurrentServerConfig() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Erreur récupération config serveur:', error);
        addLogEntry('❌ Impossible de charger la configuration du serveur.', 'error');
        return null;
    }
}

// Export des fonctions pour utilisation dans d'autres modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        saveSettings, loadSavedSettings, loadSettings, updateUI,
        formatDuration, formatTokenCount, generateUniqueId,
        debounce, throttle, isElementVisible, copyToClipboard,
        isValidEmail, isValidUrl, sanitizeString, formatFileSize,
        getBrowserInfo, supportsFeature, handleError, createElement, showToast,
        getCurrentServerConfig
    };
}