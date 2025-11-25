/**
 * settings-frontend.js - Frontend unifié pour configuration
 * 🎯 Toutes les opérations via REST
 */
class ConfigAPI {
    constructor() {
        this.baseUrl = '/api/config';
    }

    // === LECTURE ===
    async getFullConfig() {
        const response = await fetch(`${this.baseUrl}`);
        const data = await response.json();
        return data.success ? data.config : null;
    }

    async getVoiceConfig() {
        const response = await fetch(`${this.baseUrl}/voice`);
        const data = await response.json();
        return data.success ? data.voice_config : null;
    }

    async getInterfaceConfig() {
        const response = await fetch(`${this.baseUrl}/interface`);
        const data = await response.json();
        return data.success ? data.config : null;
    }

    // === ÉCRITURE ===
    async updateConfig(updates) {
        const response = await fetch(`${this.baseUrl}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        });
        const data = await response.json();
        return data.success;
    }

    async updateVoice(personality, ttsModel, options = {}) {
        const response = await fetch(`${this.baseUrl}/voice`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                personality,
                tts_model: ttsModel,
                ...options
            })
        });
        const data = await response.json();
        return data.success;
    }

    async updateInterface(interfaceConfig) {
        const response = await fetch(`${this.baseUrl}/interface`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(interfaceConfig)
        });
        const data = await response.json();
        return data.success;
    }
}

// Instance globale
const configAPI = new ConfigAPI();

/**
 * 🚀 THEME MANAGER UNIFIÉ - Plus de localStorage
 *//*
function setTheme(theme) {
    // 1. Appliquer immédiatement l'UI
    document.body.className = `theme-${theme}`;
    currentTheme = theme;
    updateThemeButton();
    
    // 2. Sauvegarder via API
    configAPI.updateInterface({ theme })
        .then(success => {
            if (success) {
                addLogEntry(`✅ Thème sauvegardé: ${theme}`, 'success');
            }
        })
        .catch(error => {
            addLogEntry(`❌ Erreur sauvegarde thème: ${error.message}`, 'error');
        });
}

function setBackground(backgroundPath) {
    const dialogueContainer = document.getElementById('dialogue-container');
    if (!dialogueContainer) return;
    
    const dialogueSection = dialogueContainer.closest('.dialogue-section');
    if (!dialogueSection) return;
    
    // 1. Appliquer immédiatement l'UI
    dialogueSection.style.removeProperty('--bg-image-url');
    dialogueSection.classList.remove('bg-image');
    
    if (backgroundPath && backgroundPath !== 'default') {
        let imagePath = backgroundPath.startsWith('images/') ? 
            `static/${backgroundPath}` : `static/images/${backgroundPath}`;
        
        dialogueSection.style.setProperty('--bg-image-url', `url('${imagePath}')`);
        dialogueSection.classList.add('bg-image');
    }
    
    // 2. Sauvegarder via API
    configAPI.updateInterface({ background: backgroundPath })
        .then(success => {
            if (success) {
                addLogEntry(`✅ Background sauvegardé: ${backgroundPath}`, 'success');
            }
        })
        .catch(error => {
            addLogEntry(`❌ Erreur sauvegarde background: ${error.message}`, 'error');
        });
}

function setBackgroundOpacity(opacity) {
    // 1. Appliquer immédiatement l'UI
    const style = document.createElement('style');
    style.id = 'background-opacity-override';
    
    const existing = document.getElementById('background-opacity-override');
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
    
    // 2. Sauvegarder via API
    configAPI.updateInterface({ background_opacity: opacity })
        .then(success => {
            if (success) {
                addLogEntry(`✅ Opacité sauvegardée: ${opacity}%`, 'success');
            }
        })
        .catch(error => {
            addLogEntry(`❌ Erreur sauvegarde opacité: ${error.message}`, 'error');
        });
}
*/
/**
 * 🚀 SETTINGS MODAL UNIFIÉ
 */
async function saveSettings() {
    try {
        addLogEntry('💾 Sauvegarde unifiée...', 'info');
        
        // Collecter TOUTES les valeurs depuis l'interface
        const updates = {};
        
        // Voix
        const personality = document.getElementById('voice-personality')?.value;
        if (personality) {
            updates.voice = { personality };
        }
        
        // Audio
        const voiceSpeed = document.getElementById('voice-speed')?.value;
        const voiceVolume = document.getElementById('voice-volume')?.value;
        if (voiceSpeed || voiceVolume) {
            updates.audio = { output: {} };
            if (voiceSpeed) updates.audio.output.speed = parseFloat(voiceSpeed);
            if (voiceVolume) updates.audio.output.volume = parseInt(voiceVolume);
        }
        
        // LLM
        const llmModel = document.getElementById('llm-model')?.value;
        const llmTemperature = document.getElementById('llm-temperature')?.value;
        const role = document.getElementById('role-select')?.value;
        if (llmModel || llmTemperature || role) {
            updates.llm = {};
            if (llmModel) updates.llm.model = llmModel;
            if (llmTemperature) updates.llm.temperature = parseFloat(llmTemperature);
            if (role) updates.llm.role = role;
        }
        
        // Interface
        const theme = document.getElementById('interface-theme')?.value;
        const background = document.getElementById('interface-background')?.value;
        const backgroundOpacity = document.getElementById('background-opacity')?.value;
        if (theme || background || backgroundOpacity) {
            updates.interface = {};
            if (theme) updates.interface.theme = theme;
            if (background) updates.interface.background = background;
            if (backgroundOpacity) updates.interface.background_opacity = parseInt(backgroundOpacity);
        }
        
        console.log('🔍 [DEBUG] Updates unifiés:', updates);
        
        // 🚀 UNE SEULE REQUÊTE pour tout sauvegarder
        const success = await configAPI.updateConfig(updates);
        
        if (success) {
            addLogEntry('✅ Configuration sauvegardée', 'success');
            closeSettings();
        } else {
            addLogEntry('❌ Erreur sauvegarde', 'error');
        }
        
    } catch (error) {
        console.error('❌ Erreur sauvegarde unifiée:', error);
        addLogEntry('❌ Erreur: ' + error.message, 'error');
    }
}

/**
 * 🚀 CHARGEMENT UNIFIÉ des paramètres
 */
async function loadSettings() {
    try {
        addLogEntry('📄 Chargement configuration...', 'info');
        
        // 🚀 UNE SEULE REQUÊTE pour tout charger
        const config = await configAPI.getFullConfig();
        
        if (!config) {
            addLogEntry('❌ Erreur chargement config', 'error');
            return;
        }
        
        console.log('🔍 [DEBUG] Config chargée:', config);
        
        // Appliquer aux contrôles
        applyConfigToUI(config);
        
        addLogEntry('✅ Configuration chargée', 'success');
        
    } catch (error) {
        console.error('❌ Erreur chargement:', error);
        addLogEntry('❌ Erreur: ' + error.message, 'error');
    }
}

function applyConfigToUI(config) {
    // Voix
    if (config.voice?.personality) {
        const voiceSelect = document.getElementById('voice-personality');
        if (voiceSelect) voiceSelect.value = config.voice.personality;
    }
    
    // Audio
    if (config.audio?.output) {
        const speedSlider = document.getElementById('voice-speed');
        const volumeSlider = document.getElementById('voice-volume');
        
        if (speedSlider && config.audio.output.speed !== undefined) {
            speedSlider.value = config.audio.output.speed;
            const speedValue = document.getElementById('voice-speed-value');
            if (speedValue) speedValue.textContent = config.audio.output.speed + 'x';
        }
        
        if (volumeSlider && config.audio.output.volume !== undefined) {
            volumeSlider.value = config.audio.output.volume;
            const volumeValue = document.getElementById('voice-volume-value');
            if (volumeValue) volumeValue.textContent = config.audio.output.volume + '%';
        }
    }
    
    // LLM
    if (config.llm) {
        const modelSelect = document.getElementById('llm-model');
        const tempSlider = document.getElementById('llm-temperature');
        const roleSelect = document.getElementById('role-select');
        
        if (modelSelect && config.llm.model) {
            modelSelect.value = config.llm.model;
        }
        
        if (tempSlider && config.llm.temperature !== undefined) {
            tempSlider.value = config.llm.temperature;
            const tempValue = document.getElementById('llm-temperature-value');
            if (tempValue) tempValue.textContent = config.llm.temperature + '';
        }
        
        if (roleSelect && config.llm.role) {
            roleSelect.value = config.llm.role;
        }
    }
    
    // Interface
    if (config.interface) {
        const themeSelect = document.getElementById('interface-theme');
        const backgroundSelect = document.getElementById('interface-background');
        const opacitySlider = document.getElementById('background-opacity');
        
        if (themeSelect && config.interface.theme) {
            themeSelect.value = config.interface.theme;
            // Appliquer aussi au thème actuel
            currentTheme = config.interface.theme;
            document.body.className = `theme-${config.interface.theme}`;
        }
        
        if (backgroundSelect && config.interface.background) {
            backgroundSelect.value = config.interface.background;
        }
        
        if (opacitySlider && config.interface.background_opacity !== undefined) {
            opacitySlider.value = config.interface.background_opacity;
            const opacityValue = document.getElementById('background-opacity-value');
            if (opacityValue) opacityValue.textContent = config.interface.background_opacity + '%';
        }
    }
}

/**
 * 🚀 INITIALISATION au démarrage
 */
async function initializeConfig() {
    try {
        // Charger et appliquer la config au démarrage
        await loadSettings();
        addLogEntry('✅ Configuration unifiée initialisée', 'success');
    } catch (error) {
        addLogEntry('❌ Erreur init config unifiée: ' + error.message, 'error');
    }
}

// Export des fonctions
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        configAPI,
        setTheme,
        setBackground,
        setBackgroundOpacity,
        saveSettings,
        loadSettings,
        initializeConfig
    };
}

console.log('🎯 Frontend config unifié chargé');
