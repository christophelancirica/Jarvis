/**
 * config-loader.js - Chargement des configurations JSON
 * 🗄️ Hippocampe - Gestion de la mémoire de configuration
 */

/**
 * Charge toutes les configurations JSON au démarrage
 * @returns {Promise<boolean>} Succès du chargement
 */

/**
 * Peuple les paramètres de l'interface depuis la configuration chargée
 */
function populateSettingsFromConfig() {
    addLogEntry('🔄 Mise à jour interface depuis configuration', 'info');
    
    // Peupler les voix disponibles
    populateVoiceSelect();
    
    // Peupler les modèles LLM
    populateModelSelect();
    
    // Peupler les thèmes
    populateThemeSelect();
    
    // Peupler les arrière-plans
    populateBackgroundSelect();
}

/**
 * Peuple la liste des voix
 */
async function populateVoiceSelect() {
    const voiceSelect = document.getElementById('voice-personality');
    if (!voiceSelect) return;
    
    if (!window.voiceManager?.isLoaded) {
        setTimeout(populateVoiceSelect, 500);
        return;
    }
    
    // 1. Remplir la liste
    window.voiceManager.populateSelect('voice-personality');
    
    // 2. Récupérer la vraie valeur depuis le serveur (comme au démarrage)
    try {
        const response = await fetch('/api/voice/current');
        const data = await response.json();
        
        if (data.voice_id && voiceSelect.querySelector(`option[value="${data.voice_id}"]`)) {
            voiceSelect.value = data.voice_id;
            addLogEntry(`✅ Voix serveur restaurée: ${data.voice_id}`, 'success');
            return;
        }
    } catch (error) {
        console.warn('Erreur API voice/current:', error);
    }
    
    // 3. Fallback localStorage
    const savedSettings = loadSavedSettings();
    if (savedSettings?.personality) {
        voiceSelect.value = savedSettings.personality;
        addLogEntry(`✅ Voix localStorage: ${savedSettings.personality}`, 'info');
    }
}

/**
 * Peuple la liste des modèles LLM
 */
function populateModelSelect() {
    // Cette fonction est maintenant obsolète. Le chargement se fait
    // de manière dynamique dans app-main.js via loadModelsFromAPI().
    // On la laisse vide pour éviter des erreurs si elle est encore appelée.
}

/**
 * Peuple la liste des rôles pour LLM
 */
async function loadRoles() {
    try {
        const response = await fetch('config/roles.json');
        const data = await response.json();
        config.roles = data;
        
        const roleSelect = document.getElementById('role-select');
        if (roleSelect && data.roles) {
            roleSelect.innerHTML = '';
            Object.values(data.roles).forEach(role => {
                const option = document.createElement('option');
                option.value = role.id;
                option.textContent = role.name;
                roleSelect.appendChild(option);
            });
            
            // 🚀 AJOUTER : Sélectionner la valeur par défaut ou sauvegardée
            const savedSettings = loadSavedSettings();
            const currentRole = savedSettings?.role || data.default_role;
            if (currentRole) {
                roleSelect.value = currentRole;
            }
        }
        
        addLogEntry('✅ Rôles chargés', 'success');
    } catch (error) {
        addLogEntry(`❌ Erreur chargement rôles: ${error.message}`, 'error');
    }
}

/**
 * Peuple la liste des thèmes
 */
function populateThemeSelect() {
    const themeSelect = document.getElementById('interface-theme');
    if (!themeSelect || !config.themes?.themes) return;
    
    themeSelect.innerHTML = '';
    Object.values(config.themes.themes).forEach(theme => {
        const option = document.createElement('option');
        option.value = theme.id;
        option.textContent = theme.current_name;
        themeSelect.appendChild(option);
    });
    
    themeSelect.value = currentTheme;
}

/**
 * Peuple la liste des arrière-plans depuis l'API
 */
async function populateBackgroundSelect() {
    try {
        const response = await fetch('/api/backgrounds');
        const data = await response.json();
        
        const backgroundSelect = document.getElementById('interface-background');
        if (!backgroundSelect || !data.success) return;
        
        backgroundSelect.innerHTML = '';
        
        data.backgrounds.forEach(bg => {
            const option = document.createElement('option');
            option.value = bg.path || 'default';
            option.textContent = bg.name;
            backgroundSelect.appendChild(option);
        });
        
        // Sélectionner la valeur sauvegardée
        const savedBackground = localStorage.getItem('jarvis-background') || 'default';
        backgroundSelect.value = savedBackground;
        
        addLogEntry('✅ Arrière-plans chargés', 'success');
    } catch (error) {
        addLogEntry(`❌ Erreur chargement arrière-plans: ${error.message}`, 'error');
    }
}

/**
 * Met à jour l'affichage de l'arrière-plan actuel
 */
