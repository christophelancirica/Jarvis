/**
 * settings-modal.js - Gestion des paramètres et modales
 * ⚙️ Hypothalamus - Centre de contrôle et configuration
 * 🚀 OPTIMISÉ: Debounce + preview temps réel pour changements visuels
 */

// 🚀 Variables d'optimisation debounce
let previewTimer = null;
let batchedChanges = {};
let lastAppliedValues = {};
const PREVIEW_DEBOUNCE_DELAY = 250;      // 250ms pour preview fluide
const LOCALSTORAGE_DEBOUNCE_DELAY = 500; // 500ms pour localStorage

// Configuration des champs avec preview temps réel
const VISUAL_FIELDS = {
    'interface-background': { 
        key: 'background', 
        handler: 'setBackground',
        immediate: false
    },
    'background-opacity': { 
        key: 'background_opacity', 
        handler: 'setBackgroundOpacity',
        immediate: true   // Immediate pour feedback fluide opacité
    }
};

/**
 * Ouvre la modal des paramètres
 */
function openSettings() {
    const modal = document.getElementById('settings-modal');
    if (modal) {
        modal.classList.add('show');
        interfaceState.settingsModalOpen = true;
        
        // Reset des valeurs de preview
        resetPreviewState();
        
        // Focus sur le premier élément
        const firstInput = modal.querySelector('input, select');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
        
        addLogEntry('⚙️ Paramètres ouverts', 'info');
    }
}

/**
 * Ferme la modal des paramètres
 */
function closeSettings() {
    // Flush final des changements en attente
    flushBatchedChanges();
    
    const modal = document.getElementById('settings-modal');
    if (modal) {
        modal.classList.remove('show');
        interfaceState.settingsModalOpen = false;
        addLogEntry('⚙️ Paramètres fermés', 'info');
    }
}

/**
 * Ouvre la modal d'aide
 */
function showHelp() {
    const modal = document.getElementById('help-modal');
    if (modal) {
        modal.classList.add('show');
        interfaceState.helpModalOpen = true;
        addLogEntry('❓ Aide ouverte', 'info');
    }
}

/**
 * Ferme la modal d'aide
 */
function closeHelp() {
    const modal = document.getElementById('help-modal');
    if (modal) {
        modal.classList.remove('show');
        interfaceState.helpModalOpen = false;
        addLogEntry('❓ Aide fermée', 'info');
    }
}

/**
 * Change d'onglet dans les paramètres
 * @param {string} tabName - Nom de l'onglet
 * @param {Event} event - Événement du clic
 */
