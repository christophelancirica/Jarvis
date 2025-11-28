/**
 * app-main.js - Initialisation principale et coordination
 * 🧠 Tronc Cérébral - Fonctions vitales et coordination générale
 */

async function initializeJarvis() {
    addLogEntry('🚀 Démarrage de Jarvis unifié...', 'info');
    
    try {
        // 1. Vérifier les prérequis navigateur
        if (!checkBrowserCompatibility()) {
            return false;
        }
        
        // 2. 🚀 NOUVEAU: Initialiser la configuration unifiée
        const configLoaded = await initializeConfig();
        
        if (!configLoaded) {
            addLogEntry('⚠️ Utilisation de la configuration par défaut', 'warning');
        } else {
            addLogEntry('✅ Configuration unifiée chargée', 'success');
        }
        
        // 3. Initialiser les modules dans l'ordre logique
        await initializeModules();
        
        // 4. Établir la connexion WebSocket
        addLogEntry('🔌 Établissement de la connexion...', 'info');
        initializeWebSocket();
        
        // 5. 🚀 SUPPRIMÉ: Plus de loadSettings() - déjà fait par initializeConfig()
        
        // 6. Initialiser l'interface utilisateur
        await updateUI();
        
        // 7. Démarrer les services de fond
        startBackgroundServices();
        
        addLogEntry('✅ Jarvis unifié initialisé avec succès !', 'success');
        showToast('🤖 Jarvis est prêt !', 'success');
        
        return true;
        
    } catch (error) {
        handleError(error, 'Initialisation Jarvis');
        addLogEntry('❌ Échec de l\'initialisation', 'error');
        showToast('❌ Erreur d\'initialisation', 'error');
        return false;
    }
}

/**
 * 🚀 NOUVEAU: Initialisation de la configuration unifiée
 */
async function initializeConfig() {
    try {
        addLogEntry('🎯 Initialisation configuration unifiée...', 'info');
        
        // Charger la configuration depuis l'API REST unifiée
        const response = await fetch('/api/config');
        const data = await response.json();

        if (data && typeof data === 'object' && !data.error && Object.keys(data).length > 0) {
            // Stocker la config dans une variable globale pour accÃ¨s rapide
            window.jarvisConfig = data;
            
            addLogEntry('📄 Configuration unifiée chargée depuis le serveur', 'success');
            return true;
        } else {
            addLogEntry('❌ Erreur chargement configuration serveur', 'error');
            return false;
        }
        
    } catch (error) {
        addLogEntry(`❌ Erreur init config unifiée: ${error.message}`, 'error');
        return false;
    }
}

/**
 * 🚀 NOUVEAU: Application immédiate de la config interface
 */
async function applyInterfaceConfigFromServer(interfaceConfig) {
    try {
        // Appliquer le thème
        if (interfaceConfig.theme) {
            currentTheme = interfaceConfig.theme;
            document.body.className = `theme-${interfaceConfig.theme}`;
            updateThemeButton();
            addLogEntry(`🎨 Thème appliqué: ${interfaceConfig.theme}`, 'info');
        }
        
        // Appliquer le background
        if (interfaceConfig.background && interfaceConfig.background !== 'default') {
            await applyBackgroundFromConfig(interfaceConfig.background);
        }
        
        // Appliquer l'opacité du background
        if (interfaceConfig.background_opacity !== undefined) {
            await applyBackgroundOpacityFromConfig(interfaceConfig.background_opacity);
        }
        
        // Appliquer la visibilité des panneaux
        if (interfaceConfig.panels) {
            voiceVisible = interfaceConfig.panels.voice_lab_visible || false;
            cameraVisible = interfaceConfig.panels.camera_visible || false;
            debugVisible = interfaceConfig.panels.debug_visible || false;
            
            updateVoiceVisibility();
            updateCameraVisibility();
            updateDebugVisibility();
        }
        
    } catch (error) {
        addLogEntry(`⚠️ Erreur application config interface: ${error.message}`, 'warning');
    }
}

async function applyBackgroundFromConfig(backgroundPath) {
    const dialogueContainer = document.getElementById('dialogue-container');
    if (!dialogueContainer) return;
    
    const dialogueSection = dialogueContainer.closest('.dialogue-section');
    if (!dialogueSection) return;
    
    let imagePath = backgroundPath.startsWith('images/') ? 
        `static/${backgroundPath}` : `static/images/${backgroundPath}`;
    
    dialogueSection.style.setProperty('--bg-image-url', `url('${imagePath}')`);
    dialogueSection.classList.add('bg-image');
    
    addLogEntry(`🖼️ Background appliqué: ${backgroundPath}`, 'info');
}