function updateBackgroundDisplay(backgroundPath, backgroundName) {
    // Mettre à jour le texte dans l'onglet Config
    const configBg = document.getElementById('config-background');
    if (configBg) {
        configBg.textContent = backgroundName || backgroundPath || 'Par défaut';
    }
    
    // Mettre à jour la preview
    const previewContainer = document.getElementById('background-preview-container');
    const previewImg = document.getElementById('background-preview');
    
    if (previewContainer && previewImg) {
        if (backgroundPath && backgroundPath !== 'default') {
            const imagePath = backgroundPath.startsWith('images/') ? 
                `static/${backgroundPath}` : 
                `static/images/${backgroundPath}`;
            
            previewImg.src = imagePath;
            previewImg.onload = () => {
                previewContainer.style.display = 'block';
                console.log('✅ Preview image chargée');
            };
            previewImg.onerror = () => {
                console.error('❌ Preview image échouée');
                previewContainer.style.display = 'none';
            };
        } else {
            previewContainer.style.display = 'none';
        }
    }
}
async function populateBackgroundSelect() {
    try {
        const response = await fetch('/api/backgrounds');
        const data = await response.json();
        
        const backgroundSelect = document.getElementById('interface-background');
        if (!backgroundSelect || !data.success) return;
        
        backgroundSelect.innerHTML = '';
        
        // ✅ Utiliser les images scannées dynamiquement
        data.backgrounds.forEach(bg => {
            const option = document.createElement('option');
            option.value = bg.path || 'default';  // Utiliser le path comme valeur
            option.textContent = bg.name;
            option.dataset.filename = bg.filename || '';
            backgroundSelect.appendChild(option);
        });
        
        // ✅ Sélectionner l'arrière-plan actuel
        const saved = localStorage.getItem('jarvis-background');
        if (saved) {
            backgroundSelect.value = saved;
        }
        
    } catch (error) {
        console.error('Erreur chargement backgrounds:', error);
    }
}

async function populateAllSelects() {
    addLogEntry('📋 Chargement des listes de sélection...', 'info');
    
    // Peupler les voix disponibles
    populateVoiceSelect();
    
    // Peupler les modèles LLM
    populateModelSelect();
    
    // Peupler les Rôles LLM
    loadRoles();
    
    // Peupler les thèmes
    populateThemeSelect();
    
    // ✅ AJOUTER : Peupler les arrière-plans
    await populateBackgroundSelect();
}

/**
 * Applique un arrière-plan par path
 */
function setBackground(backgroundPath) {
    const body = document.body;
    
    // ✅ Nettoyer
    body.style.backgroundImage = '';
    body.style.backgroundColor = '';
    body.classList.remove('bg-image');
    
    if (backgroundPath && backgroundPath !== 'default') {
        // ✅ Appliquer l'image
        body.style.backgroundImage = `url('${backgroundPath}')`;
        body.style.backgroundSize = 'cover';
        body.style.backgroundPosition = 'center';
        body.style.backgroundRepeat = 'no-repeat';
        body.classList.add('bg-image');
        
        addLogEntry(`🖼️ Arrière-plan: ${backgroundPath}`, 'info');
    } else {
        // ✅ Par défaut
        body.style.backgroundColor = 'var(--bg-primary)';
        addLogEntry('🎨 Arrière-plan par défaut', 'info');
    }
    
    // ✅ Sauvegarder
    localStorage.setItem('jarvis-background', backgroundPath || 'default');
}

/**
 * Charge la configuration actuelle depuis l'API
 */
async function loadCurrentConfig() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();
        console.log('Réponse complète du serveur (/api/config) :', data);
        if (data.voice) {
            const serverConfig = data.voice;

            const displayName = `Assistant virtuel - ${serverConfig.display_name}`;
            updatePersonality(displayName);
            addLogEntry(`✅ ${displayName} chargé`, 'success');
            
            // Mettre à jour le thème si différent
            if (data.interface.theme !== currentTheme) {
                setTheme(data.interface.theme);
            }
            
            // Mettre à jour l'affichage de configuration
            updateConfigDisplay(data);
            
            return serverConfig;
        } else {
            addLogEntry('⚠️ Config serveur non disponible', 'warning');
            return null;
        }
    } catch (error) {
        addLogEntry(`❌ Erreur chargement config serveur: ${error.message}`, 'error');
        return null;
    }
}

/**
 * Met à jour l'affichage de la configuration dans l'interface
 * @param {Object} configData - Données de configuration
 */
function updateConfigDisplay(configData) {
    const elements = {
        'config-llm': configData.llm.model || 'llama3.1:8b',
        'config-tts': configData.voice.tts_model || 'edge-tts', 
        'config-personality': configData.voice.display_name || configData.voice.personality || 'Samantha',
        'role-select': configData.llm.role || 'assistant_general',
        'config-audio': configData.audio.output.device_index !== null ? `Device ${configData.audio.output.device_index}` : 'Auto',
        'config-theme': configData.interface.theme || 'light'
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    });
    
    // Mettre à jour la personnalité dans le header si disponible
    if (configData.display_name) {
        updatePersonality(configData.display_name);
    }
}