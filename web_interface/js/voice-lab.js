/**
 * voice-lab-complete.js - Laboratoire de clonage vocal complet
 * 🎭 Interface complète pour créer, gérer et utiliser des voix clonées
 */

// État du Voice Lab
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let recordingStartTime = null;
let recordingTimer = null;
let currentEditingVoice = null;
let pendingAudioData = null;

/**
 * Toggle le panneau Voice Lab
 */
function toggleVoiceLab() {
    voiceVisible = !voiceVisible;
    updateVoiceVisibility();

    addLogEntry(`🔍 Voice Lab : ${voiceVisible ? 'activé' : 'désactivé'}`, 'info');
    saveSettings();
}

/**
 * Met à jour la visibilité du panneau de camera
 */
function updateVoiceVisibility() {
    const voiceSection = document.getElementById('voice-section');
    const mainContent = document.querySelector('.main-content');
    
    if (!voiceSection || !mainContent) return;
    
    if (voiceVisible) {
        voiceSection.classList.remove('hidden');
        mainContent.classList.remove('voice-hidden');        
        loadClonedVoices();
        updateVoiceStats();
    } else {
        voiceSection.classList.add('hidden');
        mainContent.classList.add('voice-hidden');
        // Arrêter l'enregistrement si en cours
        if (isRecording) {
            stopVoiceRecording();
        }
    }
}

/**
 * Démarre l'enregistrement audio pour le clonage
 */
async function startVoiceRecording() {
    if (isRecording) {
        addLogEntry('⚠️ Enregistrement déjà en cours', 'warning');
        return;
    }
    
    try {
        // Configuration audio optimisée pour le clonage vocal
        const stream = await navigator.mediaDevices.getUserMedia({ 
            audio: {
                channelCount: 1,
                sampleRate: 16000,
                sampleSize: 16,
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            } 
        });
        
        // Créer le MediaRecorder
        const mimeType = MediaRecorder.isTypeSupported('audio/webm') 
            ? 'audio/webm' 
            : 'audio/ogg';
        
        mediaRecorder = new MediaRecorder(stream, { 
            mimeType,
            audioBitsPerSecond: 128000
        });
        
        audioChunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: mimeType });
            const duration = (Date.now() - recordingStartTime) / 1000;
            
            if (duration < 6) {
                showToast('⚠️ Enregistrement trop court (minimum 6 secondes)', 'warning');
                addLogEntry(`⚠️ Audio rejeté: ${duration.toFixed(1)}s (min 6s)`, 'warning');
                pendingAudioData = null;
            } else {
                // Stocker l'audio en attente
                pendingAudioData = {
                    blob: audioBlob,
                    duration: duration,
                    type: 'recording'
                };
                
                showAudioPreview(audioBlob, duration);
                enableSaveButton(true);
                
                addLogEntry(`✅ Enregistrement terminé: ${duration.toFixed(1)}s`, 'success');
                showToast('✅ Enregistrement prêt à être sauvegardé', 'success');
            }
            
            // Libérer le stream
            stream.getTracks().forEach(track => track.stop());
        };
        
        isRecording = true;
        recordingStartTime = Date.now();
        
        mediaRecorder.start();
        startRecordingTimer();
        updateRecordingUI(true);
        
        addLogEntry('🎤 Enregistrement démarré...', 'info');
        showToast('🎤 Parlez clairement pendant 6-30 secondes', 'info');
        
        // Arrêt automatique après 30 secondes
        setTimeout(() => {
            if (isRecording) {
                stopVoiceRecording();
                showToast('⏰ Arrêt automatique (30s max)', 'warning');
            }
        }, 30000);
        
    } catch (error) {
        addLogEntry(`❌ Erreur microphone: ${error.message}`, 'error');
        showToast('❌ Impossible d\'accéder au microphone', 'error');
    }
}

/**
 * Arrête l'enregistrement vocal
 */
