@echo off
chcp 65001 >nul
echo ╔════════════════════════════════════════╗
echo ║   🤖 JARVIS - Installation Complète    ║
echo ╚════════════════════════════════════════╝
echo.

REM Vérifier les droits administrateur
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ Ce script nécessite les droits administrateur
    echo 💡 Faites un clic droit sur le fichier et "Exécuter en tant qu'administrateur"
    pause
    exit /b 1
)

echo 📋 Vérification des prérequis...
echo.

REM Vérifier Python
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ Python n'est pas installé
    echo 💡 Installez Python depuis : https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python détecté : 
python --version
echo.

REM Vérifier winget
winget --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ winget n'est pas disponible
    echo 💡 Installez "App Installer" depuis le Microsoft Store
    pause
    exit /b 1
)

echo ✅ winget détecté
echo.

REM Vérifier si FFmpeg est déjà installé
echo 🔍 Vérification FFmpeg...
ffmpeg -version >nul 2>&1
if %errorLevel% equ 0 (
    echo ✅ FFmpeg déjà installé
    goto :skip_ffmpeg
)

echo 📥 Installation de FFmpeg...
echo    Cela peut prendre quelques minutes...
winget install "FFmpeg (Essentials Build)" --silent --accept-source-agreements --accept-package-agreements

if %errorLevel% neq 0 (
    echo ⚠️ Installation FFmpeg échouée avec winget
    echo 💡 Vous pouvez l'installer manuellement depuis : https://ffmpeg.org/download.html
    echo 💡 Ajoutez ensuite FFmpeg au PATH système
    pause
    goto :skip_ffmpeg
)

echo ✅ FFmpeg installé
echo.

REM Rafraîchir les variables d'environnement (approximatif)
echo 🔄 Rafraîchissement PATH...
call RefreshEnv.cmd >nul 2>&1

:skip_ffmpeg

REM Vérifier l'environnement virtuel
echo 🔍 Vérification environnement virtuel...
if not exist "venv" (
    echo 📦 Création de l'environnement virtuel...
    python -m venv venv
    if %errorLevel% neq 0 (
        echo ❌ Erreur création environnement virtuel
        pause
        exit /b 1
    )
    echo ✅ Environnement virtuel créé
) else (
    echo ✅ Environnement virtuel existant
)
echo.

REM Activer l'environnement virtuel
echo 🔌 Activation environnement virtuel...
call venv\Scripts\activate.bat
if %errorLevel% neq 0 (
    echo ❌ Erreur activation environnement
    pause
    exit /b 1
)
echo ✅ Environnement activé
echo.

REM Mettre à jour pip
echo 📦 Mise à jour pip...
python -m pip install --upgrade pip
echo.

REM Installer les dépendances Python
echo 📥 Installation des dépendances Python...
echo    Cela peut prendre 5-10 minutes...
echo.

pip install -r requirements.txt

if %errorLevel% neq 0 (
    echo ❌ Erreur installation dépendances
    echo 💡 Vérifiez le fichier requirements.txt
    pause
    exit /b 1
)

echo.
echo ✅ Installation des dépendances terminée
echo.

REM Vérifier les dépendances critiques
echo 🔍 Vérification des modules critiques...

python -c "import fastapi; print('✅ FastAPI')" 2>nul || echo ❌ FastAPI manquant
python -c "import uvicorn; print('✅ Uvicorn')" 2>nul || echo ❌ Uvicorn manquant
python -c "import ollama; print('✅ Ollama')" 2>nul || echo ❌ Ollama manquant
python -c "import edge_tts; print('✅ Edge-TTS')" 2>nul || echo ❌ Edge-TTS manquant
python -c "import TTS; print('✅ Coqui TTS')" 2>nul || echo ❌ Coqui TTS manquant
python -c "import torch; print('✅ PyTorch')" 2>nul || echo ❌ PyTorch manquant
python -c "import whisper; print('✅ Whisper')" 2>nul || echo ❌ Whisper manquant

echo.

REM Créer les dossiers nécessaires
echo 📁 Création des dossiers...
if not exist "config" mkdir config
if not exist "config\cloned_voices" mkdir config\cloned_voices
if not exist "config\cloned_voices\samples" mkdir config\cloned_voices\samples
if not exist "config\cloned_voices\models" mkdir config\cloned_voices\models
echo ✅ Structure de dossiers créée
echo.

REM Vérifier Ollama
echo 🔍 Vérification Ollama...
ollama --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ⚠️ Ollama n'est pas installé
    echo 💡 Installez Ollama depuis : https://ollama.com/download
    echo 💡 Puis téléchargez un modèle : ollama pull llama3.1:8b
    echo.
) else (
    echo ✅ Ollama installé
    echo.
)

echo.
echo ╔════════════════════════════════════════╗
echo ║      ✅ Installation terminée !         ║
echo ╚════════════════════════════════════════╝
echo.
echo 📝 Prochaines étapes :
echo.
echo 1. Si FFmpeg n'est pas dans le PATH, redémarrez le terminal
echo 2. Assurez-vous qu'Ollama est démarré
echo 3. Lancez Jarvis avec : python jarvis.py
echo.
echo 💡 Pour vérifier FFmpeg : ffmpeg -version
echo 💡 Pour vérifier Ollama : ollama list
echo.

pause
