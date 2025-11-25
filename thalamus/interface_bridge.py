"""
interface_bridge.py - Pont entre interface web et modules Jarvis (Thalamus) - VERSION AVEC CONFIG
ResponsabilitÃ© : Interface simplifiÃ©e pour l'accÃ¨s aux modules + gestion configurations JSON
Utilise maintenant le ConfigLoader pour charger les paramètres depuis les fichiers JSON
"""

from pathlib import Path
import sys

# Ajouter le chemin vers les modules Jarvis
sys.path.append(str(Path(__file__).parent.parent))

# Imports des modules existants (rÃ©utilisation)
from cortex_prefrontal.llm_client import JarvisLLM
from lobes_temporaux.stt import SpeechToText
from lobes_temporaux.tts import TextToSpeech
from hypothalamus.device_manager import DeviceManager
from hypothalamus.voice_manager import VoiceManager
from hypothalamus.logger import log

# Import du nouveau gestionnaire de configuration
from thalamus.config_loader import ConfigLoader

class InterfaceBridge:
    """Pont simplifiÃ© entre interface web et modules Jarvis (Thalamus) avec gestion config JSON"""
    
    def __init__(self):
        # Initialiser le gestionnaire de configuration
        self.config_loader = ConfigLoader()
        self.voices_json_path = Path(__file__).parent.parent / "config" / "voices.json" 
        log.info("Interface Bridge initialisÃ© avec ConfigLoader (Thalamus)")
    
    @staticmethod
    def get_system_info():
        """Retourne les informations systÃ¨me pour debug"""
        try:
            import psutil
            import platform
            
            return {
                'platform': platform.system(),
                'python_version': platform.python_version(),
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total // (1024**3),  # GB
                'memory_available': psutil.virtual_memory().available // (1024**3)  # GB
            }
        except ImportError:
            return {
                'platform': 'Unknown',
                'python_version': 'Unknown',
                'note': 'psutil non installÃ© - infos limitÃ©es'
            }

    @staticmethod
    def validate_ollama_connection():
        """VÃ©rifie la connexion Ã  Ollama"""
        try:
            import ollama
            
            # Test simple de connexion
            models = ollama.list()
            return {
                'success': True,
                'models_count': len(models.get('models', [])),
                'models': [m['name'] for m in models.get('models', [])]
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'suggestion': 'VÃ©rifiez qu\'Ollama est dÃ©marrÃ©'
            }

    @staticmethod
    def get_available_microphones():
        """Retourne la liste des microphones disponibles (via DeviceManager)"""
        try:
            device_manager = DeviceManager()
            
            import pyaudio
            p = pyaudio.PyAudio()
            devices = []
            
            for i in range(p.get_device_count()):
                try:
                    info = p.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        devices.append({
                            'index': i,
                            'name': info['name'],
                            'channels': info['maxInputChannels'],
                            'sample_rate': int(info['defaultSampleRate'])
                        })
                except:
                    continue
            
            p.terminate()
            return devices
            
        except Exception as e:
            log.error(f"Erreur Ã©numÃ©ration microphones: {e}")
            return []

    def get_available_voices(self):
        """Retourne la liste des voix disponibles (standard + clonées)"""
        try:
            import json
            from pathlib import Path
            
            voices_json_path = Path(__file__).parent.parent / "config" / "voices.json"
            
            if not voices_json_path.exists():
                log.warning(f"voices.json introuvable : {voices_json_path}")
                return {
                    'success': False,
                    'error': 'voices.json introuvable',
                    'voices': {}
                }
            
            # Charger voices.json
            with open(voices_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Fusionner voix standard et clonées
            all_voices = {}
            
            # Voix standard
            for voice_id, voice_data in data.get('voices', {}).items():
                all_voices[voice_id] = {
                    'id': voice_id,
                    'name': voice_data.get('name'),
                    'display_name': voice_data.get('display_name', voice_data.get('name')),
                    'model': voice_data.get('model'),
                    'edge_voice': voice_data.get('edge_voice'),
                    'description': voice_data.get('description', ''),
                    'type': 'standard'
                }
            
            # Voix clonées (SI status = ready)
            for voice_id, voice_data in data.get('cloned_voices', {}).items():
                if voice_data.get('processing_status') == 'ready':
                    all_voices[voice_id] = {
                        'id': voice_id,
                        'name': voice_data.get('name'),
                        'display_name': voice_data.get('display_name', voice_data.get('name')),
                        'model': 'xtts-v2',
                        'sample_path': voice_data.get('sample_path'),
                        'description': voice_data.get('description', ''),
                        'type': 'cloned'
                    }
            
            log.info(f"Voix chargées : {len(all_voices)} (standard + clonées)")
            
            return {
                'success': True,
                'voices': all_voices,
                'default_voice': data.get('default_voice', 'jarvis'),
                'demo_text': data.get('demo_text', 'Bonjour')
            }
            
        except Exception as e:
            log.error(f"Erreur chargement voix : {e}")
            import traceback
            log.error(traceback.format_exc())
            return {
                'success': False,
                'error': str(e),
                'voices': {}
            }

    def get_available_models(self):
        """Retourne la liste des modèles LLM disponibles depuis la configuration JSON"""
        try:
            return {
                'success': True,
                'models': self.config_loader.get_model_list(),
                'default_model': self.config_loader.get_default_model()
            }
        except Exception as e:
            log.error(f"Erreur chargement modèles: {e}")
            return {
                'success': False,
                'error': str(e),
                'models': []
            }

    def get_available_themes(self):
        """Retourne la liste des thèmes disponibles depuis la configuration JSON"""
        try:
            return {
                'success': True,
                'themes': self.config_loader.get_theme_list(),
                'default_theme': self.config_loader.get_default_theme()
            }
        except Exception as e:
            log.error(f"Erreur chargement thèmes: {e}")
            return {
                'success': False,
                'error': str(e),
                'themes': []
            }

    def get_available_backgrounds(self):
        """Version simplifiée - sans la fonction inutile"""
        try:
            images_path = Path("web_interface/images")
            
            if not images_path.exists():
                return {
                    'success': False,
                    'error': 'Dossier images inexistant',
                    'backgrounds': []
                }
            
            supported_formats = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
            backgrounds = []
            
            # Option par défaut
            backgrounds.append({
                'name': 'Par défaut',
                'path': None,
                'filename': None
            })
            
            # Scanner les fichiers
            for file_path in images_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in supported_formats:
                    display_name = file_path.stem.replace('_', ' ').replace('-', ' ').title()
                    
                    backgrounds.append({
                        'name': display_name,
                        'path': f"images/{file_path.name}",
                        'filename': file_path.name
                    })
            
            backgrounds[1:] = sorted(backgrounds[1:], key=lambda x: x['name'])
            
            return {
                'success': True,
                'backgrounds': backgrounds
            }
            
        except Exception as e:
            log.error(f"Erreur scan backgrounds: {e}")
            return {'success': False, 'error': str(e), 'backgrounds': []}

    def create_jarvis_instance(self, personality: str = None):
        """CrÃ©e une instance Jarvis complÃ¨te en utilisant les configurations JSON"""
        try:
            # Utiliser la voix par défaut si aucune spécifiée
            if personality is None:
                personality = self.config_loader.get_default_voice()
            
            # Récupérer la configuration de la voix
            voice_config = self.config_loader.get_voice_config(personality)
            if not voice_config:
                log.warning(f"Voix '{personality}' non trouvée, utilisation par défaut")
                personality = self.config_loader.get_default_voice()
                voice_config = self.config_loader.get_voice_config(personality)
            
            # Récupérer le modèle par défaut
            default_model = self.config_loader.get_default_model()
            
            # CrÃ©er les instances en rÃ©utilisant les modules existants
            llm = JarvisLLM(personality=personality)
            
            # Pour le TTS, utiliser la configuration de la voix depuis JSON
            tts = TextToSpeech(
                model_name=voice_config['model'],
                personality=personality,
                edge_voice=voice_config.get('edge_voice')
            )
            
            display_name = voice_config['display_name']
            log.success(f"Instance Jarvis crÃ©Ã©e: {display_name}")
            
            return {
                'llm': llm,
                'tts': tts,
                'config': voice_config,
                'personality': personality,
                'display_name': display_name,
                'model': default_model
            }
            
        except Exception as e:
            log.error(f"Erreur crÃ©ation instance Jarvis: {e}")
            raise

    @staticmethod
    def test_audio_pipeline(device_index: int = None):
        """Teste la pipeline audio complÃ¨te (rÃ©utilise modules existants)"""
        try:
            # Test STT avec module existant
            stt = SpeechToText(device_index=device_index)
            
            # Test TTS avec voix par dÃ©faut
            tts = TextToSpeech(
                model_name="edge-tts",
                personality="Samantha", 
                edge_voice="fr-FR-DeniseNeural"
            )
            
            return {
                'stt_ready': True,
                'tts_ready': True,
                'device_index': device_index
            }
            
        except Exception as e:
            return {
                'stt_ready': False,
                'tts_ready': False,
                'error': str(e)
            }

    def format_display_name(self, personality: str) -> str:
        """Formate le nom d'affichage selon la configuration JSON"""
        voice_config = self.config_loader.get_voice_config(personality)
        if voice_config:
            return voice_config.get('display_name', f"Assistant virtuel - {personality}")
        else:
            return f"Assistant virtuel - {personality}"

    def get_personality_config(self, personality: str) -> dict:
        """Retourne la configuration d'une personnalitÃ© depuis JSON"""
        voice_config = self.config_loader.get_voice_config(personality)
        if voice_config:
            return voice_config
        else:
            # Fallback sur config par défaut
            default_personality = self.config_loader.get_default_voice()
            return self.config_loader.get_voice_config(default_personality) or {}

    def get_config_status(self) -> dict:
        """Retourne le statut des configurations chargées"""
        return {
            'success': True,
            'config_loader_status': self.config_loader.get_status(),
            'available_configs': {
                'voices': len(self.config_loader.get_voice_list()),
                'models': len(self.config_loader.get_model_list()),
                'themes': len(self.config_loader.get_theme_list()),
                'backgrounds': len(self.config_loader.get_background_list())
            }
        }

    def reload_configurations(self) -> dict:
        """Recharge toutes les configurations depuis les fichiers JSON"""
        try:
            success = self.config_loader.reload_all()
            return {
                'success': success,
                'message': 'Configurations rechargées' if success else 'Erreurs lors du rechargement',
                'status': self.config_loader.get_status()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def log_system_startup(self):
        """Log les informations de dÃ©marrage systÃ¨me avec config JSON"""
        system_info = self.get_system_info()
        ollama_status = self.validate_ollama_connection()
        config_status = self.get_config_status()
        
        log.info("=== DÃ‰MARRAGE JARVIS THALAMUS (CONFIG JSON) ===")
        log.info(f"SystÃ¨me: {system_info.get('platform', 'Unknown')}")
        log.info(f"Python: {system_info.get('python_version', 'Unknown')}")
        log.info(f"RAM: {system_info.get('memory_available', '?')}GB disponible")
        
        if ollama_status['success']:
            log.success(f"Ollama connectÃ© ({ollama_status['models_count']} modÃ¨les)")
        else:
            log.warning(f"Ollama: {ollama_status['error']}")
        
        microphones = self.get_available_microphones()
        log.info(f"Microphones dÃ©tectÃ©s: {len(microphones)}")
        
        # Informations sur les configurations chargées
        available = config_status['available_configs']
        log.info(f"Configurations chargées:")
        log.info(f"  - Voix: {available['voices']}")
        log.info(f"  - Modèles: {available['models']}")
        log.info(f"  - Thèmes: {available['themes']}")
        log.info(f"  - Arrière-plans: {available['backgrounds']}")
        
        log.info("=== THALAMUS INITIALISÃ‰ (CONFIG JSON) ===")

# Test standalone
if __name__ == "__main__":
    print("🧪 Test Interface Bridge avec ConfigLoader (Thalamus)")
    
    bridge = InterfaceBridge()
    bridge.log_system_startup()
    
    try:
        # Test des configurations
        voices = bridge.get_available_voices()
        models = bridge.get_available_models()
        themes = bridge.get_available_themes()
        backgrounds = bridge.get_available_backgrounds()
        
        if voices['success']:
            print(f"✅ Voix chargées: {len(voices['voices'])}")
            for voice in voices['voices'][:3]:  # Afficher les 3 premières
                print(f"   - {voice['display_name']}: {voice['description']}")
        
        if models['success']:
            print(f"✅ Modèles chargés: {len(models['models'])}")
            for model in models['models']:
                status = "✅" if model['available'] else "⏳"
                print(f"   {status} {model['display_name']}: {model['description']}")
        
        if themes['success']:
            print(f"✅ Thèmes chargés: {len(themes['themes'])}")
        
        if backgrounds['success']:
            print(f"✅ Arrière-plans chargés: {len(backgrounds['backgrounds'])}")
        
        # Test création instance
        instance = bridge.create_jarvis_instance("samantha")
        print(f"✅ Instance crÃ©Ã©e: {instance['display_name']}")
        
        # Test statut config
        config_status = bridge.get_config_status()
        print(f"✅ Statut configurations: {config_status['config_loader_status']}")
        
        print("\n✅ Test Interface Bridge terminé avec succès")
        
    except Exception as e:
        print(f"❌ Erreur test bridge: {e}")
        import traceback
        traceback.print_exc()