function stopVoiceRecording() {
    if (!isRecording || !mediaRecorder) {
        addLogEntry('⚠️ Aucun enregistrement en cours', 'warning');
        return;
    }
    
    try {
        mediaRecorder.stop();
        isRecording = false;
        
        stopRecordingTimer();
        updateRecordingUI(false);
        
        addLogEntry('🛑 Enregistrement arrêté', 'info');
        
    } catch (error) {
        addLogEntry(`❌ Erreur arrêt: ${error.message}`, 'error');
    }
}

/**
 * Gère l'upload de fichier audio/vidéo
 */
async function handleVoiceFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // Vérifier le type de fichier
    const isVideo = file.type.startsWith('video/');
    const isAudio = file.type.startsWith('audio/');
    
    if (!isVideo && !isAudio) {
        showToast('⚠️ Veuillez sélectionner un fichier audio ou vidéo', 'warning');
        event.target.value = ''; // Reset input
        return;
    }
    
    // Vérifier la taille (max 50MB)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
        showToast('⚠️ Fichier trop volumineux (max 50MB)', 'warning');
        event.target.value = '';
        return;
    }
    
    try {
        addLogEntry(`📁 Fichier chargé: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)}MB)`, 'info');
        
        // Lire le fichier en tant qu'ArrayBuffer
        const arrayBuffer = await file.arrayBuffer();
        
        // Stocker en attente de sauvegarde
        pendingAudioData = {
            data: arrayBuffer,
            filename: file.name,
            type: isVideo ? 'video' : 'audio',
            size: file.size
        };
        
        showFileInfo(file.name, file.size, isVideo);
        
        const voiceName = document.getElementById('voice-name-input')?.value?.trim();
        enableSaveButton(voiceName && pendingAudioData);
        
        showToast(
            isVideo 
                ? '✅ Vidéo chargée - audio sera extrait' 
                : '✅ Audio chargé et prêt', 
            'success'
        );
        
    } catch (error) {
        addLogEntry(`❌ Erreur lecture fichier: ${error.message}`, 'error');
        showToast('❌ Erreur lors du chargement du fichier', 'error');
        event.target.value = '';
    }
}

/**
 * Sauvegarde la voix clonée
 */

function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    
    return btoa(binary);
}

async function saveClonedVoice() {
    const voiceName = document.getElementById('voice-name-input')?.value?.trim();
    const voiceDescription = document.getElementById('voice-description-input')?.value?.trim();
    
    // Validation
    if (!voiceName) {
        showToast('⚠️ Nom de la voix requis', 'warning');
        return;
    }
    
    if (!pendingAudioData) {
        showToast('⚠️ Aucun audio en attente de sauvegarde', 'warning');
        return;
    }
    
    // Désactiver l'interface pendant le traitement
    const saveBtn = document.getElementById('save-voice-btn');
    const originalText = saveBtn?.textContent;
    if (saveBtn) saveBtn.textContent = '🔄 Traitement...';

    try {
        addLogEntry(`💾 Création voix: ${voiceName}...`, 'info');
        showToast('🔄 Traitement en cours...', 'info');
        
        let audioData;
        let fileType;
        
        if (pendingAudioData.type === 'recording') {
            // Enregistrement direct
            audioData = await pendingAudioData.blob.arrayBuffer();
            fileType = 'audio';
        } else {
            // Fichier uploadé
            audioData = pendingAudioData.data;
            fileType = pendingAudioData.type;
        }
        
        
        // Encoder en base64
        const base64Audio = arrayBufferToBase64(audioData);
        
        // Envoyer au serveur
        const response = await fetch('/api/voice/clone', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                audio_data: base64Audio,
                voice_name: voiceName,
                description: voiceDescription,
                file_type: fileType
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            addLogEntry(`✅ Voix créée: ${voiceName} (ID: ${result.voice_id})`, 'success');
            showToast(`✅ Voix "${voiceName}" créée avec succès !`, 'success');
            
            // ✅ NOUVEAU - Utiliser le gestionnaire centralisé
            await refreshVoices();
            
            // Reset du formulaire
            resetVoiceForm();
            
        } else {
            throw new Error(result.error || 'Erreur inconnue');
        }
        
    } catch (error) {
        addLogEntry(`❌ Erreur création voix: ${error.message}`, 'error');
        showToast(`❌ Erreur: ${error.message}`, 'error');
    } finally {
        if (saveBtn && originalText) {
            saveBtn.textContent = originalText;
        }
    }
}

