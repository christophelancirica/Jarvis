"""
Speech-to-Text avec Whisper + VAD (Voice Activity Detection)
"""

import whisper
import pyaudio
import wave
import os
from pathlib import Path
import yaml
from datetime import datetime
import numpy as np
import webrtcvad
from collections import deque
import time

# Import logger
import sys
sys.path.append(str(Path(__file__).parent.parent))
from hypothalamus.logger import log

# Configuration FFmpeg
import imageio_ffmpeg
os.environ["PATH"] = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe()) + os.pathsep + os.environ.get("PATH", "")

class SpeechToText:
    def __init__(self, device_index=None):
        # Charger config
        config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        model_size = config['audio']['input']['whisper_model']
        self.language = config['audio']['input']['language']
        self.device_index = device_index
        
        # Créer dossier pour les enregistrements
        self.recordings_dir = Path("recordings")
        self.recordings_dir.mkdir(exist_ok=True)
        
        log.info(f"Chargement modèle Whisper '{model_size}'...", "🎤")
        self.model = whisper.load_model(model_size)
        log.success("Whisper prêt !", "🎤")
        
        # Initialiser VAD (Voice Activity Detection)
        self.vad = webrtcvad.Vad(2)  # Agressivité 0-3 (2 = équilibré)
        log.success("VAD initialisé !", "🎙️")
        
        if self.device_index is not None:
            p = pyaudio.PyAudio()
            device_name = p.get_device_info_by_index(self.device_index)['name']
            p.terminate()
            log.info(f"Utilise : {device_name}", "🎙️")
    
    def listen_with_vad(self, timeout: int = 30, silence_duration: float = 1.5):
        """
        Enregistre avec détection de voix automatique
        
        timeout: durée max d'attente/enregistrement (secondes)
        silence_duration: durée de silence pour arrêter (secondes)
        """
        
        # Paramètres audio pour VAD
        RATE = 16000
        CHUNK = 480  # 30ms à 16kHz (requis par webrtcvad)
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        
        # Buffers
        pre_speech_buffer = deque(maxlen=20)  # 600ms avant détection
        speech_frames = []
        
        # États
        is_speaking = False
        silence_frames = 0
        silence_threshold = int(silence_duration * RATE / CHUNK)
        
        log.info("🎙️  Micro actif, parle quand tu veux...", "")
        
        p = pyaudio.PyAudio()
        
        stream_params = {
            'format': FORMAT,
            'channels': CHANNELS,
            'rate': RATE,
            'input': True,
            'frames_per_buffer': CHUNK
        }
        
        if self.device_index is not None:
            stream_params['input_device_index'] = self.device_index
        
        stream = p.open(**stream_params)
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < timeout:
                frame = stream.read(CHUNK, exception_on_overflow=False)
                
                # Détection de voix avec VAD
                is_speech = self.vad.is_speech(frame, RATE)
                
                if not is_speaking:
                    # Avant de parler : garder un buffer
                    pre_speech_buffer.append(frame)
                    
                    if is_speech:
                        # Début de parole détecté !
                        log.success("🗣️  Parole détectée, enregistrement...", "")
                        is_speaking = True
                        # Ajouter le buffer pré-parole
                        speech_frames.extend(pre_speech_buffer)
                        speech_frames.append(frame)
                else:
                    # En train de parler
                    speech_frames.append(frame)
                    
                    if not is_speech:
                        # Silence détecté
                        silence_frames += 1
                        
                        if silence_frames > silence_threshold:
                            # Assez de silence, arrêter
                            log.success("✅ Fin de parole détectée", "")
                            break
                    else:
                        # Réinitialiser le compteur de silence
                        silence_frames = 0
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            if not speech_frames:
                log.warning("Aucune parole détectée")
                return ""
            
            log.success(f"Enregistré {len(speech_frames)} frames")
            
            # Sauvegarder le fichier
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_filename = f"recording_{timestamp}.wav"
            tmp_path = self.recordings_dir / audio_filename
            
            log.debug(f"Sauvegarde : {tmp_path}", "💾")
            
            wf = wave.open(str(tmp_path), 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(speech_frames))
            wf.close()
            
            file_size = tmp_path.stat().st_size
            log.debug(f"Fichier : {tmp_path.name} ({file_size} bytes)")
            
            # Analyser volume
            import audioop
            volumes = [audioop.rms(frame, 2) for frame in speech_frames]
            volume_max = max(volumes)
            volume_avg = sum(volumes) / len(volumes)
            log.debug(f"Volume max: {volume_max}, moyen: {volume_avg:.0f}", "📊")
            
            # Transcription
            return self._transcribe(tmp_path)
            
        except Exception as e:
            log.error(f"Erreur enregistrement VAD: {e}")
            stream.stop_stream()
            stream.close()
            p.terminate()
            return ""
    
    def _transcribe(self, audio_path):
        """Transcription interne"""
        log.thinking("Transcription...")
        log.debug(f"Fichier : {audio_path.absolute()}")
        
        try:
            # Lecture manuelle WAV
            with wave.open(str(audio_path.absolute()), 'rb') as wf:
                n_channels = wf.getnchannels()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                
                log.debug(f"Format : {n_channels} canal, {framerate}Hz, {n_frames} frames")
                
                audio_data = wf.readframes(n_frames)
            
            # Convertir en numpy
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            log.debug(f"Audio chargé : {len(audio_array)} samples")
            
            # Transcription
            result = self.model.transcribe(
                audio_array,
                language=self.language, 
                fp16=False
            )
            text = result["text"].strip()
            
            if text:
                log.success(f"Transcription: '{text}'")
            else:
                log.warning("Transcription vide")
            
            return text
            
        except Exception as e:
            log.error(f"Erreur transcription: {e}")
            import traceback
            log.debug(traceback.format_exc())
            return ""