function switchSettingsTab(tabName, event) {
    // Masquer tous les onglets
    document.querySelectorAll('.settings-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Désactiver tous les boutons
    document.querySelectorAll('.settings-tabs .tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Activer l'onglet et le bouton sélectionnés
    const targetTab = document.getElementById(`settings-${tabName}`);
    if (targetTab) {
        targetTab.classList.add('active');
        interfaceState.currentSettingsTab = tabName;
    }
    
    if (event && event.target) {
        event.target.classList.add('active');
    }
    
    addLogEntry(`⚙️ Onglet paramètres: ${tabName}`, 'info');
}

/**
 * 🚀 OPTIMISÉ - Initialise les sliders avec preview temps réel debounced
 */
function initializeSliders() {
    const sliders = [
        { id: 'voice-speed', valueId: 'voice-speed-value', suffix: 'x', type: 'audio' },
        { id: 'voice-volume', valueId: 'voice-volume-value', suffix: '%', type: 'audio' },
        { id: 'audio-sensitivity', valueId: 'audio-sensitivity-value', suffix: '', type: 'audio' },
        { id: 'llm-temperature', valueId: 'llm-temperature-value', suffix: '', type: 'model' },
        { id: 'background-opacity', valueId: 'background-opacity-value', suffix: '%', type: 'visual' }
    ];
    
    sliders.forEach(slider => {
        const element = document.getElementById(slider.id);
        const valueElement = document.getElementById(slider.valueId);
        
        if (element && valueElement) {
            // 🚀 Event listener optimisé avec preview
            element.addEventListener('input', function() {
                // Mise à jour immédiate de l'affichage (pas de debounce sur l'UI)
                valueElement.textContent = this.value + slider.suffix;
                
                // Preview temps réel pour les champs visuels
                if (slider.type === 'visual') {
                    triggerVisualPreview(this.id, this.value);
                }
            });
            
            // Initialiser la valeur affichée
            valueElement.textContent = element.value + slider.suffix;
        }
    });
    
    // Event listeners pour les selects visuels
    Object.keys(VISUAL_FIELDS).forEach(fieldId => {
        const element = document.getElementById(fieldId);
        if (element) {
            element.addEventListener('change', function() {
                triggerVisualPreview(this.id, this.value);
            });
        }
    });
}

/**
 * 🚀 Déclenche une preview visuelle avec debounce intelligent
 */
function triggerVisualPreview(elementId, value) {
    const field = VISUAL_FIELDS[elementId];
    if (!field) return;
    
    // Ajouter aux changements en batch
    batchedChanges[field.key] = value;
    
    // Application immédiate ou debounced selon le type
    if (field.immediate) {
        applyVisualChange(field.key, value, field.handler);
    } else {
        // Debounce pour éviter les changements rapides
        if (previewTimer) clearTimeout(previewTimer);
        previewTimer = setTimeout(() => {
            flushVisualPreview();
        }, PREVIEW_DEBOUNCE_DELAY);
    }
}

/**
 * 🚀 Applique les changements visuels en batch (debounced)
 */
function flushVisualPreview() {
    Object.entries(batchedChanges).forEach(([key, value]) => {
        const field = Object.values(VISUAL_FIELDS).find(f => f.key === key);
        if (field && !field.immediate) {
            applyVisualChange(key, value, field.handler);
        }
    });
    
    // Sauvegarder en localStorage avec debounce
    debouncedLocalStorageSave();
}

/**
 * 🚀 Applique un changement visuel individuel (optimisé)
 */
function applyVisualChange(key, value, handlerName) {
    // Éviter les applications redondantes
    if (lastAppliedValues[key] === value) return;
    lastAppliedValues[key] = value;
    
    try {
        switch(handlerName) {
            case 'setTheme':
                if (typeof setTheme === 'function') setTheme(value);
                break;
            case 'setBackground':
                if (typeof setBackground === 'function') setBackground(value);
                break;
            case 'setBackgroundOpacity':
                if (typeof setBackgroundOpacity === 'function') setBackgroundOpacity(value);
                break;
        }
    } catch (error) {
        console.warn(`Erreur application preview ${handlerName}:`, error);
    }
}

/**
 * 🚀 Sauvegarde localStorage debounced
 */
let localStorageTimer = null;
function debouncedLocalStorageSave() {
    if (localStorageTimer) clearTimeout(localStorageTimer);
    
    localStorageTimer = setTimeout(() => {
        try {
            const savedSettings = JSON.parse(localStorage.getItem('jarvis-settings') || '{}');
            Object.assign(savedSettings, batchedChanges);
            localStorage.setItem('jarvis-settings', JSON.stringify(savedSettings));
        } catch (error) {
            console.warn('Erreur sauvegarde localStorage:', error);
        }
    }, LOCALSTORAGE_DEBOUNCE_DELAY);
}

/**
 * 🚀 Flush final des changements en attente
 */
function flushBatchedChanges() {
    if (previewTimer) {
        clearTimeout(previewTimer);
        flushVisualPreview();
    }
    
    if (localStorageTimer) {
        clearTimeout(localStorageTimer);
        debouncedLocalStorageSave();
    }
    
    batchedChanges = {};
}

/**
 * 🚀 Reset l'état de preview
 */
function resetPreviewState() {
    if (previewTimer) clearTimeout(previewTimer);
    if (localStorageTimer) clearTimeout(localStorageTimer);
    
    batchedChanges = {};
    lastAppliedValues = {};
}

/**
 * Gère les événements clavier des modales
 * @param {KeyboardEvent} event 
 */
function handleModalKeydown(event) {
    if (event.key === 'Escape') {
        if (interfaceState.settingsModalOpen) {
            closeSettings();
        } else if (interfaceState.helpModalOpen) {
            closeHelp();
        }
    }
}

/**
 * Initialise les événements des paramètres
 */
function initializeSettingsEvents() {
    // Boutons de modal
    const settingsBtn = document.getElementById('settings-btn');
    if (settingsBtn) {
        settingsBtn.addEventListener('click', openSettings);
    }
    
    const helpBtn = document.getElementById('help-btn');
    if (helpBtn) {
        helpBtn.addEventListener('click', showHelp);
    }
    
    // Boutons de fermeture
    const closeButtons = document.querySelectorAll('.modal-close, .close-settings, .close-help');
    closeButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const modal = this.closest('.modal');
            if (modal && modal.id === 'settings-modal') {
                closeSettings();
            } else if (modal && modal.id === 'help-modal') {
                closeHelp();
            }
        });
    });
    
    // Bouton de sauvegarde
    const saveBtn = document.getElementById('save-settings');
    if (saveBtn) {
        saveBtn.addEventListener('click', saveSettingsFromModal);
    }
    
    // Bouton de reset
    const resetBtn = document.getElementById('reset-settings');
    if (resetBtn) {
        resetBtn.addEventListener('click', resetSettings);
    }
    
    // Fermeture en cliquant sur l'overlay
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                if (this.id === 'settings-modal') {
                    closeSettings();
                } else if (this.id === 'help-modal') {
                    closeHelp();
                }
            }
        });
    });
    
    // Gestion des touches
    document.addEventListener('keydown', handleModalKeydown);
    
    // Initialiser les sliders
    initializeSliders();
}