/**
 * Charge la liste des voix clonées
 */
async function loadClonedVoices() {
    try {
        const response = await fetch('/api/voice/cloned/list');
        const data = await response.json();
        
        if (data.success) {
            displayClonedVoices(data.voices);
            addLogEntry(`📋 ${data.voices.length} voix clonées chargées`, 'info');
        } else {
            console.error('Erreur API:', data.error);
            displayClonedVoices([]);
        }
    } catch (error) {
        console.error('Erreur chargement voix clonées:', error);
        displayClonedVoices([]);
        addLogEntry(`❌ Erreur: ${error.message}`, 'error');
    }
}

/**
 * Affiche la liste des voix clonées
 */
function displayClonedVoices(voices) {
    const container = document.getElementById('cloned-voices-list');
    if (!container) return;
    
    if (!voices || voices.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>🎭 Aucune voix clonée</p>
                <small>Utilisez l'enregistrement ou l'upload pour créer votre première voix</small>
            </div>
        `;
        return;
    }
    
    // Trier par date de création (plus récent en premier)
    const sortedVoices = voices.sort((a, b) => (b.created_at || 0) - (a.created_at || 0));
    
    container.innerHTML = sortedVoices.map(voice => {
        const isDefault = voice.id === currentVoiceId;
        const statusIcon = voice.status === 'ready' ? '✅' : '⏳';
        const duration = voice.duration ? `${voice.duration.toFixed(1)}s` : 'N/A';
        
        return `
            <div class="voice-item ${isDefault ? 'is-default' : ''}" data-voice-id="${voice.id}">
                <div class="voice-header">
                    <h4>${statusIcon} ${voice.name}</h4>
                    <span class="voice-duration">${duration}</span>
                </div>
                <p class="voice-description">${voice.description || 'Aucune description'}</p>
                <div class="voice-meta">
                    <small>🎯 Modèle: ${voice.model}</small>
                    <small>📅 ${new Date(voice.created_at * 1000).toLocaleDateString()}</small>
                    ${voice.has_embedding ? '<small>⚡ Optimisée</small>' : ''}
                </div>
                <div class="voice-actions">
                    <button onclick="testClonedVoice('${voice.id}')" 
                            class="voice-btn test-btn" 
                            title="Tester cette voix"
                            ${voice.status !== 'ready' ? 'disabled' : ''}>
                        🔊
                    </button>
                    <button onclick="selectClonedVoice('${voice.id}')" 
                            class="voice-btn select-btn" 
                            title="Utiliser cette voix"
                            ${voice.status !== 'ready' || isDefault ? 'disabled' : ''}>
                        ${isDefault ? '✅' : '☑️'}
                    </button>
                    <button onclick="editClonedVoice('${voice.id}')" 
                            class="voice-btn edit-btn" 
                            title="Renommer">
                        ✏️
                    </button>
                    <button onclick="exportClonedVoice('${voice.id}')" 
                            class="voice-btn export-btn" 
                            title="Exporter">
                        💾
                    </button>
                    <button onclick="deleteClonedVoice('${voice.id}')" 
                            class="voice-btn delete-btn" 
                            title="Supprimer">
                        🗑️
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Édite une voix clonée (renommer)
 */
async function editClonedVoice(voiceId) {
    const newName = prompt('Nouveau nom de la voix:');
    const newDesc = prompt('Nouvelle description (optionnel):');
    
    if (!newName || newName.trim() === '') {
        showToast('⚠️ Nom requis', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/api/voice/rename/${voiceId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                new_name: newName.trim(),
                new_description: newDesc?.trim() || ''
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast(`✅ Voix renommée: ${newName}`, 'success');
            await loadClonedVoices();  // Recharger la liste
            // ✅ NOUVEAU - Utiliser le gestionnaire centralisé
            await refreshVoices();
        } else {
            showToast(`❌ Erreur: ${result.error}`, 'error');
        }
    } catch (error) {
        showToast(`❌ Erreur: ${error.message}`, 'error');
    }
}

/**
 * Supprime une voix clonée
 */
async function deleteClonedVoice(voiceId) {
    if (!confirm('⚠️ Êtes-vous sûr de vouloir supprimer cette voix ?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/voice/delete/${voiceId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('✅ Voix supprimée', 'success');
            await loadClonedVoices();  // Recharger la liste
            updateVoiceStats();        // Mettre à jour les stats
            
            // ✅ NOUVEAU - Utiliser le gestionnaire centralisé
            await refreshVoices();
        } else {
            showToast(`❌ Erreur: ${result.error}`, 'error');
        }
    } catch (error) {
        showToast(`❌ Erreur: ${error.message}`, 'error');
    }
}

/**
 * Teste une voix clonée
 */
async function testClonedVoice(voiceId) {
    try {
        showToast('🔊 Test de la voix...', 'info');
        
        const response = await fetch('/api/voice/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                voice_id: voiceId,
                text: document.getElementById('test-text-input')?.value || 
                      "Bonjour, ceci est un test de ma voix clonée. Je peux maintenant parler avec cette voix personnalisée."
            })
        });
        
        if (response.ok) {
            addLogEntry(`🔊 Test voix: ${voiceId}`, 'info');
        } else {
            const error = await response.json();
            showToast(`❌ Erreur: ${error.message || 'Test échoué'}`, 'error');
        }
        
    } catch (error) {
        showToast(`❌ Erreur: ${error.message}`, 'error');
    }
}