async function applyBackgroundOpacityFromConfig(opacity) {
    const style = document.createElement('style');
    style.id = 'background-opacity-config';
    
    const existing = document.getElementById('background-opacity-config');
    if (existing) existing.remove();
    
    style.textContent = `
        .dialogue-section.bg-image::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background-image: var(--bg-image-url);
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            opacity: ${opacity / 100};
            z-index: 1;
            pointer-events: none;
            border-radius: inherit;
        }
    `;
    
    document.head.appendChild(style);
    addLogEntry(`🎨 Opacité background: ${opacity}%`, 'info');
}

/**
 * 🚀 MODIFIÉ: Initialisation des modules avec config unifiée
 */
async function initializeModules() {
    try {
        addLogEntry('🔧 Initialisation des modules...', 'info');
        
        // Charger la configuration des thèmes en premier
        if (typeof loadThemesConfig === 'function') {
            await loadThemesConfig();
        }

        // ✅ Initialisation du gestionnaire de voix
        if (typeof initVoices === 'function') {
            await initVoices();
            addLogEntry('🎤 Module voix initialisé', 'info');
        }
        
        // ✅ Charger les listes
        await loadVoicesFromAPI();
        await loadRolesFromAPI();
        await loadBackgroundsFromAPI();
        await loadModelsFromAPI();
        await loadAudioDevicesFromAPI();
        
        // ✅ Visibilité des panneaux
        updateVoiceVisibility();
        updateCameraVisibility(); 
        updateDebugVisibility();
        
        addLogEntry('✅ Modules unifiés initialisés', 'success');
        
    } catch (error) {
        addLogEntry(`❌ Erreur init modules: ${error.message}`, 'error');
        throw error;
    }
}

/**
 * 🚀 NOUVEAU: Chargement des voix depuis l'API unifiée
 */
async function loadVoicesFromAPI() {
    try {
        const response = await fetch('/api/voice/all/list');
        const data = await response.json();
        
        if (data.success) {
            // Peupler le select des voix
            await populateVoiceSelectFromAPI(data.voices, data.cloned_voices);
            addLogEntry(`🎤 ${Object.keys(data.voices || {}).length} voix standard + ${Object.keys(data.cloned_voices || {}).length} clonées`, 'info');
        }
    } catch (error) {
        addLogEntry(`❌ Erreur chargement voix API: ${error.message}`, 'error');
    }
}

async function populateVoiceSelectFromAPI(standardVoices, clonedVoices) {
    const voiceSelect = document.getElementById('voice-personality');
    if (!voiceSelect) return;

    voiceSelect.innerHTML = '';
    
    const categories = {
        'edge-tts': { label: 'Edge-TTS', element: document.createElement('optgroup'), voices: [] },
        'coqui-tts': { label: 'Coqui/Local', element: document.createElement('optgroup'), voices: [] },
        'cloned': { label: '🎭 Voix clonées', element: document.createElement('optgroup'), voices: [] }
    };

    // Catégoriser les voix standard
    if (standardVoices) {
        Object.entries(standardVoices).forEach(([id, voice]) => {
            const model = voice.model || 'coqui-tts'; // Fallback pour les anciens formats
            if (model.includes('edge')) {
                categories['edge-tts'].voices.push({ id, voice });
            } else {
                categories['coqui-tts'].voices.push({ id, voice });
            }
        });
    }

    // Ajouter les voix clonées
    if (clonedVoices) {
        Object.entries(clonedVoices).forEach(([id, voice]) => {
            if (voice.processing_status === 'ready') {
                categories['cloned'].voices.push({ id, voice });
            }
        });
    }

    // Construire les optgroups
    for (const key in categories) {
        const category = categories[key];
        if (category.voices.length > 0) {
            category.element.label = category.label;
            category.voices.forEach(({ id, voice }) => {
                const option = document.createElement('option');
                option.value = id;
                let indicators = '';
                if (voice.model === 'edge-tts' || voice.model === 'piper') {
                    indicators = ' 🟢⚡'; // Streaming | Vitesse native
                } else if (voice.model === 'gtts') {
                    indicators = ' 🟠🐌'; // Différé | Vitesse simulée
                } else if (voice.model === 'xtts-v2') {
                    indicators = ' 🟠💎'; // Différé | Haute Qualité
                }
                option.textContent = (voice.display_name || voice.name) + indicators;
                category.element.appendChild(option);
            });
            voiceSelect.appendChild(category.element);
        }
    }

    // Sélectionner la voix actuelle depuis la config
    if (window.jarvisConfig?.voice?.personality) {
        voiceSelect.value = window.jarvisConfig.voice.personality;
    }
}

