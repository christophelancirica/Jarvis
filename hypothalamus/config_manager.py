"""
config_manager.py - Gestionnaire unifié de configuration
🎯 Source unique de vérité : settings.yaml SEULEMENT
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from hypothalamus.logger import log

class ConfigManager:
    """
    Gestionnaire unifié pour TOUTES les configurations
    """
    
    def __init__(self):
        self.settings_path = Path(__file__).parent.parent / "config/settings.yaml"
        self.config = {}
        self._load_config()
    
    def _load_config(self):
        """Charge la configuration depuis settings.yaml"""
        try:
            if self.settings_path.exists():
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f) or {}
                log.success("📄 Configuration unifiée chargée")
            else:
                self.config = self._get_default_config()
                self._save_config()
                log.info("📄 Configuration par défaut créée")
                
        except Exception as e:
            log.error(f"❌ Erreur chargement config: {e}")
            self.config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Configuration par défaut"""
        return {
            'voice': {
                'personality': 'Samantha',
                'display_name': 'Samantha',
                'tts_model': 'edge-tts',
                'edge_voice': 'fr-FR-DeniseNeural',
                'sample_path': None,
                'embedding_path': None
            },
            'audio': {
                'input': {
                    'whisper_model': 'small',
                    'language': 'fr',
                    'vad_aggressiveness': 2,
                    'silence_duration': 1.5,
                    'timeout': 30,
                    'sensitivity': 5
                },
                'output': {
                    'speed': 1.0,
                    'volume': 90,
                    'device_index': None
                }
            },
            'llm': {
                'model': 'llama3.1:8b',
                'temperature': 0.7,
                'role': 'assistant_general'
            },
            'interface': {
                'theme': 'light',
                'background': 'default',
                'background_opacity': 30,
                'panels': {
                    'voice_lab_visible': False,
                    'camera_visible': False,
                    'debug_visible': False
                }
            },
            'system': {
                'language': 'fr',
                'log_level': 'DEBUG'
            }
        }
    
    def _save_config(self):
        """Sauvegarde la configuration"""
        try:
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
            log.success("💾 Configuration sauvegardée")
        except Exception as e:
            log.error(f"❌ Erreur sauvegarde: {e}")
    
    # === LECTURE ===
    def get_config(self) -> Dict[str, Any]:
        """Retourne la configuration complète"""
        return self.config.copy()
    
    def get_voice_config(self) -> Dict[str, Any]:
        """Retourne la config voix"""
        return self.config.get('voice', {})
    
    def get_audio_config(self) -> Dict[str, Any]:
        """Retourne la config audio"""
        return self.config.get('audio', {})
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Retourne la config LLM"""
        return self.config.get('llm', {})
    
    def get_interface_config(self) -> Dict[str, Any]:
        """Retourne la config interface"""
        return self.config.get('interface', {})
    
    def get(self, key_path: str, default=None):
        """
        Récupère une valeur par chemin (ex: 'voice.personality')
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    # === ÉCRITURE ===
    def update_config(self, updates: Dict[str, Any]) -> bool:
        """
        Met à jour la configuration avec les changements
        """
        try:
            self._deep_update(self.config, updates)
            self._save_config()
            log.info(f"✅ Config mise à jour: {list(updates.keys())}")
            return True
        except Exception as e:
            log.error(f"❌ Erreur mise à jour: {e}")
            return False
    
    def set(self, key_path: str, value: Any) -> bool:
        """
        Définit une valeur par chemin (ex: 'voice.personality', 'Jarvis')
        """
        try:
            keys = key_path.split('.')
            config_ref = self.config
            
            # Naviguer jusqu'à l'avant-dernière clé
            for key in keys[:-1]:
                if key not in config_ref:
                    config_ref[key] = {}
                config_ref = config_ref[key]
            
            # Définir la valeur finale
            config_ref[keys[-1]] = value
            self._save_config()
            log.debug(f"✅ {key_path} = {value}")
            return True
            
        except Exception as e:
            log.error(f"❌ Erreur set {key_path}: {e}")
            return False
    
    def _deep_update(self, base_dict: dict, updates: dict):
        """Mise à jour récursive des dictionnaires"""
        for key, value in updates.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value

# Instance globale
config = ConfigManager()

# API simplifiée pour compatibilité
def get_config() -> Dict[str, Any]:
    return config.get_config()

def update_config(updates: Dict[str, Any]) -> bool:
    return config.update_config(updates)

def get_voice_config() -> Dict[str, Any]:
    return config.get_voice_config()

def get_current_personality() -> str:
    return config.get('voice.personality', 'Samantha')

def save_voice_config(personality: str, tts_model: str, **kwargs):
    """Migration : remplace voice_manager.save_voice()"""
    voice_config = {
        'voice': {
            'personality': personality,
            'display_name': kwargs.get('display_name', personality),
            'tts_model': tts_model,
            'edge_voice': kwargs.get('edge_voice'),
            'sample_path': kwargs.get('sample_path'),
            'embedding_path': kwargs.get('embedding_path')
        }
    }
    return config.update_config(voice_config)

if __name__ == "__main__":
    # Test
    config_manager = ConfigManager()
    print("✅ Configuration chargée:", config_manager.get_config())
