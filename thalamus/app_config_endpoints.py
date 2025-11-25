"""
api_config_endpoints.py - Endpoints API pour les configurations JSON
À intégrer dans le serveur FastAPI principal pour servir les configurations
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
import sys

# Import du gestionnaire de configuration
sys.path.append(str(Path(__file__).parent.parent))
from thalamus.config_loader import ConfigLoader
from thalamus.interface_bridge import InterfaceBridge
from hypothalamus.logger import log

# Créer le routeur API
config_router = APIRouter(prefix="/api", tags=["configuration"])

# Instances globales
config_loader = ConfigLoader()
interface_bridge = InterfaceBridge()

@config_router.get("/voices")
async def get_voices():
    """Retourne la liste des voix disponibles"""
    try:
        voices_data = interface_bridge.get_available_voices()
        return voices_data
    except Exception as e:
        log.error(f"Erreur API /voices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.get("/models")
async def get_models():
    """Retourne la liste des modèles LLM disponibles"""
    try:
        models_data = interface_bridge.get_available_models()
        return models_data
    except Exception as e:
        log.error(f"Erreur API /models: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.get("/themes")
async def get_themes():
    """Retourne la liste des thèmes disponibles"""
    try:
        themes_data = interface_bridge.get_available_themes()
        return themes_data
    except Exception as e:
        log.error(f"Erreur API /themes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.get("/backgrounds")
async def get_backgrounds():
    """Retourne la liste des arrière-plans disponibles"""
    try:
        backgrounds_data = interface_bridge.get_available_backgrounds()
        return backgrounds_data
    except Exception as e:
        log.error(f"Erreur API /backgrounds: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.get("/demo-text")
async def get_demo_text():
    """Retourne le texte de démonstration pour les voix"""
    try:
        demo_text = config_loader.get_demo_text()
        return {
            "success": True,
            "demo_text": demo_text
        }
    except Exception as e:
        log.error(f"Erreur API /demo-text: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.get("/config/status")
async def get_config_status():
    """Retourne le statut des configurations"""
    try:
        status = interface_bridge.get_config_status()
        return status
    except Exception as e:
        log.error(f"Erreur API /config/status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.post("/reload-config")
async def reload_configurations():
    """Recharge toutes les configurations depuis les fichiers JSON"""
    try:
        result = interface_bridge.reload_configurations()
        log.info("Configurations rechargées via API")
        return result
    except Exception as e:
        log.error(f"Erreur API /reload-config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.get("/voice/{voice_id}")
async def get_voice_config(voice_id: str):
    """Retourne la configuration détaillée d'une voix"""
    try:
        voice_config = config_loader.get_voice_config(voice_id)
        if voice_config:
            return {
                "success": True,
                "voice": voice_config
            }
        else:
            return {
                "success": False,
                "error": f"Voix '{voice_id}' non trouvée"
            }
    except Exception as e:
        log.error(f"Erreur API /voice/{voice_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.get("/model/{model_id}")
async def get_model_config(model_id: str):
    """Retourne la configuration détaillée d'un modèle"""
    try:
        model_config = config_loader.get_model_config(model_id)
        if model_config:
            return {
                "success": True,
                "model": model_config
            }
        else:
            return {
                "success": False,
                "error": f"Modèle '{model_id}' non trouvé"
            }
    except Exception as e:
        log.error(f"Erreur API /model/{model_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.get("/defaults")
async def get_defaults():
    """Retourne toutes les valeurs par défaut"""
    try:
        return {
            "success": True,
            "defaults": {
                "voice": config_loader.get_default_voice(),
                "model": config_loader.get_default_model(),
                "theme": config_loader.get_default_theme(),
                "background": config_loader.get_default_background()
            }
        }
    except Exception as e:
        log.error(f"Erreur API /defaults: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@config_router.get("/config/all")
async def get_all_configs():
    """Retourne toutes les configurations en une seule fois (pour optimisation)"""
    try:
        return {
            "success": True,
            "configurations": {
                "voices": interface_bridge.get_available_voices(),
                "models": interface_bridge.get_available_models(),
                "themes": interface_bridge.get_available_themes(),
                "backgrounds": interface_bridge.get_available_backgrounds(),
                "defaults": {
                    "voice": config_loader.get_default_voice(),
                    "model": config_loader.get_default_model(),
                    "theme": config_loader.get_default_theme(),
                    "background": config_loader.get_default_background()
                },
                "demo_text": config_loader.get_demo_text()
            }
        }
    except Exception as e:
        log.error(f"Erreur API /config/all: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint pour mettre à jour une configuration spécifique
@config_router.post("/config/{config_name}")
async def update_config(config_name: str, config_data: dict):
    """Met à jour une configuration spécifique"""
    try:
        if config_name not in ['voices', 'models', 'themes', 'backgrounds']:
            raise HTTPException(status_code=400, detail=f"Configuration '{config_name}' non supportée")
        
        success = config_loader.save_config(config_name, config_data)
        
        if success:
            return {
                "success": True,
                "message": f"Configuration '{config_name}' mise à jour"
            }
        else:
            return {
                "success": False,
                "error": f"Erreur sauvegarde '{config_name}'"
            }
            
    except Exception as e:
        log.error(f"Erreur API update /config/{config_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Fonction d'initialisation à appeler depuis le serveur principal
def setup_config_routes(app):
    """
    Fonction pour configurer les routes de configuration dans l'app FastAPI principale
    
    Usage dans le serveur principal:
    from api_config_endpoints import setup_config_routes
    setup_config_routes(app)
    """
    app.include_router(config_router)
    log.info("Routes de configuration API configurées")

# Test standalone des endpoints
if __name__ == "__main__":
    import asyncio
    
    async def test_endpoints():
        print("🧪 Test des endpoints de configuration")
        
        try:
            # Test chargement voix
            voices = await get_voices()
            print(f"✅ Voix: {voices['success']}, count: {len(voices.get('voices', []))}")
            
            # Test chargement modèles
            models = await get_models()
            print(f"✅ Modèles: {models['success']}, count: {len(models.get('models', []))}")
            
            # Test chargement thèmes
            themes = await get_themes()
            print(f"✅ Thèmes: {themes['success']}, count: {len(themes.get('themes', []))}")
            
            # Test chargement arrière-plans
            backgrounds = await get_backgrounds()
            print(f"✅ Arrière-plans: {backgrounds['success']}, count: {len(backgrounds.get('backgrounds', []))}")
            
            # Test valeurs par défaut
            defaults = await get_defaults()
            print(f"✅ Défauts: {defaults['success']}")
            if defaults['success']:
                print(f"   Voix: {defaults['defaults']['voice']}")
                print(f"   Modèle: {defaults['defaults']['model']}")
                print(f"   Thème: {defaults['defaults']['theme']}")
            
            # Test texte démo
            demo = await get_demo_text()
            print(f"✅ Demo text: {demo['success']}")
            if demo['success']:
                print(f"   Texte: '{demo['demo_text'][:50]}...'")
            
            # Test statut config
            status = await get_config_status()
            print(f"✅ Statut: {status['success']}")
            
            print("\n✅ Test endpoints terminé avec succès")
            
        except Exception as e:
            print(f"❌ Erreur test endpoints: {e}")
            import traceback
            traceback.print_exc()
    
    # Exécuter le test
    asyncio.run(test_endpoints())