async function saveSettingsFromModal() {
    try {
        addLogEntry('💾 Sauvegarde sélective...', 'info');
        
        // Flush final des previews en attente
        flushBatchedChanges();
        
        const changes = {};
        
        // Helper pour ajouter un changement si la valeur est différente
        const addChange = (key, newValue, currentValue) => {
            if (newValue !== currentValue) {
                changes[key] = newValue;
            }
        };

        const currentSettings = await getCurrentServerConfig();

        // Voix
        addChange('personality', document.getElementById('voice-personality')?.value, currentSettings.voice?.personality);
        addChange('voice_speed', parseFloat(document.getElementById('voice-speed')?.value || 1.0), currentSettings.audio?.output?.speed);
        addChange('voice_volume', parseInt(document.getElementById('voice-volume')?.value || 90), currentSettings.audio?.output?.volume);
        
        // LLM
        addChange('llm_model', document.getElementById('llm-model')?.value, currentSettings.llm?.model);
        addChange('llm_temperature', parseFloat(document.getElementById('llm-temperature')?.value || 0.7), currentSettings.llm?.temperature);

        // Interface
        addChange('theme', document.getElementById('interface-theme')?.value, currentSettings.interface?.theme);
        addChange('background', document.getElementById('interface-background')?.value, currentSettings.interface?.background);
        addChange('background_opacity', parseInt(document.getElementById('background-opacity')?.value || 30), currentSettings.interface?.background_opacity);

        // Audio
        addChange('audio_device', document.getElementById('audio-device')?.value, currentSettings.audio?.input?.device_index);
        console.log('🔍 [DEBUG] Changements détectés:', changes);
        
        if (Object.keys(changes).length === 0) {
            addLogEntry('ℹ️ Aucun changement détecté', 'info');
            closeSettings();
            return;
        }
        
        console.log('🚨 [DEBUG] ENVOI WebSocket:', {
            type: 'config_update',
            config: changes
        });
        // ✅ Catégoriser les changements
        const lightChanges = {}; // Interface, theme, background - application immédiate
        const heavyChanges = {}; // Voice, LLM, STT - nécessitent rechargement modules
        
        Object.entries(changes).forEach(([key, value]) => {
            if (['theme', 'background', 'background_opacity', 'voice_speed', 'voice_volume'].includes(key)) {
                lightChanges[key] = value;
            } else {
                heavyChanges[key] = value;
            }
        });
        
        // ✅ Appliquer les changements légers IMMÉDIATEMENT (optimisé)
        if (Object.keys(lightChanges).length > 0) {
            applyLightChanges(lightChanges);
        
            addLogEntry(`✅ Changements visuels appliqués`, 'success');
        }
        
        // ✅ Sauvegarder TOUS les changements sur le serveur
        const allChangesToSave = {...lightChanges, ...heavyChanges};
        
        if (Object.keys(allChangesToSave).length > 0) {
        
            // Validation
            if (allChangesToSave.personality && !allChangesToSave.personality.trim()) {
                throw new Error('Personnalité requise');
            }
            
            // Envoyer au serveur via WebSocket
            if (!isConnected) {
                throw new Error('Connexion WebSocket requise');
            }
            
            // Créer une promesse pour attendre la réponse
            const success = await new Promise((resolve) => {
                const timeout = setTimeout(() => resolve(false), 5000);
                
                const handleResponse = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        if (data.type === 'config_updated') {
                            clearTimeout(timeout);
                            ws.removeEventListener('message', handleResponse);
                            resolve(data.success === true);
                        }
                    } catch (e) {
                        // Ignorer les autres messages
                    }
                };
                
                ws.addEventListener('message', handleResponse);
                
                console.log('🚨 ENVOI WebSocket:', {
                    type: 'config_update',
                    config: allChangesToSave
                });
                
                const sent = sendWebSocketMessage({
                    type: 'config_update',
                    config: allChangesToSave
                });
                
                if (!sent) {
                    clearTimeout(timeout);
                    resolve(false);
                }
            });
            
            if (success) {
                addLogEntry(`✅ Paramètres sauvegardés (${Object.keys(allChangesToSave).length} changements)`, 'success');
            } else {
                throw new Error('Timeout ou erreur serveur');
            }
        }
        
        closeSettings();
        
    } catch (error) {
        console.error('Erreur sauvegarde:', error);
        addLogEntry('❌ Erreur sauvegarde: ' + error.message, 'error');
    }
}

