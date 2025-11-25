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
    config_coordinator = None
    conversation_flow = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Gestionnaire de cycle de vie FastAPI"""
        # Startup minimal pour éviter les blocages
        print(f"{Fore.BLUE}🚀 Démarrage FastAPI (initialisation différée)...{Style.RESET_ALL}")
        
        # Variables globales mises à jour mais pas initialisées ici
        nonlocal websocket_relay, config_coordinator, conversation_flow
        
        print(f"{Fore.GREEN}✅ Serveur prêt (modules chargés à la première connexion){Style.RESET_ALL}")
        
        yield  # Application en cours
        
        # Shutdown
        print(f"{Fore.YELLOW}🛑 Arrêt du serveur...{Style.RESET_ALL}")
        if websocket_relay:
            await websocket_relay.shutdown()

    # Fonction d'initialisation différée (appelée au premier WebSocket)
    def init_modules_lazy():
        """Initialisation paresseuse des modules"""
        nonlocal websocket_relay, config_coordinator, conversation_flow
        
        if websocket_relay is None:  # Première fois
            print(f"{Fore.CYAN}🔧 Initialisation différée des modules...{Style.RESET_ALL}")
            
            from thalamus.websocket_relay import WebSocketRelay
            from hypothalamus.config_coordinator import ConfigCoordinator
            from lobes_temporaux.conversation_flow import ConversationFlow
            
            websocket_relay = WebSocketRelay()
            config_coordinator = ConfigCoordinator()
            conversation_flow = ConversationFlow()
            
            config_coordinator.set_conversation_flow(conversation_flow)
            
            print(f"{Fore.GREEN}✅ Modules initialisés !{Style.RESET_ALL}")
        
        return websocket_relay, config_coordinator, conversation_flow

    # Créer l'application
    app = FastAPI(title="Jarvis Assistant - Architecture Neuroanatomique", lifespan=lifespan)

    # Servir les fichiers statiques
    app.mount("/static", StaticFiles(directory="web_interface"), name="static")

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
    url = "http://localhost:8000"
    
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