/**
 * 🚀 NOUVEAU: Chargement des rôles depuis l'API
 */
async function loadRolesFromAPI() {
    try {
        const response = await fetch('config/roles.json');
        const data = await response.json();
        
        const roleSelect = document.getElementById('role-select');
        if (roleSelect && data.roles) {
            roleSelect.innerHTML = '';
            Object.values(data.roles).forEach(role => {
                const option = document.createElement('option');
                option.value = role.id;
                option.textContent = role.name;
                roleSelect.appendChild(option);
            });
            
            // Sélectionner le rôle actuel
            if (window.jarvisConfig?.llm?.role) {
                roleSelect.value = window.jarvisConfig.llm.role;
            }
            
            addLogEntry(`👨‍🏫 ${Object.keys(data.roles).length} rôles chargés`, 'info');
        }
    } catch (error) {
        addLogEntry(`❌ Erreur chargement rôles: ${error.message}`, 'error');
    }
}

/**
 * 🚀 NOUVEAU: Chargement des modèles depuis l'API
 */
async function loadModelsFromAPI() {
    try {
        const response = await fetch('/api/models');
        const data = await response.json();
        
        const modelSelect = document.getElementById('llm-model');
        if (modelSelect && data.success && data.models) {
            modelSelect.innerHTML = '';
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                modelSelect.appendChild(option);
            });
            
            // Sélectionner le modèle actuel
            if (window.jarvisConfig?.llm?.model) {
                modelSelect.value = window.jarvisConfig.llm.model;
            }
            
            addLogEntry(`🧠 ${data.models.length} modèles LLM chargés`, 'info');
        }
    } catch (error) {
        addLogEntry(`❌ Erreur chargement modèles: ${error.message}`, 'error');
    }
}

/**
 * 🚀 NOUVEAU: Chargement des backgrounds depuis l'API
 */
async function loadBackgroundsFromAPI() {
    try {
        const response = await fetch('/api/backgrounds');
        const data = await response.json();
        
        const backgroundSelect = document.getElementById('interface-background');
        if (backgroundSelect && data.success && data.backgrounds) {
            backgroundSelect.innerHTML = '';
            
            data.backgrounds.forEach(bg => {
                const option = document.createElement('option');
                option.value = bg.path;
                option.textContent = bg.name;
                backgroundSelect.appendChild(option);
            });
            
            // Sélectionner le background actuel
            if (window.jarvisConfig?.interface?.background) {
                backgroundSelect.value = window.jarvisConfig.interface.background;
            }
            
            addLogEntry(`🖼️ ${data.backgrounds.length} arrière-plans chargés`, 'info');
        }
    } catch (error) {
        addLogEntry(`❌ Erreur chargement backgrounds: ${error.message}`, 'error');
    }
}

/**
 * Charge la liste des périphériques audio depuis l'API et peuple le sélecteur.
 */
async function loadAudioDevicesFromAPI() {
    try {
        const response = await fetch('/api/audio/devices');
        const data = await response.json();

        const deviceSelect = document.getElementById('audio-device');
        if (deviceSelect && data.success && data.devices) {
            deviceSelect.innerHTML = ''; // Vide les options existantes

            if (data.devices.length === 0) {
                const option = document.createElement('option');
                option.value = "";
                option.textContent = "Aucun microphone trouvé";
                option.disabled = true;
                deviceSelect.appendChild(option);
            } else {
                data.devices.forEach(device => {
                    const option = document.createElement('option');
                    option.value = device.index;
                    option.textContent = device.name;
                    deviceSelect.appendChild(option);
                });
            }

            // Pré-sélectionner le périphérique sauvegardé si disponible
            if (window.jarvisConfig?.audio?.input?.device_index) {
                deviceSelect.value = window.jarvisConfig.audio.input.device_index;
            }

            addLogEntry(`🎤 ${data.devices.length} microphones chargés`, 'info');
        } else if (!data.success) {
            throw new Error(data.error || 'Réponse invalide du serveur');
        }
    } catch (error) {
        addLogEntry(`❌ Erreur chargement des périphériques audio : ${error.message}`, 'error');
        const deviceSelect = document.getElementById('audio-device');
        if (deviceSelect) {
            deviceSelect.innerHTML = '<option value="">Erreur de chargement</option>';
        }
    }
}

