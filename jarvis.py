"""
jarvis.py - Point d'entrée unifié (Interface Web)
Lance automatiquement l'interface web et ouvre le navigateur
"""

import sys
import time
import webbrowser
import threading
from pathlib import Path
import uvicorn
from colorama import init, Fore, Style
from cortex_prefrontal.model_manager import ModelManager
import asyncio
import json
from typing import Dict, Any


# Initialiser colorama
init()

def print_banner():
    """Bannière Jarvis avec info web"""
    print(f"""{Fore.CYAN}
╔═══════════════════════════════════╗
║         🤖 JARVIS v0.2            ║
║    Assistant Vocal Intelligent    ║
║     Interface Web Unifiée         ║
╚═══════════════════════════════════╝
{Style.RESET_ALL}""")

def check_dependencies():
    """Vérifier que toutes les dépendances sont installées"""
    missing = []
    
    try:
        import fastapi
    except ImportError:
        missing.append("fastapi")
    
    try:
        import uvicorn
    except ImportError:
        missing.append("uvicorn")
    
    try:
        import ollama
    except ImportError:
        missing.append("ollama")
    
    if missing:
        print(f"{Fore.RED}❌ Dépendances manquantes: {', '.join(missing)}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💡 Installez avec: pip install {' '.join(missing)}{Style.RESET_ALL}")
        return False
    
    return True

def check_ollama_running():
    """Vérifier qu'Ollama est démarré"""
    try:
        import ollama
        models = ollama.list()
        print(f"{Fore.GREEN}✅ Ollama connecté ({len(models.get('models', []))} modèles){Style.RESET_ALL}")
        return True
    except Exception as e:
        print(f"{Fore.RED}❌ Ollama non accessible: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💡 Démarrez Ollama puis relancez Jarvis{Style.RESET_ALL}")
        return False

def open_browser_delayed(url: str, delay: float = 2.0):
    """Ouvre le navigateur après un délai"""
    time.sleep(delay)
    try:
        webbrowser.open(url)
        print(f"{Fore.GREEN}🌐 Navigateur ouvert sur {url}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️ Impossible d'ouvrir le navigateur: {e}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}💡 Ouvrez manuellement: {url}{Style.RESET_ALL}")

