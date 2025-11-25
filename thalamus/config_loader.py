"""
config_loader.py - Gestionnaire centralisé des configurations JSON
Charge et gère tous les fichiers de paramètres (voices, models, themes, backgrounds)
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import sys

# Import logger
sys.path.append(str(Path(__file__).parent.parent))
from hypothalamus.logger import log

class ConfigLoader:
    """Gestionnaire centralisé des configurations JSON"""
    
    def __init__(self, config_dir: Path = None):
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "config"
        
        self.config_dir = config_dir
        self.config_dir.mkdir(exist_ok=True)
        
        # Cache des configurations
        self._cache = {}
        self._loaded_files = set()
        
        log.info("ConfigLoader initialisé", "⚙️")
    
    def load_config(self, config_name: str, force_reload: bool = False) -> Dict[str, Any]:
        """
        Charge une configuration depuis son fichier JSON
        
        Args:
            config_name: Nom du fichier sans extension (voices, models, themes, backgrounds)
            force_reload: Force le rechargement même si déjà en cache
        
        Returns:
            Dict contenant la configuration
        """
        if not force_reload and config_name in self._cache:
            return self._cache[config_name]
        
        config_file = self.config_dir / f"{config_name}.json"
        
        try:
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self._cache[config_name] = config
                    self._loaded_files.add(config_name)
                    log.success(f"Configuration '{config_name}' chargée", "📁")
                    return config
            else:
                log.warning(f"Fichier de config '{config_file}' introuvable")
                return self._get_default_config(config_name)
                
        except json.JSONDecodeError as e:
            log.error(f"Erreur JSON dans '{config_name}': {e}")
            return self._get_default_config(config_name)
        except Exception as e:
            log.error(f"Erreur chargement '{config_name}': {e}")
            return self._get_default_config(config_name)
    
    def save_config(self, config_name: str, config: Dict[str, Any]) -> bool:
        """
        Sauvegarde une configuration dans son fichier JSON
        
        Args:
            config_name: Nom du fichier sans extension
            config: Configuration à sauvegarder
        
        Returns:
            True si succès, False sinon
        """
        config_file = self.config_dir / f"{config_name}.json"
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            # Mettre à jour le cache
            self._cache[config_name] = config
            self._loaded_files.add(config_name)
            
            log.success(f"Configuration '{config_name}' sauvegardée", "💾")
            return True
            
        except Exception as e:
            log.error(f"Erreur sauvegarde '{config_name}': {e}")
            return False
    
    def get_voices(self) -> Dict[str, Any]:
        """Retourne la configuration des voix"""
        return self.load_config('voices')
    
    def get_models(self) -> Dict[str, Any]:
        """Retourne la configuration des modèles LLM"""
        return self.load_config('models')
    
    def get_themes(self) -> Dict[str, Any]:
        """Retourne la configuration des thèmes"""
        return self.load_config('themes')
    
    def get_backgrounds(self) -> Dict[str, Any]:
        """Retourne la configuration des arrière-plans"""
        return self.load_config('backgrounds')
    
    def get_voice_list(self) -> List[Dict[str, Any]]:
        """Retourne la liste des voix disponibles pour l'interface"""
        voices_config = self.get_voices()
        return [
            {
                'id': voice_id,
                'name': voice_data['name'],
                'display_name': voice_data['display_name'],
                'description': voice_data['description'],
                'gender': voice_data['gender'],
                'voice_type': voice_data.get('voice_type', 'standard'),
                'age_range': voice_data.get('age_range', 'adulte')
            }
            for voice_id, voice_data in voices_config.get('voices', {}).items()
        ]
    
    def get_model_list(self) -> List[Dict[str, Any]]:
        """Retourne la liste des modèles disponibles pour l'interface"""
        models_config = self.get_models()
        return [
            {
                'id': model_id,
                'name': model_data['name'],
                'display_name': model_data['display_name'],
                'description': model_data['description'],
                'size': model_data['size'],
                'speed': model_data['speed'],
                'quality': model_data['quality'],
                'available': model_data['available'],
                'ram_required': model_data['ram_required']
            }
            for model_id, model_data in models_config.get('llm_models', {}).items()
        ]
    
    def get_theme_list(self) -> List[Dict[str, Any]]:
        """Retourne la liste des thèmes disponibles pour l'interface"""
        themes_config = self.get_themes()
        return [
            {
                'id': theme_id,
                'name': theme_data['current_name'],
                'description': theme_data['description'],
                'css_class': theme_data['css_class'],
                'primary_color': theme_data.get('primary_color', '#ffffff'),
                'text_color': theme_data.get('text_color', '#000000'),
                'accent_color': theme_data.get('accent_color', '#0066cc')
            }
            for theme_id, theme_data in themes_config.get('themes', {}).items()
        ]
    
    def get_background_list(self) -> List[Dict[str, Any]]:
        """Retourne la liste des arrière-plans disponibles pour l'interface"""
        backgrounds_config = self.get_backgrounds()
        return [
            {
                'id': bg_id,
                'name': bg_data['name'],
                'description': bg_data['description'],
                'type': bg_data['type'],
                'file': bg_data.get('file'),
                'opacity': bg_data.get('opacity', 0.2),
                'available': bg_data.get('available', True),
                'themes_compatible': bg_data.get('themes_compatible', [])
            }
            for bg_id, bg_data in backgrounds_config.get('backgrounds', {}).items()
            if bg_data.get('available', True)
        ]
    
    def get_default_voice(self) -> str:
        """Retourne l'ID de la voix par défaut"""
        voices_config = self.get_voices()
        return voices_config.get('default_voice', 'samantha')
    
    def get_default_model(self) -> str:
        """Retourne l'ID du modèle par défaut"""
        models_config = self.get_models()
        return models_config.get('config', {}).get('default_model', 'llama3.1:8b')
    
    def get_default_theme(self) -> str:
        """Retourne l'ID du thème par défaut"""
        themes_config = self.get_themes()
        return themes_config.get('config', {}).get('default_theme', 'light')
    
    def get_default_background(self) -> str:
        """Retourne l'ID de l'arrière-plan par défaut"""
        backgrounds_config = self.get_backgrounds()
        return backgrounds_config.get('default_background', 'default')
    
    def get_voice_config(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Retourne la configuration complète d'une voix"""
        voices_config = self.get_voices()
        return voices_config.get('voices', {}).get(voice_id)
    
    def get_model_config(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Retourne la configuration complète d'un modèle"""
        models_config = self.get_models()
        return models_config.get('llm_models', {}).get(model_id)
    
    def get_demo_text(self) -> str:
        """Retourne le texte de démonstration pour les voix"""
        voices_config = self.get_voices()
        return voices_config.get('demo_text', "Bonjour, je suis votre assistant virtuel.")
    
    def _get_default_config(self, config_name: str) -> Dict[str, Any]:
        """Retourne une configuration par défaut en cas d'erreur"""
        defaults = {
            'voices': {
                'voices': {
                    'samantha': {
                        'id': 'samantha',
                        'name': 'Samantha',
                        'display_name': 'Samantha (Par défaut)',
                        'gender': 'female',
                        'model': 'edge-tts',
                        'edge_voice': 'fr-FR-DeniseNeural',
                        'description': 'Voix par défaut',
                        'audio_config': {'voice_speed': 1.0, 'voice_volume': 85}
                    }
                },
                'default_voice': 'samantha',
                'demo_text': 'Bonjour, je suis votre assistant virtuel.'
            },
            'models': {
                'llm_models': {
                    'llama3.1:8b': {
                        'id': 'llama3.1:8b',
                        'name': 'Llama 3.1 8B',
                        'display_name': 'Llama 3.1 8B (Par défaut)',
                        'available': True,
                        'default': True
                    }
                },
                'config': {'default_model': 'llama3.1:8b'}
            },
            'themes': {
                'themes': {
                    'light': {
                        'id': 'light',
                        'current_name': 'Mode Clair',
                        'css_class': 'theme-light'
                    }
                },
                'config': {'default_theme': 'light'}
            },
            'backgrounds': {
                'backgrounds': {
                    'default': {
                        'id': 'default',
                        'name': 'Par défaut',
                        'type': 'solid',
                        'available': True
                    }
                },
                'default_background': 'default'
            }
        }
        
        return defaults.get(config_name, {})
    
    def reload_all(self) -> bool:
        """Recharge toutes les configurations"""
        success = True
        for config_name in ['voices', 'models', 'themes', 'backgrounds']:
            try:
                self.load_config(config_name, force_reload=True)
            except Exception as e:
                log.error(f"Erreur rechargement {config_name}: {e}")
                success = False
        
        return success
    
    def get_status(self) -> Dict[str, Any]:
        """Retourne le statut du gestionnaire de configuration"""
        return {
            'loaded_files': list(self._loaded_files),
            'cache_size': len(self._cache),
            'config_dir': str(self.config_dir),
            'files_exist': {
                config: (self.config_dir / f"{config}.json").exists()
                for config in ['voices', 'models', 'themes', 'backgrounds']
            }
        }

# Instance globale
# config_loader = ConfigLoader()

# Test standalone
if __name__ == "__main__":
    print("🧪 Test ConfigLoader")
    
    try:
        # Test chargement
        voices = config_loader.get_voices()
        models = config_loader.get_models()
        themes = config_loader.get_themes()
        backgrounds = config_loader.get_backgrounds()
        
        print(f"✅ Voix chargées: {len(voices.get('voices', {}))}")
        print(f"✅ Modèles chargés: {len(models.get('llm_models', {}))}")
        print(f"✅ Thèmes chargés: {len(themes.get('themes', {}))}")
        print(f"✅ Arrière-plans chargés: {len(backgrounds.get('backgrounds', {}))}")
        
        # Test listes pour interface
        voice_list = config_loader.get_voice_list()
        model_list = config_loader.get_model_list()
        
        print(f"✅ Liste voix interface: {len(voice_list)} éléments")
        print(f"✅ Liste modèles interface: {len(model_list)} éléments")
        
        # Test valeurs par défaut
        print(f"✅ Voix par défaut: {config_loader.get_default_voice()}")
        print(f"✅ Modèle par défaut: {config_loader.get_default_model()}")
        print(f"✅ Thème par défaut: {config_loader.get_default_theme()}")
        
        print("\n✅ Test ConfigLoader terminé avec succès")
        
    except Exception as e:
        print(f"❌ Erreur test: {e}")
        import traceback
        traceback.print_exc()