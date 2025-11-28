/**
 * theme-manager.js - Gestion des thèmes de l'interface
 * 🎨 Lobes Occipitaux - Traitement visuel et esthétique
 * 🚀 CORRIGÉ: Background correct + opacité seulement sur l'image
 */

let themesConfig = null;

/**
 * Charge la configuration des thèmes depuis themes.json
 */
function loadThemesConfig() {
    return fetch('config/themes.json')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            themesConfig = data;
            addLogEntry('✅ Configuration thèmes chargée', 'success');
            return true;
        })
        .catch(error => {
            addLogEntry(`❌ Erreur chargement themes.json: ${error.message}`, 'error');
            return false;
        });
}

/**
 * Bascule vers le thème suivant dans le cycle
 */
function toggleTheme() {
    if (!themesConfig?.themes) {
        addLogEntry('Configuration des thèmes non chargée', 'error');
        return;
    }
    
    // Utiliser l'ordre de cycle défini ou les clés par défaut
    const themes = themesConfig.config?.cycle_order || Object.keys(themesConfig.themes);
    const currentIndex = themes.indexOf(currentTheme);
    const nextIndex = (currentIndex + 1) % themes.length;
    
    addLogEntry(`🎨 Passage du thème ${currentTheme} vers ${themes[nextIndex]}`, 'info');
    setTheme(themes[nextIndex]);
}

/**
 * Applique un thème spécifique
 * @param {string} theme - ID du thème à appliquer
 */
function setTheme(theme) {
    if (!themesConfig?.themes?.[theme]) {
        addLogEntry(`❌ Thème inconnu: ${theme}`, 'error');
        return;
    }
    
    // Mettre à jour la variable globale
    currentTheme = theme;
    
    // Appliquer la classe CSS
    document.body.className = `theme-${theme}`;
    
    // Mettre à jour le select des paramètres si ouvert
    const themeSelect = document.getElementById('interface-theme');
    if (themeSelect) {
        themeSelect.value = theme;
    }
    
    // Mettre à jour le bouton de navigation
    updateThemeButton();
    
    // Sauvegarder les préférences
    saveSettings();
    
    // Log du changement
    const themeConfig = themesConfig.themes[theme];
    addLogEntry(`✅ Thème appliqué: ${themeConfig.current_name}`, 'success');
    
    // Émettre un événement personnalisé pour les autres modules
    document.dispatchEvent(new CustomEvent('themeChanged', { 
        detail: { theme, config: themeConfig } 
    }));
}

/**
 * 🚀 CORRIGÉ - Applique un arrière-plan avec stockage pour contrôle opacité
 * @param {string} backgroundPath - Chemin de l'arrière-plan
 */
function setBackground(backgroundPath) {
    console.log('🎨 setBackground appelé avec:', backgroundPath);
    
    // 🚀 FIX: Sélectionner le bon dialogue-section (celui qui contient dialogue-container)
    const dialogueContainer = document.getElementById('dialogue-container');
    if (!dialogueContainer) {
        console.error('❌ dialogue-container introuvable');
        return;
    }
    
    const dialogueSection = dialogueContainer.closest('.dialogue-section');
    if (!dialogueSection) {
        console.error('❌ Zone dialogue parente introuvable');
        return;
    }
    
    console.log('✅ Zone dialogue trouvée (bonne):', dialogueSection);
    
    // Nettoyer ancien arrière-plan
    dialogueSection.style.backgroundImage = '';
    dialogueSection.classList.remove('bg-image');
    dialogueSection.style.removeProperty('--bg-image-url');
    console.log('🧹 Ancien arrière-plan nettoyé');
    
    if (backgroundPath && backgroundPath !== 'default') {
        // Construire le chemin
        let imagePath;
        if (backgroundPath.startsWith('images/')) {
            imagePath = `static/${backgroundPath}`;
        } else {
            imagePath = `static/images/${backgroundPath}`;
        }
        
        console.log('🖼️ Chemin image final:', imagePath);
        
        // 🚀 NOUVEAU: Stocker l'URL dans une CSS custom property
        dialogueSection.style.setProperty('--bg-image-url', `url('${imagePath}')`);
        dialogueSection.classList.add('bg-image');
        
        console.log('✅ Styles CSS appliqués avec custom property');
        
        // Mettre à jour l'indicateur
        //updateBackgroundDisplay(backgroundPath, 'Image sélectionnée');
        
        addLogEntry(`🖼️ Arrière-plan dialogue: ${backgroundPath}`, 'info');
        localStorage.setItem('jarvis-background', backgroundPath);
        
    } else {
        console.log('🎨 Arrière-plan par défaut');
        //updateBackgroundDisplay('default', 'Par défaut');
        addLogEntry('🎨 Arrière-plan par défaut (dialogue)', 'info');
        localStorage.setItem('jarvis-background', 'default');
    }
}


/**
 * 🚀 CORRIGÉ - Met à jour la transparence de l'arrière-plan (utilise custom property)
 * @param {number} opacity - Opacité en pourcentage (10-100)
 */
function setBackgroundOpacity(opacity) {
    const style = document.createElement('style');
    style.id = 'background-opacity-override';
    
    const existing = document.getElementById('background-opacity-override');
    if (existing) existing.remove();
    
    // 🚀 FIX: Utilise la CSS custom property stockée par setBackground
    style.textContent = `
        .dialogue-section.bg-image::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-image: var(--bg-image-url);
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            opacity: ${opacity / 100};
            z-index: 1;
            pointer-events: none;
            border-radius: inherit;
        }
        
        .dialogue-section.bg-image .dialogue-header,
        .dialogue-section.bg-image .dialogue-container {
            position: relative;
            z-index: 2;
        }
    `;
    
    document.head.appendChild(style);
    localStorage.setItem('jarvis-background-opacity', opacity);
    
    console.log(`🎨 Transparence background: ${opacity}%`);
}

