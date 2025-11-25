"""
config_api.py - API REST unifiée pour la configuration
🎯 Remplace tous les endpoints config séparés
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from config_manager import config, get_config, update_config

# Router API
router = APIRouter(prefix="/api/config", tags=["config"])

# Modèles Pydantic
class ConfigUpdate(BaseModel):
    config: Dict[str, Any]

class VoiceConfig(BaseModel):
    personality: str
    tts_model: str
    edge_voice: Optional[str] = None
    sample_path: Optional[str] = None
    embedding_path: Optional[str] = None

class InterfaceConfig(BaseModel):
    theme: Optional[str] = None
    background: Optional[str] = None
    background_opacity: Optional[int] = None

class LLMConfig(BaseModel):
    model: Optional[str] = None
    temperature: Optional[float] = None
    role: Optional[str] = None

# === ENDPOINTS LECTURE ===

@router.get("/")
async def get_full_config():
    """Retourne la configuration complète (remplace /api/config ancien)"""
    try:
        config = get_config()
        return {
            "success": True,
            "config": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lecture config: {e}")

@router.get("/voice")
async def get_voice_config():
    """Configuration voix (remplace /api/voice/current)"""
    try:
        voice_config = config.get_voice_config()
        return {
            "success": True,
            "voice_id": voice_config.get('personality'),
            "personality": voice_config.get('personality'),
            "tts_model": voice_config.get('tts_model'),
            "voice_config": voice_config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur config voix: {e}")

@router.get("/interface")
async def get_interface_config():
    """Configuration interface"""
    try:
        interface_config = config.get_interface_config()
        return {
            "success": True,
            "config": interface_config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur config interface: {e}")

@router.get("/llm")
async def get_llm_config():
    """Configuration LLM"""
    try:
        llm_config = config.get_llm_config()
        return {
            "success": True,
            "config": llm_config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur config LLM: {e}")

# === ENDPOINTS ÉCRITURE ===

@router.post("/update")
async def update_full_config(request: ConfigUpdate):
    """
    Mise à jour générique (remplace WebSocket config_update)
    """
    try:
        success = update_config(request.config)
        if success:
            return {
                "success": True,
                "message": f"Configuration mise à jour: {list(request.config.keys())}",
                "config": get_config()
            }
        else:
            raise HTTPException(status_code=400, detail="Erreur mise à jour config")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")

@router.post("/voice")
async def update_voice_config(voice_config: VoiceConfig):
    """Mise à jour voix (remplace /api/voice/set-default)"""
    try:
        updates = {
            "voice": {
                "personality": voice_config.personality,
                "display_name": voice_config.personality,
                "tts_model": voice_config.tts_model,
                "edge_voice": voice_config.edge_voice,
                "sample_path": voice_config.sample_path,
                "embedding_path": voice_config.embedding_path
            }
        }
        
        success = update_config(updates)
        if success:
            return {
                "success": True,
                "message": f"Voix mise à jour: {voice_config.personality}",
                "voice_name": voice_config.personality
            }
        else:
            raise HTTPException(status_code=400, detail="Erreur mise à jour voix")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")

@router.post("/interface")
async def update_interface_config(interface_config: InterfaceConfig):
    """Mise à jour interface"""
    try:
        updates = {"interface": {}}
        
        if interface_config.theme:
            updates["interface"]["theme"] = interface_config.theme
        if interface_config.background:
            updates["interface"]["background"] = interface_config.background
        if interface_config.background_opacity is not None:
            updates["interface"]["background_opacity"] = interface_config.background_opacity
        
        success = update_config(updates)
        if success:
            return {
                "success": True,
                "message": "Interface mise à jour",
                "config": config.get_interface_config()
            }
        else:
            raise HTTPException(status_code=400, detail="Erreur mise à jour interface")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")

@router.post("/llm")
async def update_llm_config(llm_config: LLMConfig):
    """Mise à jour LLM"""
    try:
        updates = {"llm": {}}
        
        if llm_config.model:
            updates["llm"]["model"] = llm_config.model
        if llm_config.temperature is not None:
            updates["llm"]["temperature"] = llm_config.temperature
        if llm_config.role:
            updates["llm"]["role"] = llm_config.role
        
        success = update_config(updates)
        if success:
            return {
                "success": True,
                "message": "LLM mis à jour",
                "config": config.get_llm_config()
            }
        else:
            raise HTTPException(status_code=400, detail="Erreur mise à jour LLM")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {e}")

# === ENDPOINTS DE COMPATIBILITÉ ===

@router.get("/backgrounds") 
async def get_backgrounds():
    """Compatibilité avec ancien /api/backgrounds"""
    # TODO: Scanner le dossier images/ ou utiliser une liste fixe
    return {
        "success": True,
        "backgrounds": [
            {"name": "Par défaut", "path": "default", "filename": None},
            {"name": "Jarvis", "path": "images/Jarvis.jpeg", "filename": "Jarvis.jpeg"},
            {"name": "One Piece", "path": "images/One_piece.jpg", "filename": "One_piece.jpg"},
            {"name": "Samatha", "path": "images/Samatha.jpeg", "filename": "Samatha.jpeg"}
        ]
    }

@router.get("/models")
async def get_models():
    """Compatibilité - retourne modèles disponibles"""
    # TODO: Scanner Ollama ou utiliser liste fixe
    return {
        "success": True,
        "models": ["llama3.1:8b", "qwen2.5:7b", "mistral:7b"]
    }

# Fonction d'initialisation
def register_config_api(app):
    """Enregistre l'API unifiée dans FastAPI"""
    app.include_router(router)
    print("✅ API configuration unifiée enregistrée")

if __name__ == "__main__":
    print("✅ API config unifiée prête")