/**
 * Sélectionne une voix clonée pour l'utiliser
 */
async function selectClonedVoice(voiceId) {
    try {
        const response = await fetch('/api/voice/set-default', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                voice_id: voiceId
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast(`✅ Voix active: ${result.voice_name}`, 'success');
            
            // Mettre à jour la variable globale
            currentVoiceId = voiceId;
            
            // Mettre à jour l'affichage dans les paramètres
            updatePersonality(`🎭 ${result.voice_name}`);
            
            // Recharger la liste pour mettre à jour l'UI
            await loadClonedVoices();
            
            // ✅ NOUVEAU - Utiliser le gestionnaire centralisé
            await refreshVoices();
            
            // Mettre à jour le sélecteur de voix dans les paramètres
            const voiceSelect = document.getElementById('voice-personality');
            for (let option of voiceSelect.options) {
                const voiceData = voices[option.value];
                if (voiceData && voiceData.voice_id === currentVoiceId) {
                    voiceSelect.value = option.value;
                    break;
                }
            }
            
        } else {
            showToast(`❌ ${result.error}`, 'error');
        }
        
    } catch (error) {
        showToast(`❌ Erreur: ${error.message}`, 'error');
    }
}

/**
 * Édite une voix clonée (renommer)
 */
async function editClonedVoice(voiceId) {
    const newName = prompt('Nouveau nom de la voix:');
    const newDesc = prompt('Nouvelle description (optionnel):');
    
    if (!newName || newName.trim() === '') {
        showToast('⚠️ Nom requis', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`/api/voice/rename/${voiceId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                new_name: newName.trim(),
                new_description: newDesc?.trim() || ''
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast(`✅ Voix renommée: ${newName}`, 'success');
            await loadClonedVoices();  // Recharger la liste
            updateVoiceStats();        // Mettre à jour les stats
        } else {
            showToast(`❌ Erreur: ${result.error}`, 'error');
        }
    } catch (error) {
        showToast(`❌ Erreur: ${error.message}`, 'error');
    }
}

/**
 * Supprime une voix clonée
 */
async function deleteClonedVoice(voiceId) {
    if (!confirm('⚠️ Êtes-vous sûr de vouloir supprimer cette voix ?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/voice/delete/${voiceId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('✅ Voix supprimée', 'success');
            await loadClonedVoices();  // Recharger la liste
            updateVoiceStats();        // Mettre à jour les stats
        } else {
            showToast(`❌ Erreur: ${result.error}`, 'error');
        }
    } catch (error) {
        showToast(`❌ Erreur: ${error.message}`, 'error');
    }
}

/**
 * Met à jour les statistiques des voix
 */
async function updateVoiceStats() {
    try {
        const response = await fetch('/api/voice/stats');
        const data = await response.json();
        
        const statsDiv = document.getElementById('voice-stats');
        if (statsDiv && data.success) {
            statsDiv.innerHTML = `
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-label">Total</span>
                        <span class="stat-value">${data.total_voices}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Clonées</span>
                        <span class="stat-value">${data.cloned_voices}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Stockage</span>
                        <span class="stat-value">${data.storage_used}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Modèle</span>
                        <span class="stat-value">${data.xtts_loaded ? '✅ XTTS' : '⚠️ Edge-TTS'}</span>
                    </div>
                </div>
            `;
        }
    } catch (error) {
        console.error('Erreur stats:', error);
    }
}

// Fonctions utilitaires

/**
 * Active/désactive le bouton de sauvegarde
 */
function enableSaveButton(enabled) {
    console.log('🔍 enableSaveButton appelée');
    const saveBtn = document.getElementById('save-voice-btn');
    if (saveBtn) {
        saveBtn.disabled = !enabled;
        saveBtn.style.opacity = enabled ? '1' : '0.5';
    }
}

/**
 * Affiche l'aperçu audio
 */
function showAudioPreview(blob, duration) {
    const previewDiv = document.getElementById('audio-preview');
    if (!previewDiv) return;
    
    const url = URL.createObjectURL(blob);
    
    previewDiv.innerHTML = `
        <div class="audio-preview-card">
            <h5>📊 Aperçu de l'enregistrement</h5>
            <audio controls src="${url}"></audio>
            <p>Durée: ${duration.toFixed(1)} secondes</p>
        </div>
    `;
    
    previewDiv.style.display = 'block';
}

/**
 * Affiche les infos du fichier uploadé
 */
function showFileInfo(filename, size, isVideo) {
    const previewDiv = document.getElementById('audio-preview');
    if (!previewDiv) return;
    
    const sizeKB = (size / 1024).toFixed(1);
    const sizeMB = (size / (1024 * 1024)).toFixed(2);
    const displaySize = size > 1024 * 1024 ? `${sizeMB} MB` : `${sizeKB} KB`;
    
    previewDiv.innerHTML = `
        <div class="file-info-card">
            <h5>${isVideo ? '🎥' : '🎵'} Fichier chargé</h5>
            <p><strong>Nom:</strong> ${filename}</p>
            <p><strong>Taille:</strong> ${displaySize}</p>
            <p><strong>Type:</strong> ${isVideo ? 'Vidéo' : 'Audio'}</p>
            ${isVideo ? '<p class="info-note">ℹ️ L\'audio sera extrait de la vidéo</p>' : ''}
        </div>
    `;
    
    previewDiv.style.display = 'block';
}

/**
 * Lance le timer d'enregistrement
 */
function startRecordingTimer() {
    let seconds = 0;
    const timerDisplay = document.getElementById('recording-timer');
    
    if (timerDisplay) {
        timerDisplay.style.display = 'inline-block';
    }
    
    recordingTimer = setInterval(() => {
        seconds++;
        if (timerDisplay) {
            timerDisplay.textContent = `${seconds}s / 30s`;
            
            // Changer la couleur selon la durée
            if (seconds < 6) {
                timerDisplay.style.color = '#ff9800'; // Orange
            } else {
                timerDisplay.style.color = '#4caf50'; // Vert
            }
        }
        
        // Indicateur à 6s
        if (seconds === 6) {
            showToast('✅ Durée minimale atteinte', 'success');
        }
    }, 1000);
}

/**
 * Arrête le timer d'enregistrement
 */
function stopRecordingTimer() {
    if (recordingTimer) {
        clearInterval(recordingTimer);
        recordingTimer = null;
    }
    
    const timerDisplay = document.getElementById('recording-timer');
    if (timerDisplay) {
        timerDisplay.style.display = 'none';
        timerDisplay.textContent = '';
        timerDisplay.style.color = '';
    }
}

/**
 * Met à jour l'interface d'enregistrement
 */
function updateRecordingUI(recording) {
    const recordBtn = document.getElementById('record-btn');
    const stopBtn = document.getElementById('stop-record-btn');
    const indicator = document.getElementById('recording-indicator');
    
    if (recording) {
        if (recordBtn) recordBtn.style.display = 'none';
        if (stopBtn) stopBtn.style.display = 'inline-block';
        if (indicator) indicator.classList.add('hidden');
        
        // Désactiver les autres contrôles
        document.querySelectorAll('#cloned-voices-list input, #cloned-voices-list textarea')
            .forEach(input => input.disabled = true);
        
    } else {
        if (recordBtn) recordBtn.style.display = 'inline-block';
        if (stopBtn) stopBtn.style.display = 'none';
        if (indicator) indicator.classList.remove('hidden');
        
        // Réactiver les contrôles
        document.querySelectorAll('#cloned-voices-list input, #cloned-voices-list textarea')
            .forEach(input => input.disabled = false);
    }
}

/**
 * Remet le formulaire à zéro
 */
function resetVoiceForm() {
    // Reset des champs texte
    const nameInput = document.getElementById('voice-name-input');
    const descInput = document.getElementById('voice-description-input');
    const fileInput = document.getElementById('voice-file-input');
    
    if (nameInput) nameInput.value = '';
    if (descInput) descInput.value = '';
    if (fileInput) fileInput.value = '';
    
    // Reset de l'aperçu
    const previewDiv = document.getElementById('audio-preview');
    if (previewDiv) {
        previewDiv.style.display = 'none';
        previewDiv.innerHTML = '';
    }
    
    // Reset des données en attente
    pendingAudioData = null;
    enableSaveButton(false);
    
    addLogEntry('🔄 Formulaire réinitialisé', 'info');
}


/**
 * Initialise les événements du Voice Lab
 */
function initializeVoiceLab() {
    // Connecter l'upload de fichier
    const fileInput = document.getElementById('voice-upload');
    if (fileInput) {
        fileInput.addEventListener('change', handleVoiceFileUpload);
        console.log('✅ Event file upload connecté');
    }
    
    // Validation simple sur le nom
    const nameInput = document.getElementById('voice-name-input');
    if (nameInput) {
        nameInput.addEventListener('input', function() {
            const voiceName = this.value.trim();
            enableSaveButton(voiceName && pendingAudioData);
        });
    }
}

/**
 * Vérifie si le formulaire est valide
 */
function checkFormValidation() {
    const voiceName = document.getElementById('voice-name-input')?.value?.trim();
    const hasAudio = pendingAudioData !== null;
    
    console.log('🔍 Validation:', { voiceName, hasAudio });
    
    const shouldEnable = voiceName && hasAudio;
    
    // ✅ Appel direct sans récursion
    const saveBtn = document.getElementById('save-voice-btn');
    if (saveBtn) {
        saveBtn.disabled = !shouldEnable;
        saveBtn.style.opacity = shouldEnable ? '1' : '0.5';
    }
}

// Chargement initial
document.addEventListener('DOMContentLoaded', () => {
    console.log('🎭 Voice Lab DOM loaded');
    
    // Initialiser les événements
    initializeVoiceLab();
    
    if (voiceVisible) {
        loadClonedVoices();
        updateVoiceStats();
    }
});

console.log('🎭 Voice Lab chargé');