/**
 * 🚀 MODIFIÉ: Mise à jour de l'interface avec config unifiée
 */
async function updateUI() {
    try {
        addLogEntry('🎨 Mise à jour interface unifiée...', 'info');

        // Initialiser l'état 'muet'
        if (window.jarvisConfig?.audio?.output?.muted !== undefined) {
            isMuted = window.jarvisConfig.audio.output.muted;
        }
        updateMuteButton();

        // Appliquer la configuration de l'interface maintenant que les thèmes sont chargés
        if (window.jarvisConfig?.interface) {
            await applyInterfaceConfigFromServer(window.jarvisConfig.interface);
        }
        
        // Mettre à jour les informations de configuration affichées
        if (window.jarvisConfig) {
            updateConfigDisplay(window.jarvisConfig);
        }
        
        // Initialiser les sliders avec les valeurs de la config
        initializeSlidersFromConfig();
        
        // Mettre à jour les sélecteurs avec les valeurs actuelles
        updateSelectorsFromConfig();
        
        addLogEntry('✅ Interface unifiée mise à jour', 'success');
        
    } catch (error) {
        addLogEntry(`❌ Erreur mise à jour UI: ${error.message}`, 'error');
    }
}

function updateConfigDisplay(config) {
    // Mettre à jour l'affichage de la config dans le debug panel si présent
    const configElements = {
        'config-personality': config.voice?.personality || 'Non défini',
        'config-llm': config.llm?.model || 'Non défini',
        'config-tts': config.voice?.tts_model || 'Non défini'
    };
    
    Object.entries(configElements).forEach(([elementId, value]) => {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    });
}

function initializeSlidersFromConfig() {
    if (!window.jarvisConfig) return;
    
    const sliderMappings = [
        { id: 'voice-speed', value: window.jarvisConfig.audio?.output?.speed || 1.0, suffix: 'x' },
        { id: 'voice-volume', value: window.jarvisConfig.audio?.output?.volume || 90, suffix: '%' },
        { id: 'audio-sensitivity', value: window.jarvisConfig.audio?.input?.sensitivity || 5, suffix: '' },
        { id: 'llm-temperature', value: window.jarvisConfig.llm?.temperature || 0.7, suffix: '' },
        { id: 'background-opacity', value: window.jarvisConfig.interface?.background_opacity || 30, suffix: '%' }
    ];
    
    sliderMappings.forEach(mapping => {
        const slider = document.getElementById(mapping.id);
        const valueElement = document.getElementById(`${mapping.id}-value`);
        
        if (slider) {
            slider.value = mapping.value;
        }
        if (valueElement) {
            valueElement.textContent = mapping.value + mapping.suffix;
        }
    });
}

function updateSelectorsFromConfig() {
    if (!window.jarvisConfig) return;
    
    const selectorMappings = [
        { id: 'interface-theme', value: window.jarvisConfig.interface?.theme },
        { id: 'interface-background', value: window.jarvisConfig.interface?.background },
        { id: 'voice-personality', value: window.jarvisConfig.voice?.personality },
        { id: 'llm-model', value: window.jarvisConfig.llm?.model },
        { id: 'role-select', value: window.jarvisConfig.llm?.role }
    ];
    
    selectorMappings.forEach(mapping => {
        const element = document.getElementById(mapping.id);
        if (element && mapping.value) {
            element.value = mapping.value;
        }
    });
}

/**
 * ✅ GARDÉ: Fonctions existantes compatibles
 */
function checkBrowserCompatibility() {
    // Vérifications basiques du navigateur
    const required = ['fetch', 'WebSocket', 'Promise', 'localStorage'];
    const missing = required.filter(feature => !(feature in window));
    
    if (missing.length > 0) {
        addLogEntry(`❌ Fonctionnalités manquantes: ${missing.join(', ')}`, 'error');
        return false;
    }
    
    return true;
}

