"""
interface_bridge.py - Pont entre interface web et modules Jarvis (Thalamus)
Responsabilité : Interface simplifiée pour l'accès aux modules
Remplace jarvis_backend.py avec logique thalamique
"""

from pathlib import Path
import sys

# Ajouter le chemin vers les modules Jarvis
sys.path.append(str(Path(__file__).parent.parent))

# Imports des modules existants (réutilisation)
from cortex_prefrontal.llm_client import JarvisLLM
from lobes_temporaux.stt import SpeechToText
from lobes_temporaux.tts import TextToSpeech
from hypothalamus.device_manager import DeviceManager
from hypothalamus.voice_manager import VoiceManager
from hypothalamus.logger import log

# Constantes et configurations
DEFAULT_PERSONALITIES = {
    'Jarvis': {
        'display_name': 'Assistant virtuel - Jarvis',
        'tts_model': 'edge-tts',
        'edge_voice': 'fr-FR-HenriNeural',
        'description': 'Assistant masculin, style professionnel'
    },
    'Samantha': {
        'display_name': 'Assistant virtuel - Samantha', 
        'tts_model': 'edge-tts',
        'edge_voice': 'fr-FR-DeniseNeural',
        'description': 'Assistante féminine, style chaleureux'
    },
    'Eloise': {
        'display_name': 'Assistant virtuel - Eloise',
        'tts_model': 'edge-tts',
        'edge_voice': 'fr-FR-EloiseNeural',
        'description': 'Assistante jeune et dynamique'
    },
    'Josephine': {
        'display_name': 'Assistant virtuel - Josephine',
        'tts_model': 'edge-tts', 
        'edge_voice': 'fr-FR-JosephineNeural',
        'description': 'Assistante professionnelle et moderne'
    }
}

class InterfaceBridge:
    """Pont simplifié entre interface web et modules Jarvis (Thalamus)"""
    
    def __init__(self):
        log.info("Interface Bridge initialisé (Thalamus)")
    
    @staticmethod
    def get_system_info():
        """Retourne les informations système pour debug"""
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
                'note': 'psutil non installé - infos limitées'
            }

    @staticmethod
    def validate_ollama_connection():
        """Vérifie la connexion à Ollama"""
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
                'suggestion': 'Vérifiez qu\'Ollama est démarré'
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
            log.error(f"Erreur énumération microphones: {e}")
            return []

    @staticmethod
    def create_jarvis_instance(personality: str = "Samantha"):
        """Crée une instance Jarvis complète (réutilise modules existants)"""
        try:
            # Validation de la personnalité
            if personality not in DEFAULT_PERSONALITIES:
                personality = "Samantha"
            
            config = DEFAULT_PERSONALITIES[personality]
            
            # Créer les instances en réutilisant les modules existants
            llm = JarvisLLM(personality=personality)
            
            # Pour le TTS, utiliser la configuration de la personnalité
            tts = TextToSpeech(
                model_name=config['tts_model'],
                personality=personality,
                edge_voice=config['edge_voice']
            )
            
            log.success(f"Instance Jarvis créée: {config['display_name']}")
            
            return {
                'llm': llm,
                'tts': tts,
                'config': config,
                'personality': personality
            }
            
        except Exception as e:
            log.error(f"Erreur création instance Jarvis: {e}")
            raise

    @staticmethod
    def test_audio_pipeline(device_index: int = None):
        """Teste la pipeline audio complète (réutilise modules existants)"""
        try:
            # Test STT avec module existant
            stt = SpeechToText(device_index=device_index)
            
            # Test TTS avec voix par défaut
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

    @staticmethod
    def format_display_name(personality: str) -> str:
        """Formate le nom d'affichage selon la spec"""
        if personality in DEFAULT_PERSONALITIES:
            return DEFAULT_PERSONALITIES[personality]['display_name']
        else:
            return f"Assistant virtuel - {personality}"

    @staticmethod
    def get_personality_config(personality: str) -> dict:
        """Retourne la configuration d'une personnalité"""
        return DEFAULT_PERSONALITIES.get(personality, DEFAULT_PERSONALITIES['Samantha'])

    @staticmethod
    def log_system_startup():
        """Log les informations de démarrage système"""
        system_info = InterfaceBridge.get_system_info()
        ollama_status = InterfaceBridge.validate_ollama_connection()
        
        log.info("=== DÉMARRAGE JARVIS THALAMUS ===")
        log.info(f"Système: {system_info.get('platform', 'Unknown')}")
        log.info(f"Python: {system_info.get('python_version', 'Unknown')}")
        log.info(f"RAM: {system_info.get('memory_available', '?')}GB disponible")
        
        if ollama_status['success']:
            log.success(f"Ollama connecté ({ollama_status['models_count']} modèles)")
        else:
            log.warning(f"Ollama: {ollama_status['error']}")
        
        microphones = InterfaceBridge.get_available_microphones()
        log.info(f"Microphones détectés: {len(microphones)}")
        
        log.info("=== THALAMUS INITIALISÉ ===")

# Test standalone
if __name__ == "__main__":
    print("🧪 Test Interface Bridge (Thalamus)")
    
    bridge = InterfaceBridge()
    bridge.log_system_startup()
    
    try:
        instance = bridge.create_jarvis_instance("Samantha")
        print(f"✅ Instance créée: {instance['config']['display_name']}")
        
        audio_test = bridge.test_audio_pipeline()
        if audio_test['stt_ready'] and audio_test['tts_ready']:
            print("✅ Pipeline audio fonctionnelle")
        else:
            print(f"❌ Pipeline audio: {audio_test.get('error', 'Erreur inconnue')}")
            
    except Exception as e:
        print(f"❌ Erreur test bridge: {e}")