/**
 * Reset des paramètres
 */
async function resetSettings() {
    if (!confirm('Remettre tous les paramètres par défaut ?')) return;
    
    // Reset preview state
    resetPreviewState();
    
    try {
        // Valeurs par défaut
        const defaultSettings = {
            personality: 'Jarvis',
            voice_speed: 1.0,
            voice_volume: 90,
            llm_model: 'qwen2.5:7b',
            llm_temperature: 0.7,
            theme: 'dark',
            background: 'none',
            background_opacity: 30,
            audio_sensitivity: 5
        };
        
        // Mettre à jour l'interface immédiatement
        Object.entries(defaultSettings).forEach(([key, value]) => {
            const element = document.getElementById(key === 'theme' ? 'interface-theme' : 
                                                 key === 'background' ? 'interface-background' :
                                                 key === 'llm_model' ? 'llm-model' :
                                                 key === 'personality' ? 'voice-personality' :
                                                 key.replace('_', '-'));
            if (element) {
                element.value = value;
            }
        });
        
        // Recharger pour mettre à jour les sliders
        await populateVoiceSelect();
        
        // Appliquer les changements visuels
        applyLightChanges({
            theme: defaultSettings.theme,
            background: defaultSettings.background,
            background_opacity: defaultSettings.background_opacity
        });
        
        // Supprimer du localStorage
        localStorage.removeItem('jarvis-settings');
        
        addLogEntry('🔄 Paramètres remis à zéro', 'info');
        
    } catch (error) {
        addLogEntry('❌ Erreur reset: ' + error.message, 'error');
    }
}

/**
 * 🚀 OPTIMISÉ - Applique les changements légers côté client (avec anti-redondance)
 */
function applyLightChanges(changes) {
    console.log('🎨 applyLightChanges optimisé avec:', changes);
    
    // Éviter les applications redondantes
    Object.entries(changes).forEach(([key, value]) => {
        if (lastAppliedValues[key] === value) {
            delete changes[key];
        } else {
            lastAppliedValues[key] = value;
        }
    });
    
    if (Object.keys(changes).length === 0) {
        console.log('⚡ Tous changements déjà appliqués - skip');
        return;
    }
    
    if (changes.theme) {
        console.log('🎨 Application thème:', changes.theme);
        setTheme(changes.theme);
    }
    
    if (changes.background) {
        console.log('🖼️ Application background:', changes.background);
        setBackground(changes.background);
    }
    
    if (changes.background_opacity !== undefined) {
        setBackgroundOpacity(changes.background_opacity);
    }
    
    // Sauvegarder dans localStorage (sans debounce car c'est la sauvegarde finale)
    const savedSettings = JSON.parse(localStorage.getItem('jarvis-settings') || '{}');
    Object.assign(savedSettings, changes);
    localStorage.setItem('jarvis-settings', JSON.stringify(savedSettings));
    
    console.log('✅ applyLightChanges optimisé terminé');
}


/**
 * Compare deux objets (ancien et nouveau) et retourne un objet contenant 
 * uniquement les parties du nouvel objet qui ont changé.
 * @param {Object} current - La configuration actuelle (serveur).
 * @param {Object} newSettings - La nouvelle configuration (modale).
 * @returns {Object} Un objet contenant uniquement les changements.
 */