def create_web_app():
    """Crée l'application FastAPI"""
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    from contextlib import asynccontextmanager

    # Variables globales pour les gestionnaires
    websocket_relay = None
    interface_bridge = None
    config_coordinator = None
    conversation_flow = None

    # Gestionnaire de modèles
    model_manager = ModelManager()

    # Gestionnaire de clonage vocal
    from lobes_temporaux.voice_cloner import VoiceCloner
    voice_cloner = VoiceCloner()
    print(f"{Fore.GREEN}🎭 Voice Cloner initialisé{Style.RESET_ALL}")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Gestionnaire de cycle de vie FastAPI"""
        # Startup minimal pour éviter les blocages
        print(f"{Fore.BLUE}🚀 Démarrage FastAPI (initialisation différée)...{Style.RESET_ALL}")
        
        # NOUVEAU : Initialiser le gestionnaire de modèles
        print(f"{Fore.GREEN}🧠 Gestionnaire de modèles initialisé{Style.RESET_ALL}")
        
        # Variables globales mises à jour mais pas initialisées ici
        nonlocal websocket_relay, interface_bridge, config_coordinator, conversation_flow
        yield
        print(f"{Fore.YELLOW}🛑 Arrêt FastAPI...{Style.RESET_ALL}")

    app = FastAPI(lifespan=lifespan)

    @app.get("/api/models/status")
    async def get_models_status():
        """Retourne le statut de tous les modèles"""
        try:
            status = model_manager.get_model_status()
            return {"success": True, "data": status}
        except Exception as e:
            print(f"{Fore.RED}❌ Erreur API models status: {e}{Style.RESET_ALL}")
            return {"success": False, "error": str(e)}
    
    @app.post("/api/models/install/{model_id}")
    async def install_model(model_id: str):
        """Lance l'installation d'un modèle"""
        try:
            if model_manager.is_model_available(model_id):
                return {"success": False, "error": "Modèle déjà installé"}
            
            # Lancer l'installation en arrière-plan
            asyncio.create_task(model_manager.download_model(model_id))
            
            print(f"{Fore.BLUE}📥 Installation {model_id} lancée{Style.RESET_ALL}")
            return {
                "success": True, 
                "message": f"Installation de {model_id} lancée",
                "model_id": model_id
            }
        except Exception as e:
            print(f"{Fore.RED}❌ Erreur API install model {model_id}: {e}{Style.RESET_ALL}")
            return {"success": False, "error": str(e)}
    
    @app.post("/api/models/switch/{model_id}")
    async def switch_model(model_id: str):
        """Bascule vers un modèle différent"""
        try:
            if not model_manager.is_model_available(model_id):
                return {"success": False, "error": f"Modèle {model_id} non installé"}
            
            success = model_manager.set_current_model(model_id)
            
            if success:
                print(f"{Fore.GREEN}✅ Basculé vers {model_id}{Style.RESET_ALL}")
                return {
                    "success": True,
                    "message": f"Basculé vers {model_id}",
                    "current_model": model_id
                }
            else:
                return {"success": False, "error": f"Échec du basculement vers {model_id}"}
                
        except Exception as e:
            print(f"{Fore.RED}❌ Erreur API switch model {model_id}: {e}{Style.RESET_ALL}")
            return {"success": False, "error": str(e)}
    
    @app.get("/api/models/current")
    async def get_current_model():
        """Retourne le modèle actuellement utilisé"""
        try:
            current = model_manager.get_current_model()
            return {
                "success": True,
                "current_model": current,
                "available": model_manager.is_model_available(current) if current else False
            }
        except Exception as e:
            print(f"{Fore.RED}❌ Erreur API current model: {e}{Style.RESET_ALL}")
            return {"success": False, "error": str(e)}

    # Fonction d'initialisation différée (appelée au premier WebSocket)
    def init_modules_lazy():
        """Initialisation paresseuse des modules"""
        nonlocal websocket_relay, interface_bridge, config_coordinator, conversation_flow
        
        if websocket_relay is None:  # Première fois
            print(f"{Fore.CYAN}🔧 Initialisation différée des modules...{Style.RESET_ALL}")
            
            from thalamus.websocket_relay import WebSocketRelay
            from thalamus.interface_bridge import InterfaceBridge
            from hypothalamus.config_coordinator import ConfigCoordinator
            from lobes_temporaux.conversation_flow import ConversationFlow
            
            websocket_relay = WebSocketRelay()
            interface_bridge = InterfaceBridge()
            conversation_flow = ConversationFlow() 
            config_coordinator = ConfigCoordinator(conversation_flow)
            
            
            print(f"{Fore.GREEN}✅ Modules initialisés !{Style.RESET_ALL}")
        
        return websocket_relay, config_coordinator, conversation_flow

    # Créer l'application
    app = FastAPI(title="Jarvis Assistant - Architecture Neuroanatomique", lifespan=lifespan)

    # Servir les fichiers statiques
    app.mount("/static", StaticFiles(directory="web_interface"), name="static")
    app.mount("/config", StaticFiles(directory="config"), name="config")

    # Routes principales
    @app.get("/")
    async def root():
        """Page principale"""
        return FileResponse('web_interface/index.html')

    # Routes API - Délégation selon architecture neuroanatomique
    @app.get("/api/config")
    async def get_config():
        """Configuration actuelle (Hypothalamus)"""
        try:
            _, coordinator, _ = init_modules_lazy()
            if coordinator:
                return coordinator.get_current_config()
            return {"error": "Config coordinator non initialisé"}
        except Exception as e:
            return {"error": f"Erreur: {e}"}

    @app.post("/api/config")
    async def update_config(config: dict):
        """Mettre à jour la configuration (Hypothalamus)"""
        try:
            _, coordinator, _ = init_modules_lazy()
            if coordinator:
                return await coordinator.update_config(config)
            return {"error": "Config coordinator non initialisé"}
        except Exception as e:
            return {"error": f"Erreur: {e}"}

    @app.get("/api/conversation")
    async def get_conversation():
        """Historique de conversation (Lobes Temporaux)"""
        try:
            _, _, flow = init_modules_lazy()
            if flow:
                return flow.get_history()
            return {"error": "Conversation flow non initialisé"}
        except Exception as e:
            return {"error": f"Erreur: {e}"}

    @app.delete("/api/conversation")
    async def clear_conversation():
        """Effacer l'historique (Lobes Temporaux)"""
        try:
            _, _, flow = init_modules_lazy()
            if flow:
                return flow.clear_history()
            return {"error": "Conversation flow non initialisé"}
        except Exception as e:
            return {"error": f"Erreur: {e}"}

    @app.get("/api/voices")
    async def get_available_voices():
        """Voix disponibles (Hypothalamus)"""
        try:
            _, coordinator, _ = init_modules_lazy()
            if coordinator:
                return coordinator.get_available_voices()
            return {"error": "Config coordinator non initialisé"}
        except Exception as e:
            return {"error": f"Erreur: {e}"}
    
    @app.get("/api/models")
    async def get_models():
        try:
            status = model_manager.get_model_status()
            installed_models = [
                model_id for model_id, model_info in status['models'].items() 
                if model_info.get('installed', False)
            ]
            return {
                "success": True,
                "models": installed_models,
                "current_model": status.get('current_model')
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        
    @app.get("/api/devices")
    async def get_available_devices():
        """Périphériques audio disponibles (Hypothalamus)"""
        try:
            _, coordinator, _ = init_modules_lazy()
            if coordinator:
                return coordinator.get_available_devices()
            return {"error": "Config coordinator non initialisé"}
        except Exception as e:
            return {"error": f"Erreur: {e}"}

    @app.get("/api/backgrounds")
    async def get_backgrounds():
        """Endpoint pour récupérer la liste des arrière-plans"""
        # Vérifier si les modules sont initialisés
        if interface_bridge is None:
            # Initialisation lazy si nécessaire
            _, _, _ = init_modules_lazy()
        
        return interface_bridge.get_available_backgrounds()

    # WebSocket - Thalamus (Hub communication)
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket principal - Thalamus relay avec initialisation différée"""
        try:
            # Initialisation différée des modules
            relay, coordinator, flow = init_modules_lazy()
            
            if not all([relay, coordinator, flow]):
                await websocket.close(code=1011, reason="Modules neuroanatomiques non initialisés")
                return
            
            await relay.handle_connection(
                websocket, 
                flow,        # Lobes temporaux
                coordinator  # Hypothalamus
            )
        except WebSocketDisconnect:
            pass  # Déconnexion normale
        except Exception as e:
            print(f"{Fore.RED}❌ Erreur Thalamus WebSocket: {e}{Style.RESET_ALL}")

    # Routes Voice Lab
    @app.post("/api/voice/clone")
    async def clone_voice(request: dict):
        """Clone une voix à partir d'un échantillon audio"""
        try:
            import base64
            
            # Décoder l'audio base64
            audio_data = base64.b64decode(request['audio_data'])
            
            result = await voice_cloner.clone_voice(
                audio_data=audio_data,
                voice_name=request['voice_name'],
                description=request.get('description', ''),
                file_type=request.get('file_type', 'audio')
            )
            
            return result
            
        except Exception as e:
            log.error(f"Erreur clonage voix: {e}")
            return {"success": False, "error": str(e)}

    @app.get("/api/voice/cloned/list")
    async def list_cloned_voices():
        """Liste uniquement les voix clonées"""
        try:
            voices = voice_cloner.list_cloned_voices()
            return {"success": True, "voices": voices}
        except Exception as e:
            return {"success": False, "error": str(e), "voices": []}

    @app.get("/api/voice/all/list")
    async def list_all_voices():
        """Liste toutes les voix (prédéfinies + clonées)"""
        try:
            result = voice_cloner.get_all_voices()
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.post("/api/voice/test")
    async def test_voice(request: dict):
        """Teste une voix avec du texte"""
        try:
            voice_id = request['voice_id']
            text = request.get('text', 'Test de voix')
            
            # Synthétiser l'audio
            audio_data = await voice_cloner.synthesize_with_voice(text, voice_id)
            
            if audio_data:
                # Jouer l'audio via TTS existant
                from lobes_temporaux.tts import TextToSpeech
                tts = TextToSpeech()
                
                # Sauvegarder temporairement et jouer
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as f:
                    f.write(audio_data)
                    temp_path = f.name
                
                tts.play_audio_file(temp_path)
                
                # Nettoyer
                import os
                os.remove(temp_path)
                
                return {"success": True}
            else:
                return {"success": False, "error": "Synthèse échouée"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.post("/api/voice/set-default")
    async def set_default_voice(request: dict):
        """Définit la voix par défaut"""
        try:
            voice_id = request['voice_id']
            result = voice_cloner.set_default_voice(voice_id)
            
            if result['success']:
                # Mettre à jour la conversation flow
                _, _, conversation_flow = init_modules_lazy()
                if conversation_flow:
                    # Recharger le TTS avec la nouvelle voix
                    voice_config = voice_cloner.voices_config['cloned_voices'].get(voice_id)
                    if not voice_config:
                        voice_config = voice_cloner.voices_config['voices'].get(voice_id)
                    
                    if voice_config:
                        await conversation_flow.reload_tts(
                            voice_config.get('model', 'edge-tts'),
                            voice_config['name'],
                            voice_config.get('edge_voice')
                        )
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.put("/api/voice/rename/{voice_id}")
    async def rename_voice(voice_id: str, request: dict):
        """Renomme une voix clonée"""
        try:
            result = voice_cloner.rename_voice(
                voice_id,
                request['new_name'],
                request.get('new_description')
            )
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.delete("/api/voice/delete/{voice_id}")
    async def delete_voice(voice_id: str):
        """Supprime une voix clonée"""
        try:
            return voice_cloner.delete_voice(voice_id)
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.get("/api/voice/stats")
    async def get_voice_stats():
        """Retourne les statistiques des voix"""
        try:
            status = voice_cloner.get_status()
            return {"success": True, **status}
        except Exception as e:
            return {"success": False, "error": str(e)}

    return app

def main():
    """Point d'entrée principal"""
    print_banner()
    
    # Vérifications préalables
    print(f"{Fore.BLUE}🔍 Vérification des prérequis...{Style.RESET_ALL}")
    
    if not check_dependencies():
        return 1
    
    if not check_ollama_running():
        return 1
    
    # Créer l'application web
    app = create_web_app()
    
    # URL de l'interface
    url = f"http://localhost:8000"
    
    # Programmer l'ouverture du navigateur
    browser_thread = threading.Thread(
        target=open_browser_delayed, 
        args=(url, 3.0),
        daemon=True
    )
    browser_thread.start()
    
    # Démarrer le serveur
    print(f"{Fore.BLUE}🌐 Démarrage de l'interface web...{Style.RESET_ALL}")
    print(f"{Fore.GREEN}📍 Interface accessible sur: {url}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}💡 Le navigateur va s'ouvrir automatiquement{Style.RESET_ALL}")
    print(f"{Fore.CYAN}🔄 Appuyez Ctrl+C pour arrêter{Style.RESET_ALL}\n")
    
    try:
        # Lancer uvicorn
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=8000,
            log_level="error",  # Moins verbeux
            access_log=False    # Pas de logs d'accès
        )
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}🛑 Arrêt demandé par l'utilisateur{Style.RESET_ALL}")
        print(f"{Fore.GREEN}👋 Au revoir !{Style.RESET_ALL}")
        return 0
    except Exception as e:
        print(f"\n{Fore.RED}❌ Erreur fatale: {e}{Style.RESET_ALL}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)