function startBackgroundServices() {
    addLogEntry('⚙️ Démarrage des services...', 'info');
    
    // Keep-alive WebSocket (déjà démarré dans websocket-manager.js)   
    // Nettoyage périodique des logs
    setInterval(() => {
        cleanupLogs();
    }, 300000); // Toutes les 5 minutes
    
    // Vérification de l'état de connexion
    setInterval(() => {
        if (!isConnected && ws && ws.readyState === WebSocket.CLOSED) {
            addLogEntry('🔄 Reconnexion automatique...', 'info');
            initializeWebSocket();
        }
    }, 30000); // Toutes les 30 secondes
    
    addLogEntry('✅ Services de fond démarrés', 'success');
}

/**
 * 🚀 NOUVEAU: Fonction de recharge de la configuration
 */
async function reloadConfig() {
    try {
        addLogEntry('🔄 Rechargement configuration...', 'info');
        
        const configLoaded = await initializeConfig();
        if (configLoaded) {
            await updateUI();
            addLogEntry('✅ Configuration rechargée', 'success');
            showToast('✅ Configuration mise à jour', 'success');
        } else {
            addLogEntry('❌ Échec rechargement configuration', 'error');
            showToast('❌ Erreur rechargement', 'error');
        }
        
    } catch (error) {
        addLogEntry(`❌ Erreur rechargement: ${error.message}`, 'error');
        showToast('❌ Erreur rechargement', 'error');
    }
}

/**
 * ✅ GARDÉ: Gestionnaire d'erreurs
 */
function handleError(error, context = '') {
    console.error(`Erreur ${context}:`, error);
    addLogEntry(`❌ Erreur ${context}: ${error.message}`, 'error');
}

/**
 * ✅ GARDÉ: Gestion de la visibilité de page
 */
function handleVisibilityChange() {
    if (document.hidden) {
        addLogEntry('👁️ Page masquée, réduction activité', 'info');
        // Réduire les activités de fond
    } else {
        addLogEntry('👁️ Page visible, reprise activité', 'info');
        // Reprendre les activités normales
        if (!isConnected) {
            initializeWebSocket();
        }
    }
}

/**
 * 🚀 MODIFIÉ: Point d'entrée principal
 */
async function main() {
    try {
        // Gestionnaire de visibilité
        document.addEventListener('visibilitychange', handleVisibilityChange);
        
        // Initialisation principale
        const success = await initializeJarvis();
        
        if (!success) {
            // Mode dégradé
            addLogEntry('🔧 Tentative de mode dégradé...', 'warning');
            setTimeout(() => {
                if (confirm('L\'initialisation a échoué. Essayer le mode dégradé ?')) {
                    // Mode dégradé: juste l'interface sans WebSocket
                    initializeConfig();
                    updateUI();
                    showToast('⚠️ Mode dégradé activé', 'warning');
                }
            }, 2000);
        }
    } catch (error) {
        handleError(error, 'Initialisation principale');
        showToast('❌ Erreur critique', 'error');
    }
}

// Point d'entrée unique de l'application
document.addEventListener('DOMContentLoaded', main);

let isMuted = false;

function toggleMute() {
    isMuted = !isMuted;
    updateMuteButton();
    sendWebSocketMessage({
        type: 'config_update',
        config: { audio_output_muted: isMuted }
    });
    addLogEntry(`🔊 Audio ${isMuted ? 'désactivé' : 'activé'}`, 'info');
}

function updateMuteButton() {
    const muteBtn = document.getElementById('mute-btn');
    if (muteBtn) {
        if (isMuted) {
            muteBtn.innerHTML = '🔇';
            muteBtn.title = 'Activer la voix';
            muteBtn.classList.add('muted');
        } else {
            muteBtn.innerHTML = '🔊';
            muteBtn.title = 'Désactiver la voix';
            muteBtn.classList.remove('muted');
        }
    }
}

// Fallback si DOMContentLoaded a déjà été déclenché
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', main);
} else {
    main();
}

// Export des fonctions pour utilisation globale
if (typeof window !== 'undefined') {
    window.reloadConfig = reloadConfig;
    window.updateUI = updateUI;
    window.initializeConfig = initializeConfig;
}

console.log('🚀 App-main unifié chargé');