function getChangedSettings(current, newSettings) {
    const changes = {};

    for (const key in newSettings) {
        // Ignorer les propriétés héritées
        if (!Object.prototype.hasOwnProperty.call(newSettings, key)) continue;

        const currentValue = current[key];
        const newValue = newSettings[key];

        // 1. Si les deux sont des objets (mais pas null ou Array) -> Comparaison récursive
        if (typeof newValue === 'object' && newValue !== null && !Array.isArray(newValue)) {
            
            // S'assurer que la clé existe dans l'objet actuel pour éviter une erreur
            if (typeof currentValue !== 'object' || currentValue === null || Array.isArray(currentValue)) {
                 // Si la structure a changé (ex: object devient string), on considère ça comme un changement complet
                 changes[key] = newValue;
                 continue;
            }

            // Appel récursif pour détecter les changements dans l'objet imbriqué
            const nestedChanges = getChangedSettings(currentValue, newValue);
            
            // Si des changements sont trouvés dans l'objet imbriqué,
            // on ajoute l'objet *complet* au bloc de changement.
            if (Object.keys(nestedChanges).length > 0) {
                changes[key] = newValue;
            }
            
        } 
        // 2. Si c'est une valeur primitive (string, number, boolean) ou Array/null -> Comparaison directe
        else if (currentValue !== newValue) {
            
            // 🐛 Gestion des nombres à virgule flottante (pour llm_temperature) :
            // Parfois, la conversion en float peut laisser des artefacts (ex: 0.7000000000000001)
            // On peut arrondir légèrement pour une comparaison fiable.
            let isNumeric = typeof currentValue === 'number' && typeof newValue === 'number';
            
            if (isNumeric && Math.abs(currentValue - newValue) < 0.00001) {
                // Les nombres sont "identiques" malgré une légère différence binaire
                continue;
            }
            
            // C'est un changement réel de valeur (primitive ou Array/null)
            changes[key] = newValue;
        }
    }

    return changes;
}

/**
 * Récupère la config actuelle du serveur
 */
async function getCurrentServerConfig() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Erreur récupération config serveur:', error);
        return {};
    }
}

// 🚀 Nettoyage automatique lors du déchargement de page
window.addEventListener('beforeunload', function() {
    flushBatchedChanges();
});

/**
 * Teste la voix actuellement sélectionnée dans les paramètres
 */
async function testVoice() {
    const voiceSelect = document.getElementById('voice-personality');
    const testButton = document.querySelector('button[onclick="testVoice()"]');
    if (!voiceSelect || !testButton) {
        showToast('Erreur: Composants introuvables.', 'error');
        return;
    }

    const voiceId = voiceSelect.value;
    if (!voiceId) {
        showToast('Veuillez sélectionner une voix.', 'warning');
        return;
    }

    // Gérer l'état du bouton
    const originalButtonText = testButton.innerHTML;
    testButton.innerHTML = '🔊 Test en cours...';
    testButton.disabled = true;

    try {
        showToast(`🔊 Test de la voix : ${voiceSelect.options[voiceSelect.selectedIndex].text}...`, 'info');

        const response = await fetch('/api/voice/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                voice_id: voiceId,
                text: "Bonjour, ceci est un test de la voix sélectionnée."
            })
        });

        if (response.ok) {
            addLogEntry(`🔊 Test de la voix '${voiceId}' envoyé.`, 'info');
        } else {
            const error = await response.json();
            const errorMessage = error.message || 'Le test de la voix a échoué.';
            showToast(`❌ Erreur : ${errorMessage}`, 'error');
            addLogEntry(`❌ Erreur test voix : ${errorMessage}`, 'error');
        }

    } catch (error) {
        const errorMessage = error.message || 'Une erreur inattendue est survenue.';
        showToast(`❌ Erreur : ${errorMessage}`, 'error');
        addLogEntry(`❌ Erreur test voix : ${errorMessage}`, 'error');
    } finally {
        // Restaurer l'état du bouton
        if (testButton && originalButtonText) {
            testButton.innerHTML = originalButtonText;
            testButton.disabled = false;
        }
    }
}

// Initialiser les événements dès que le DOM est prêt
document.addEventListener('DOMContentLoaded', initializeSettingsEvents);
