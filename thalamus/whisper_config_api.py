"""
API pour gestion dynamique de la configuration Whisper
Permet l'ajustement en live depuis l'interface web
"""

from flask import Blueprint, request, jsonify
from pathlib import Path
import json
from typing import Dict, Any, Optional

# Import logger
import sys
sys.path.append(str(Path(__file__).parent.parent))
from hypothalamus.logger import log

# Blueprint pour les endpoints Whisper
whisper_bp = Blueprint('whisper_config', __name__)

class WhisperConfigManager:
    """Gestionnaire de configuration Whisper pour l'API"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / "whisper_config.json"
        
        self.config_path = Path(config_path)
        self.stt_instance = None  # Référence vers l'instance STT active
    
    def set_stt_instance(self, stt_instance):
        """Définit l'instance STT à notifier lors des changements"""
        self.stt_instance = stt_instance
    
    def get_config(self) -> Dict[str, Any]:
        """Récupère la configuration actuelle"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {"error": "Fichier de configuration non trouvé"}
        except Exception as e:
            log.error(f"Erreur lecture config Whisper: {e}")
            return {"error": str(e)}
    
    def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Met à jour la configuration"""
        try:
            # Charger config actuelle
            current_config = self.get_config()
            if "error" in current_config:
                return current_config
            
            # Appliquer les mises à jour (deep merge)
            updated_config = self._deep_merge(current_config, updates)
            
            # Valider la nouvelle configuration
            validation_result = self._validate_config(updated_config)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": f"Configuration invalide: {validation_result['errors']}"
                }
            
            # Sauvegarder
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(updated_config, f, indent=2, ensure_ascii=False)
            
            # Notifier l'instance STT si disponible
            if self.stt_instance:
                reload_success = self.stt_instance.reload_config()
                if not reload_success:
                    return {
                        "success": False,
                        "error": "Configuration sauvegardée mais échec du rechargement"
                    }
            
            log.success("Configuration Whisper mise à jour", "⚙️")
            
            return {
                "success": True,
                "message": "Configuration mise à jour avec succès",
                "config": updated_config
            }
            
        except Exception as e:
            log.error(f"Erreur mise à jour config: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _deep_merge(self, base: Dict, updates: Dict) -> Dict:
        """Fusion profonde de deux dictionnaires"""
        result = base.copy()
        
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Valide la configuration Whisper"""
        errors = []
        
        # Vérifier les sections obligatoires
        required_sections = ['model', 'transcription', 'vad', 'audio', 'performance', 'debug']
        for section in required_sections:
            if section not in config:
                errors.append(f"Section manquante: {section}")
        
        # Validation spécifique par section
        if 'model' in config:
            model_config = config['model']
            if 'name' not in model_config:
                errors.append("model.name est requis")
            elif model_config['name'] not in ['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3']:
                errors.append(f"model.name invalide: {model_config['name']}")
        
        if 'transcription' in config:
            trans_config = config['transcription']
            if 'no_speech_threshold' in trans_config:
                threshold = trans_config['no_speech_threshold']
                if not (0.0 <= threshold <= 1.0):
                    errors.append("no_speech_threshold doit être entre 0.0 et 1.0")
        
        if 'vad' in config:
            vad_config = config['vad']
            if 'aggressiveness' in vad_config:
                agg = vad_config['aggressiveness']
                if not (0 <= agg <= 3):
                    errors.append("vad.aggressiveness doit être entre 0 et 3")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def reset_to_defaults(self) -> Dict[str, Any]:
        """Remet la configuration aux valeurs par défaut"""
        try:
            # Créer une instance temporaire pour récupérer les defaults
            from lobes_temporaux.stt import SpeechToText
            temp_stt = SpeechToText.__new__(SpeechToText)
            default_config = temp_stt._get_default_whisper_config()
            
            # Sauvegarder
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            
            # Recharger si instance disponible
            if self.stt_instance:
                self.stt_instance.reload_config()
            
            log.info("Configuration Whisper remise aux valeurs par défaut", "⚙️")
            
            return {
                "success": True,
                "message": "Configuration remise aux valeurs par défaut",
                "config": default_config
            }
            
        except Exception as e:
            log.error(f"Erreur reset config: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# Instance globale du gestionnaire
config_manager = WhisperConfigManager()

@whisper_bp.route('/api/whisper/config', methods=['GET'])
def get_whisper_config():
    """Récupère la configuration Whisper actuelle"""
    config = config_manager.get_config()
    return jsonify({
        "success": "error" not in config,
        "config": config
    })

@whisper_bp.route('/api/whisper/config', methods=['POST'])
def update_whisper_config():
    """Met à jour la configuration Whisper"""
    try:
        updates = request.get_json()
        if not updates:
            return jsonify({
                "success": False,
                "error": "Aucune donnée JSON fournie"
            }), 400
        
        result = config_manager.update_config(updates)
        status_code = 200 if result.get("success", False) else 400
        
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Erreur traitement requête: {str(e)}"
        }), 500

@whisper_bp.route('/api/whisper/config/reset', methods=['POST'])
def reset_whisper_config():
    """Remet la configuration aux valeurs par défaut"""
    result = config_manager.reset_to_defaults()
    status_code = 200 if result.get("success", False) else 500
    return jsonify(result), status_code

@whisper_bp.route('/api/whisper/config/reload', methods=['POST'])
def reload_whisper_config():
    """Force le rechargement de la configuration"""
    try:
        if config_manager.stt_instance:
            success = config_manager.stt_instance.reload_config()
            return jsonify({
                "success": success,
                "message": "Configuration rechargée" if success else "Échec du rechargement"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Aucune instance STT active"
            }), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@whisper_bp.route('/api/whisper/presets', methods=['GET'])
def get_whisper_presets():
    """Retourne des presets de configuration Whisper"""
    presets = {
        "qualite_maximale": {
            "transcription": {
                "beam_size": 5,
                "best_of": 5,
                "temperature": [0.0],
                "no_speech_threshold": 0.8,
                "condition_on_previous_text": True
            },
            "model": {
                "name": "large"
            }
        },
        "vitesse_maximale": {
            "transcription": {
                "beam_size": 1,
                "best_of": 1,
                "temperature": [0.0],
                "no_speech_threshold": 0.4,
                "condition_on_previous_text": False
            },
            "model": {
                "name": "tiny"
            }
        },
        "equilibre": {
            "transcription": {
                "beam_size": 3,
                "best_of": 3,
                "temperature": [0.0, 0.2],
                "no_speech_threshold": 0.6,
                "condition_on_previous_text": True
            },
            "model": {
                "name": "small"
            }
        },
        "sensible_au_silence": {
            "transcription": {
                "no_speech_threshold": 0.3,
                "condition_on_previous_text": False
            },
            "vad": {
                "aggressiveness": 1
            }
        },
        "resistant_au_bruit": {
            "transcription": {
                "no_speech_threshold": 0.8,
                "condition_on_previous_text": True
            },
            "vad": {
                "aggressiveness": 3
            }
        }
    }
    
    return jsonify({
        "success": True,
        "presets": presets
    })

@whisper_bp.route('/api/whisper/config/preset/<preset_name>', methods=['POST'])
def apply_whisper_preset(preset_name: str):
    """Applique un preset de configuration"""
    # Récupérer les presets
    presets_response = get_whisper_presets()
    presets = presets_response.get_json()["presets"]
    
    if preset_name not in presets:
        return jsonify({
            "success": False,
            "error": f"Preset '{preset_name}' non trouvé"
        }), 404
    
    # Appliquer le preset
    preset_config = presets[preset_name]
    result = config_manager.update_config(preset_config)
    
    if result.get("success", False):
        result["message"] = f"Preset '{preset_name}' appliqué avec succès"
    
    status_code = 200 if result.get("success", False) else 400
    return jsonify(result), status_code

# Fonction d'initialisation pour lier l'instance STT
def init_whisper_config_api(app, stt_instance=None):
    """Initialise l'API de configuration Whisper"""
    app.register_blueprint(whisper_bp)
    
    if stt_instance:
        config_manager.set_stt_instance(stt_instance)
        log.success("API configuration Whisper initialisée", "🔧")
    
    return config_manager

if __name__ == "__main__":
    # Test des endpoints
    from flask import Flask
    
    app = Flask(__name__)
    init_whisper_config_api(app)
    
    print("🧪 Serveur de test API Whisper")
    print("Endpoints disponibles:")
    print("  GET    /api/whisper/config")
    print("  POST   /api/whisper/config")
    print("  POST   /api/whisper/config/reset")
    print("  POST   /api/whisper/config/reload")
    print("  GET    /api/whisper/presets")
    print("  POST   /api/whisper/config/preset/<name>")
    
    app.run(debug=True, port=5001)