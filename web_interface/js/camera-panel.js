/**
 * camera-panel.js - Panneau de vision par caméra
 * 📷 Interface pour la future intégration vision IA
 * Préparation de l'infrastructure pour analyse d'image
 */

// État du panneau caméra
let cameraStream = null;
let currentCamera = 'user'; // 'user' (face) ou 'environment' (arrière)
let capturedImages = [];
let maxCapturedImages = 5;

/**
 * Toggle le panneau caméra
 */
function toggleCameraPanel() {
    cameraVisible = !cameraVisible;
    updateCameraVisibility();
    
    addLogEntry(`🔍 Camera: ${cameraVisible ? 'activé' : 'désactivé'}`, 'info');
    saveSettings();
}

/**
 * Met à jour la visibilité du panneau de camera
 */
function updateCameraVisibility() {
    const cameraSection = document.getElementById('camera-section');
    const mainContent = document.querySelector('.main-content');
    
    if (!cameraSection || !mainContent) return;
    
    if (cameraVisible) {
        cameraSection.classList.remove('hidden');
        mainContent.classList.remove('camera-hidden');
    } else {
        cameraSection.classList.add('hidden');
        mainContent.classList.add('camera-hidden');
    }
}

/**
 * Démarre la caméra
 */
async function startCamera() {
    try {
        const video = document.getElementById('camera-feed');
        
        if (!video) {
            addLogEntry('⚠️ Élément vidéo non trouvé', 'warning');
            return;
        }
        
        // Configuration de la caméra
        const constraints = {
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: currentCamera
            },
            audio: false
        };
        
        // Demander l'accès à la caméra
        cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
        
        // Attacher le stream à la vidéo
        video.srcObject = cameraStream;
        
        // Attendre que la vidéo soit prête
        video.onloadedmetadata = () => {
            video.play();
            updateCameraInfo();
            enableCameraControls(true);
            addLogEntry(`📷 Caméra activée (${video.videoWidth}x${video.videoHeight})`, 'success');
        };
        
    } catch (error) {
        console.error('Erreur caméra:', error);
        
        let errorMessage = 'Impossible d\'accéder à la caméra';
        
        if (error.name === 'NotAllowedError') {
            errorMessage = 'Accès caméra refusé. Vérifiez les permissions.';
        } else if (error.name === 'NotFoundError') {
            errorMessage = 'Aucune caméra détectée';
        } else if (error.name === 'NotReadableError') {
            errorMessage = 'Caméra déjà utilisée par une autre application';
        }
        
        addLogEntry(`❌ ${errorMessage}`, 'error');
        showToast(`❌ ${errorMessage}`, 'error');
        showCameraError(errorMessage);
    }
}

/**
 * Arrête la caméra
 */
function stopCamera() {
    if (cameraStream) {
        // Arrêter toutes les pistes
        cameraStream.getTracks().forEach(track => {
            track.stop();
        });
        
        cameraStream = null;
        
        // Nettoyer la vidéo
        const video = document.getElementById('camera-feed');
        if (video) {
            video.srcObject = null;
        }
        
        enableCameraControls(false);
        addLogEntry('📷 Caméra désactivée', 'info');
    }
}

/**
 * Bascule entre caméra avant/arrière (mobile)
 */
async function switchCamera() {
    currentCamera = currentCamera === 'user' ? 'environment' : 'user';
    
    stopCamera();
    await startCamera();
    
    addLogEntry(`📷 Basculé vers caméra ${currentCamera === 'user' ? 'avant' : 'arrière'}`, 'info');
}

/**
 * Capture une image de la caméra
 */
function captureImage() {
    const video = document.getElementById('camera-feed');
    const canvas = document.createElement('canvas');
    
    if (!video || !video.srcObject) {
        showToast('⚠️ Caméra non active', 'warning');
        return;
    }
    
    // Définir les dimensions du canvas
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    // Dessiner l'image
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    
    // Effet de flash
    flashEffect();
    
    // Convertir en blob
    canvas.toBlob((blob) => {
        if (blob) {
            // Créer un objet image
            const imageData = {
                id: `img_${Date.now()}`,
                blob: blob,
                url: URL.createObjectURL(blob),
                timestamp: new Date().toISOString(),
                width: canvas.width,
                height: canvas.height
            };
            
            // Ajouter à la liste des captures
            capturedImages.unshift(imageData);
            
            // Limiter le nombre d'images
            if (capturedImages.length > maxCapturedImages) {
                const removed = capturedImages.pop();
                URL.revokeObjectURL(removed.url);
            }
            
            // Afficher la capture
            displayCapturedImage(imageData);
            
            showToast('📸 Image capturée', 'success');
            addLogEntry(`📸 Capture ${imageData.id} (${canvas.width}x${canvas.height})`, 'info');
            
            // Afficher les options d'analyse
            showAnalysisOptions(imageData);
        }
    }, 'image/jpeg', 0.9);
}

/**
 * Effet de flash lors de la capture
 */
