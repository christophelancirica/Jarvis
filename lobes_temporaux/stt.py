"""
Speech-to-Text avec Faster-Whisper + VAD (Voice Activity Detection)
Version nettoyée sans redondances
"""

import json
import pyaudio
import os
from pathlib import Path
import yaml
import numpy as np
import time
from typing import Dict, Any, Optional

# Import faster-whisper
from faster_whisper import WhisperModel
import webrtcvad

# Import logger
import sys
sys.path.append(str(Path(__file__).parent.parent))
from hypothalamus.logger import log

# Configuration FFmpeg
import imageio_ffmpeg
os.environ["PATH"] = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe()) + os.pathsep + os.environ.get("PATH", "")

class SpeechToText:
    def __init__(self, device_index=None, config_path: Optional[str] = None):
        """
        Initialise STT avec faster-whisper et configuration JSON
        
        Args:
            device_index: Index du microphone à utiliser
            config_path: Chemin vers le fichier de config JSON Whisper
        """
        self.device_index = device_index
        
        # Charger configurations
        self._load_yaml_config()
        self._load_whisper_config(config_path)
        
        # Créer dossier pour les enregistrements (optionnel selon config)
        if self.whisper_config['debug']['save_recordings']:
            self.recordings_dir = Path(self.whisper_config['debug']['recordings_path'])
            self.recordings_dir.mkdir(exist_ok=True)
        else:
            self.recordings_dir = None
        
        # Initialiser le modèle Whisper
        self._initialize_whisper_model()
        
        # Pré-charger les composants audio
        self._preload_audio_components()
        
        if self.device_index is not None:
            self._log_audio_device()
    
    def _load_yaml_config(self):
        """Charge la configuration YAML principale"""
        config_path = Path(__file__).parent.parent / "config/settings.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            self.yaml_config = yaml.safe_load(f)
    
    def _load_whisper_config(self, config_path: Optional[str] = None):
        """Charge la configuration JSON Whisper"""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config/whisper_config.json"
        
        self.whisper_config_path = Path(config_path)
        
        if self.whisper_config_path.exists():
            with open(self.whisper_config_path, 'r', encoding='utf-8') as f:
                self.whisper_config = json.load(f)
            log.success(f"Configuration Whisper chargée: {self.whisper_config_path.name}", "⚙️")
        else:
            # Configuration par défaut si le fichier n'existe pas
            self.whisper_config = self._get_default_whisper_config()
            self._save_whisper_config()
            log.warning(f"Config Whisper créée par défaut: {self.whisper_config_path}", "⚙️")
    
    def _get_default_whisper_config(self) -> Dict[str, Any]:
        """Retourne la configuration Whisper par défaut (version simplifiée)"""
        return {
            "model": {
                "name": "small",
                "device": "cpu",
                "compute_type": "int8"
            },
            "transcription": {
                "language": "fr",
                "beam_size": 5,
                "temperature": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                "no_speech_threshold": 0.6
            },
            "vad": {
                "enabled": True,
                "aggressiveness": 2,
                "min_speech_duration": 0.2,  # Optimisé pour réactivité
                "silence_duration": 1.5,
                "timeout": 30
            },
            "debug": {
                "save_recordings": False,
                "recordings_path": "./recordings",
                "log_transcription_details": True,
                "log_performance_stats": True
            }
        }
    
    def _save_whisper_config(self):
        """Sauvegarde la configuration Whisper dans le fichier JSON"""
        with open(self.whisper_config_path, 'w', encoding='utf-8') as f:
            json.dump(self.whisper_config, f, indent=2, ensure_ascii=False)
    
    def _initialize_whisper_model(self):
        """Initialise le modèle Whisper (version simplifiée)"""
        model_config = self.whisper_config['model']
        model_name = model_config['name']
        
        log.info(f"Chargement modèle Whisper '{model_name}'...", "🎤")
        
        try:
            self.model = WhisperModel(
                model_name,
                device=model_config.get('device', 'cpu'),
                compute_type=model_config.get('compute_type', 'int8')
            )
            self.use_faster_whisper = True
            log.success("Faster-Whisper prêt ! 🚀", "🎤")
            
        except Exception as e:
            log.error(f"Erreur chargement Whisper: {e}")
            raise
    
    def _preload_audio_components(self):
        """Pré-charge VAD et PyAudio une seule fois"""
        try:
            # Pré-charger VAD avec config
            vad_config = self.whisper_config['vad']
            self.vad = webrtcvad.Vad(vad_config['aggressiveness'])
            
            # Pré-charger PyAudio
            self.pyaudio_instance = pyaudio.PyAudio()
            self.audio_stream = None
            
            log.success("🎤 Composants audio pré-chargés", "⚡")
            
        except Exception as e:
            log.error(f"Erreur pré-chargement audio: {e}")
            # Fallback si problème
            self.vad = None
            self.pyaudio_instance = None
            self.audio_stream = None
    
    def _log_audio_device(self):
        """Log info sur le device audio utilisé"""
        if self.pyaudio_instance and self.device_index is not None:
            try:
                info = self.pyaudio_instance.get_device_info_by_index(self.device_index)
                log.info(f"🎤 Device: {info['name']}", "🎧")
            except:
                log.warning("Impossible de récupérer info device")
    
    def listen_with_whisper_vad(self, max_duration: int = 15) -> str:
        """
        Méthode principale : Enregistrement avec VAD + Transcription
        """
        try:
            log.info("🎙️ Micro actif, parlez...", "")
            
            # Enregistrement avec VAD
            audio_data = self._record_with_realtime_vad(max_duration)
            
            if audio_data is None or len(audio_data) == 0:
                log.warning("Aucun audio enregistré")
                return ""
            
            log.info("🔄 Transcription...", "")
            
            # Transcription unifiée
            result = self._transcribe_audio(audio_data)
            
            if result:
                log.success(f"Transcription: '{result}'")
            else:
                log.warning("⚠️ Transcription vide")
            
            return result
            
        except Exception as e:
            log.error(f"❌ Erreur transcription: {e}")
            return ""
    
    def _transcribe_audio(self, audio_data: np.ndarray) -> str:
        """
        Transcription unifiée (remplace les anciennes méthodes dupliquées)
        """
        try:
            trans_config = self.whisper_config['transcription']
            
            start_time = time.time()
            
            # Transcription avec faster-whisper
            segments, info = self.model.transcribe(
                audio_data,
                language=trans_config['language'],
                beam_size=trans_config['beam_size'],
                temperature=trans_config['temperature'],
                no_speech_threshold=trans_config['no_speech_threshold'],
                # VAD faster-whisper pour nettoyer
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=800,
                    speech_pad_ms=300
                )
            )
            
            # Assembler les segments
            result = " ".join([segment.text for segment in segments]).strip()
            
            # Stats de performance
            if self.whisper_config['debug']['log_performance_stats']:
                transcription_time = time.time() - start_time
                log.debug(f"⏱️ Temps transcription: {transcription_time:.2f}s")
            
            return result
            
        except Exception as e:
            log.error(f"❌ Erreur lors de la transcription: {e}")
            return ""
    
    def _record_with_realtime_vad(self, max_duration: int) -> Optional[np.ndarray]:
        """
        Enregistrement avec VAD temps réel optimisé
        """
        try:
            # Vérifier pré-chargement
            if self.vad is None or self.pyaudio_instance is None:
                log.warning("Composants non pré-chargés, impossible d'enregistrer")
                return None
            
            # Configuration audio
            RATE = 16000
            CHUNK = 320  # 20ms chunks pour webrtcvad
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            
            vad_config = self.whisper_config['vad']
            
            frames = []
            silence_count = 0
            speech_count = 0
            recording_speech = False
            
            # Seuils en chunks (20ms chacun)
            min_speech_chunks = int(vad_config['min_speech_duration'] * 50)
            silence_threshold_chunks = int(vad_config['silence_duration'] * 50)
            
            stream_params = {
                'format': FORMAT,
                'channels': CHANNELS,
                'rate': RATE,
                'input': True,
                'frames_per_buffer': CHUNK
            }
            
            if self.device_index is not None:
                stream_params['input_device_index'] = self.device_index
            
            # Utiliser pyaudio pré-chargé
            stream = self.pyaudio_instance.open(**stream_params)
            
            max_chunks = int(RATE / CHUNK * max_duration)
            
            for i in range(max_chunks):
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    frames.append(data)
                    
                    # VAD pré-chargé
                    try:
                        is_speech = self.vad.is_speech(data, RATE)
                    except:
                        is_speech = False
                    
                    if is_speech:
                        speech_count += 1
                        silence_count = 0
                        if speech_count >= min_speech_chunks:
                            recording_speech = True
                    else:
                        silence_count += 1
                        speech_count = 0
                    
                    # Arrêt si silence prolongé après parole
                    if recording_speech and silence_count >= silence_threshold_chunks:
                        break
                        
                except Exception as e:
                    log.warning(f"Erreur lecture audio: {e}")
                    break
            
            stream.stop_stream()
            stream.close()
            
            if not frames or not recording_speech:
                return None
            
            # Convertir en format faster-whisper
            audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
            return audio_data.astype(np.float32) / 32768.0
            
        except Exception as e:
            log.error(f"Erreur VAD: {e}")
            return None
    
    def get_current_config(self) -> Dict[str, Any]:
        """Retourne la configuration actuelle avec infos runtime"""
        return {
            "whisper_config": self.whisper_config,
            "use_faster_whisper": getattr(self, 'use_faster_whisper', False),
            "model_loaded": hasattr(self, 'model'),
            "device_index": self.device_index,
            "vad_enabled": self.whisper_config['vad']['enabled'],
            "components_preloaded": {
                "vad": self.vad is not None,
                "pyaudio": self.pyaudio_instance is not None
            }
        }
    
    def close_audio_resources(self):
        """Ferme proprement les ressources audio"""
        if self.audio_stream:
            self.audio_stream.close()
            self.audio_stream = None
        
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
            self.pyaudio_instance = None
        
        log.info("🔇 Ressources audio fermées")
    
    def __del__(self):
        """Destructeur pour nettoyer automatiquement"""
        self.close_audio_resources()

# Point d'entrée pour tests
if __name__ == "__main__":
    # Test de la classe
    stt = SpeechToText()
    print("Configuration actuelle:")
    import json
    print(json.dumps(stt.get_current_config(), indent=2, ensure_ascii=False))