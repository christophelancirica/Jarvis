/**
 * voice-manager.js - Gestionnaire centralisé des voix
 * 🎤 Module unique pour toute la gestion des voix (standard + clonées)
 */

class VoiceManager {
    constructor() {
        this.voices = {
            standard: {},
            cloned: {}
        };
        this.isLoaded = false;
        this.listeners = new Set();
    }

    /**
     * Charge TOUTES les voix depuis le serveur
     */
    async loadAllVoices() {
        try {
            console.log('🔄 Chargement des voix...');
            
            const response = await fetch('/api/voice/all/list');
            const data = await response.json();
            
            if (data.success || data.voices) {  // Parfois pas de champ "success"
                // Nettoyer et réorganiser
                this.voices.standard = data.voices || {};
                this.voices.cloned = {};
                
                // ✅ CORRECTION - Prendre TOUTES les voix clonées prêtes
                if (data.cloned_voices) {
                    Object.entries(data.cloned_voices).forEach(([id, voice]) => {
                        console.log(`🎭 Voix clonée trouvée: ${id} - ${voice.name} - Status: ${voice.processing_status}`);
                        
                        // ✅ Filtre corrigé
                        if (voice.processing_status === 'ready') {
                            this.voices.cloned[id] = voice;
                            console.log(`✅ Voix ajoutée: ${voice.name}`);
                        } else {
                            console.log(`⚠️ Voix ignorée (status: ${voice.processing_status}): ${voice.name}`);
                        }
                    });
                }
                
                this.isLoaded = true;
                this.notifyListeners('voices_loaded');
                
                console.log(`✅ ${Object.keys(this.voices.standard).length} voix standard, ${Object.keys(this.voices.cloned).length} voix clonées`);
                console.log(`🎭 Voix clonées chargées:`, Object.keys(this.voices.cloned));
                
                return true;
            } else {
                console.error('❌ Format API inattendu:', data);
                return false;
            }
        } catch (error) {
            console.error('❌ Erreur chargement voix:', error);
            return false;
        }
    }

    /**
     * Met à jour une interface avec les voix
     */
    populateSelect(selectId) {
        const select = document.getElementById(selectId);
        if (!select || !this.isLoaded) return false;

        // Vider la liste
        select.innerHTML = '';

        // Ajouter voix standard
        if (Object.keys(this.voices.standard).length > 0) {
            const standardGroup = document.createElement('optgroup');
            standardGroup.label = '🎤 Voix standard';
            
            Object.entries(this.voices.standard).forEach(([id, voice]) => {
                const option = document.createElement('option');
                option.value = id;

                // Indicateurs visuels
                let indicator = "";
                if (voice.model === "edge-tts" || voice.model === "piper") {
                    indicator = " 🟢 Streaming | ⚡ Vitesse native";
                } else if (voice.model === "gtts") {
                    indicator = " 🟠 Différé | 🐌 Vitesse simulée (Pitch)";
                } else if (voice.model === "xtts-v2" || (voice.model && voice.model.startsWith("tts_models/"))) {
                    indicator = " 🟠 Différé | 💎 Haute Qualité";
                }

                option.textContent = (voice.display_name || voice.name) + indicator;
                standardGroup.appendChild(option);
            });
            
            select.appendChild(standardGroup);
        }

        // Ajouter voix clonées
        if (Object.keys(this.voices.cloned).length > 0) {
            const clonedGroup = document.createElement('optgroup');
            clonedGroup.label = '🎭 Voix clonées';
            
            Object.entries(this.voices.cloned).forEach(([id, voice]) => {
                const option = document.createElement('option');
                option.value = id;

                // Indicateurs pour voix clonées (généralement XTTS)
                let indicator = "";
                if (voice.model === "xtts-v2" || (voice.model && voice.model.startsWith("tts_models/"))) {
                     indicator = " 🟠 Différé | 💎 Haute Qualité";
                }

                option.textContent = (voice.display_name || voice.name) + indicator;
                clonedGroup.appendChild(option);
            });
            
            select.appendChild(clonedGroup);
        }

        return true;
    }

    /**
     * Rechargement après modification
     */
    async refresh() {
        await this.loadAllVoices();
        this.notifyListeners('voices_updated');
    }

    /**
     * Système d'événements simple
     */
    addListener(callback) {
        this.listeners.add(callback);
    }

    removeListener(callback) {
        this.listeners.delete(callback);
    }

    notifyListeners(event) {
        this.listeners.forEach(callback => {
            try {
                callback(event, this.voices);
            } catch (e) {
                console.error('Erreur listener:', e);
            }
        });
    }

    /**
     * Getters utiles
     */
    getVoiceById(id) {
        return this.voices.standard[id] || this.voices.cloned[id] || null;
    }

    getAllVoices() {
        return {...this.voices.standard, ...this.voices.cloned};
    }

    getClonedVoices() {
        return this.voices.cloned;
    }

    getStats() {
        return {
            standard: Object.keys(this.voices.standard).length,
            cloned: Object.keys(this.voices.cloned).length,
            total: Object.keys(this.voices.standard).length + Object.keys(this.voices.cloned).length
        };
    }
}

// Instance globale unique
window.voiceManager = new VoiceManager();

/**
 * Fonctions publiques simplifiées
 */

// Charger les voix au démarrage
async function initVoices() {
    return await window.voiceManager.loadAllVoices();
}

// Mettre à jour un select avec les voix
function updateVoiceSelect(selectId) {
    return window.voiceManager.populateSelect(selectId);
}

// Rafraîchir après modification
async function refreshVoices() {
    await window.voiceManager.refresh();
}

// S'abonner aux changements
function onVoicesChange(callback) {
    window.voiceManager.addListener(callback);
}

console.log('🎤 Voice Manager initialisé');