function flashEffect() {
    const flash = document.createElement('div');
    flash.className = 'camera-flash';
    document.getElementById('camera-panel')?.appendChild(flash);
    
    setTimeout(() => flash.remove(), 300);
}

/**
 * Affiche une image capturée
 */
function displayCapturedImage(imageData) {
    const container = document.getElementById('captured-images');
    
    if (!container) return;
    
    // Créer l'élément image
    const imageCard = document.createElement('div');
    imageCard.className = 'captured-image-card';
    imageCard.innerHTML = `
        <img src="${imageData.url}" alt="Capture ${imageData.id}">
        <div class="image-overlay">
            <button onclick="analyzeImage('${imageData.id}')" class="mini-btn" title="Analyser">
                🔍
            </button>
            <button onclick="saveImage('${imageData.id}')" class="mini-btn" title="Sauvegarder">
                💾
            </button>
            <button onclick="deleteImage('${imageData.id}')" class="mini-btn" title="Supprimer">
                ❌
            </button>
        </div>
    `;
    
    // Ajouter au début
    if (container.firstChild) {
        container.insertBefore(imageCard, container.firstChild);
    } else {
        container.appendChild(imageCard);
    }
}

/**
 * Affiche les options d'analyse (futures fonctionnalités)
 */
function showAnalysisOptions(imageData) {
    const optionsDiv = document.getElementById('analysis-options');
    
    if (!optionsDiv) return;
    
    optionsDiv.innerHTML = `
        <div class="analysis-card">
            <h4>🔍 Dernière capture</h4>
            <p>Dimensions: ${imageData.width}x${imageData.height}</p>
            <div class="future-features">
                <h5>🚧 Fonctionnalités en développement:</h5>
                <button class="future-btn" disabled onclick="performOCR('${imageData.id}')">
                    📝 Extraire le texte (OCR)
                </button>
                <button class="future-btn" disabled onclick="detectObjects('${imageData.id}')">
                    🎯 Détecter les objets
                </button>
                <button class="future-btn" disabled onclick="describeScene('${imageData.id}')">
                    🖼️ Décrire la scène
                </button>
                <button class="future-btn" disabled onclick="analyzeFaces('${imageData.id}')">
                    👤 Analyse faciale
                </button>
                <button class="future-btn" disabled onclick="readDocument('${imageData.id}')">
                    📄 Lire le document
                </button>
                <button class="future-btn" disabled onclick="translateText('${imageData.id}')">
                    🌐 Traduire le texte
                </button>
            </div>
        </div>
    `;
}

/**
 * Analyse une image (placeholder pour future implémentation)
 */
function analyzeImage(imageId) {
    const image = capturedImages.find(img => img.id === imageId);
    
    if (!image) {
        showToast('⚠️ Image non trouvée', 'warning');
        return;
    }
    
    showToast('🔍 Analyse d\'image (fonctionnalité en développement)', 'info');
    addLogEntry(`🔍 Demande d'analyse pour ${imageId} (non implémenté)`, 'info');
    
    // Simuler une analyse
    setTimeout(() => {
        showToast('ℹ️ L\'analyse d\'image sera bientôt disponible', 'info');
    }, 1000);
}

/**
 * Sauvegarde une image capturée
 */
function saveImage(imageId) {
    const image = capturedImages.find(img => img.id === imageId);
    
    if (!image) {
        showToast('⚠️ Image non trouvée', 'warning');
        return;
    }
    
    // Créer un lien de téléchargement
    const a = document.createElement('a');
    a.href = image.url;
    a.download = `capture_${imageId}.jpg`;
    a.click();
    
    showToast('💾 Image sauvegardée', 'success');
    addLogEntry(`💾 Image ${imageId} téléchargée`, 'info');
}

/**
 * Supprime une image capturée
 */
function deleteImage(imageId) {
    const index = capturedImages.findIndex(img => img.id === imageId);
    
    if (index === -1) return;
    
    // Libérer l'URL
    URL.revokeObjectURL(capturedImages[index].url);
    
    // Supprimer de la liste
    capturedImages.splice(index, 1);
    
    // Supprimer de l'affichage
    const container = document.getElementById('captured-images');
    if (container) {
        const cards = container.querySelectorAll('.captured-image-card');
        if (cards[capturedImages.length]) {
            cards[capturedImages.length].remove();
        }
    }
    
    showToast('🗑️ Image supprimée', 'info');
}

/**
 * Active/désactive les contrôles caméra
 */
function enableCameraControls(enabled) {
    const controls = document.querySelectorAll('.camera-controls button:not(.always-enabled)');
    controls.forEach(btn => {
        btn.disabled = !enabled;
    });
}

/**
 * Met à jour les informations de la caméra
 */
function updateCameraInfo() {
    const video = document.getElementById('camera-feed');
    const infoDiv = document.getElementById('camera-info');
    
    if (!video || !infoDiv) return;
    
    const track = cameraStream?.getVideoTracks()[0];
    const settings = track?.getSettings();
    
    if (settings) {
        infoDiv.innerHTML = `
            <div class="camera-stats">
                <span>📹 ${settings.width}x${settings.height}</span>
                <span>🎯 ${settings.frameRate?.toFixed(0) || 30} FPS</span>
                <span>📱 ${settings.facingMode || currentCamera}</span>
            </div>
        `;
    }
}