/**
 * Charge l'arrière-plan sauvegardé au démarrage (avec opacité)
 */
function loadSavedBackground() {
    const saved = localStorage.getItem('jarvis-background');
    if (saved && saved !== 'default') {
        setBackground(saved);
    }

    const savedopacity = localStorage.getItem('jarvis-background-opacity');
    if (savedopacity) {
        // Appliquer l'opacité après un court délai pour s'assurer que setBackground est terminé
        setTimeout(() => {
            setBackgroundOpacity(parseInt(savedopacity));
        }, 100);
        
        // Mettre à jour le slider dans les paramètres si ouvert
        const opacitySlider = document.getElementById('background-opacity');
        const opacityValue = document.getElementById('background-opacity-value');
        if (opacitySlider) {
            opacitySlider.value = savedopacity;
        }
        if (opacityValue) {
            opacityValue.textContent = savedopacity + '%';
        }
    }
}

/**
 * Met à jour le bouton de thème dans la navigation
 */
function updateThemeButton() {
    const themeIcon = document.getElementById('theme-icon');
    const themeText = document.getElementById('theme-text');

    if (!themesConfig?.themes?.[currentTheme]) {
        addLogEntry('⚠️ Configuration thème manquante pour updateThemeButton', 'warning');
        return;
    }
    
    const themeConfig = themesConfig.themes[currentTheme];
    
    if (themeIcon && themeText) {
        // Afficher l'icône et le nom du PROCHAIN thème
        themeIcon.textContent = themeConfig.next_icon || '🎨';
        themeText.textContent = themeConfig.next_name || 'Changer thème';
        
        // Mettre à jour le titre pour l'accessibilité
        const themeButton = themeText.closest('.nav-btn');
        if (themeButton) {
            themeButton.title = themeConfig.description || `Passer en ${themeConfig.next_name}`;
        }
    }
}

/**
 * Initialise le thème au démarrage de l'application
 * @param {string} defaultTheme - Thème par défaut si aucun n'est sauvegardé
 */
function initializeTheme(defaultTheme = 'light') {
    // Charger le thème sauvegardé ou utiliser le défaut
    const savedSettings = loadSavedSettings();
    const themeToApply = savedSettings?.theme || 
                        themesConfig?.config?.default_theme || 
                        defaultTheme;
    
    addLogEntry(`🎨 Initialisation thème: ${themeToApply}`, 'info');
    setTheme(themeToApply);
}

/**
 * Applique un thème depuis les paramètres
 * @param {string} theme - ID du thème sélectionné
 */
function applyThemeFromSettings(theme) {
    if (theme !== currentTheme) {
        addLogEntry(`🎨 Changement thème depuis paramètres: ${theme}`, 'info');
        setTheme(theme);
    }
}

/**
 * Retourne la configuration du thème actuel
 * @returns {Object|null} Configuration du thème actuel
 */
function getCurrentThemeConfig() {
    return themesConfig?.themes?.[currentTheme] || null;
}

/**
 * Retourne la liste des thèmes disponibles
 * @returns {Array} Liste des thèmes avec leurs informations
 */
function getAvailableThemes() {
    if (!themesConfig?.themes) return [];
    
    return Object.values(themesConfig.themes).map(theme => ({
        id: theme.id,
        name: theme.current_name,
        description: theme.description || `Thème ${theme.current_name}`
    }));
}

/**
 * Vérifie si un thème existe
 * @param {string} themeId - ID du thème à vérifier
 * @returns {boolean} True si le thème existe
 */
function themeExists(themeId) {
    return !!(themesConfig?.themes?.[themeId]);
}

/**
 * Applique un thème temporaire (pour prévisualisation)
 * @param {string} theme - ID du thème à prévisualiser
 */
function previewTheme(theme) {
    if (!themeExists(theme)) return;
    
    // Sauvegarder le thème actuel
    const originalTheme = currentTheme;
    
    // Appliquer temporairement
    document.body.className = `theme-${theme}`;
    
    // Programmer le retour au thème original après 3 secondes
    setTimeout(() => {
        if (currentTheme === originalTheme) {
            document.body.className = `theme-${originalTheme}`;
        }
    }, 3000);
}

/**
 * Initialise les événements liés aux thèmes
 */
function initializeThemeEvents() {
    loadThemesConfig();

    // Gestion du changement depuis les paramètres
    const themeSelect = document.getElementById('interface-theme');
    if (themeSelect) {
        themeSelect.addEventListener('change', (event) => {
            applyThemeFromSettings(event.target.value);
        });
    }
    
    // Gestion du raccourci clavier pour changer de thème
    document.addEventListener('keydown', function(event) {
        if (event.ctrlKey && event.key === 'f') {
            event.preventDefault();
            toggleTheme();
        }
    });
    
    // Écouter les changements de préférences système (optionnel)
    if (window.matchMedia) {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addEventListener('change', function(event) {
            // Optionnel: adapter automatiquement au thème système
            if (themesConfig?.config?.auto_follow_system) {
                const systemTheme = event.matches ? 'dark' : 'light';
                if (themeExists(systemTheme)) {
                    setTheme(systemTheme);
                }
            }
        });
    }
}

// Initialiser les événements dès que le DOM est prêt
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeThemeEvents);
} else {
    initializeThemeEvents();
}