/**
 * Affiche l'état de développement des fonctionnalités
 */
function showCameraDevStatus() {
    const statusDiv = document.getElementById('camera-dev-status');
    
    if (!statusDiv) return;
    
    statusDiv.innerHTML = `
        <div class="dev-status">
            <h3>🚧 Vision IA - En Développement</h3>
            <p>La reconnaissance visuelle arrive bientôt !</p>
            
            <div class="feature-roadmap">
                <h4>📅 Roadmap des fonctionnalités:</h4>
                
                <div class="feature-section">
                    <h5>✅ Disponible</h5>
                    <ul>
                        <li>Accès caméra (avant/arrière)</li>
                        <li>Capture d'image haute résolution</li>
                        <li>Sauvegarde locale des captures</li>
                        <li>Prévisualisation en temps réel</li>
                    </ul>
                </div>
                
                <div class="feature-section">
                    <h5>🔄 En cours</h5>
                    <ul>
                        <li>OCR - Extraction de texte</li>
                        <li>Détection d'objets basique</li>
                        <li>Analyse de documents</li>
                    </ul>
                </div>
                
                <div class="feature-section">
                    <h5>📋 Planifié</h5>
                    <ul>
                        <li>Description de scène (GPT-4 Vision)</li>
                        <li>Traduction visuelle en temps réel</li>
                        <li>Reconnaissance de codes QR/barres</li>
                        <li>Analyse d'émotions (opt-in)</li>
                        <li>Détection de mouvements</li>
                        <li>Réalité augmentée simple</li>
                    </ul>
                </div>
            </div>
            
            <div class="dev-note">
                <p>💡 <strong>Note:</strong> Les fonctionnalités d'IA nécessiteront:</p>
                <ul>
                    <li>Installation de modèles spécifiques (YOLO, Tesseract)</li>
                    <li>Configuration GPU recommandée pour performances</li>
                    <li>Connexion API pour certaines analyses avancées</li>
                </ul>
            </div>
        </div>
    `;
}

/**
 * Affiche une erreur caméra
 */
function showCameraError(message) {
    const video = document.getElementById('camera-feed');
    const container = video?.parentElement;
    
    if (container) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'camera-error';
        errorDiv.innerHTML = `
            <div class="error-content">
                <h3>❌ Erreur Caméra</h3>
                <p>${message}</p>
                <button onclick="retryCamera()" class="retry-btn">
                    🔄 Réessayer
                </button>
            </div>
        `;
        
        container.appendChild(errorDiv);
    }
}

/**
 * Réessaye de démarrer la caméra
 */
async function retryCamera() {
    const errorDiv = document.querySelector('.camera-error');
    if (errorDiv) {
        errorDiv.remove();
    }
    
    await startCamera();
}

/**
 * Applique des filtres à la vidéo (fun feature)
 */
let currentFilter = 0;
const filters = [
    'none',
    'grayscale(100%)',
    'sepia(100%)',
    'contrast(150%)',
    'brightness(150%)',
    'hue-rotate(90deg)',
    'hue-rotate(180deg)',
    'invert(100%)',
    'blur(3px)',
    'saturate(200%)'
];

function toggleCameraFilters() {
    const video = document.getElementById('camera-feed');
    
    if (!video) return;
    
    currentFilter = (currentFilter + 1) % filters.length;
    video.style.filter = filters[currentFilter];
    
    const filterName = filters[currentFilter] === 'none' ? 'Aucun' : filters[currentFilter];
    showToast(`🎨 Filtre: ${filterName}`, 'info');
}

/**
 * Nettoie les ressources au déchargement
 */
function cleanupCameraResources() {
    stopCamera();
    
    // Libérer les URLs des images
    capturedImages.forEach(img => {
        URL.revokeObjectURL(img.url);
    });
    
    capturedImages = [];
}

/**
 * Initialisation au chargement de la page
 */
document.addEventListener('DOMContentLoaded', () => {
    // Vérifier le support de getUserMedia
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        const panel = document.getElementById('camera-panel');
        if (panel) {
            panel.innerHTML = `
                <div class="no-camera-support">
                    <h3>❌ Caméra non supportée</h3>
                    <p>Votre navigateur ne supporte pas l'accès à la caméra.</p>
                    <p>Utilisez un navigateur moderne (Chrome, Firefox, Edge).</p>
                </div>
            `;
        }
    }
    
    // Nettoyer à la fermeture
    window.addEventListener('beforeunload', cleanupCameraResources);
});

// Export pour utilisation externe
if (typeof window !== 'undefined') {
    window.CameraPanel = {
        toggle: toggleCameraPanel,
        capture: captureImage,
        switchCamera: switchCamera,
        applyFilter: toggleCameraFilters,
        getCapturedImages: () => capturedImages
    };
}