"""
Text-to-Speech avec Coqui TTS (streaming, local, offline)
"""

from pathlib import Path
import numpy as np
import sounddevice as sd

# PATCH INTELLIGENT pour PyTorch 2.6+ avec vieux modèles
import torch
_original_load = torch.load

def smart_torch_load(*args, **kwargs):
    # Si weights_only est déjà défini, on le laisse
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)

torch.load = smart_torch_load

from TTS.api import TTS

# Import logger
import sys
sys.path.append(str(Path(__file__).parent.parent))
from hypothalamus.logger import log

class TextToSpeech:
    def __init__(self, model_name, personality="Jarvis"):
        self.personality = personality
        self.model_name = model_name
        
        log.info(f"Chargement modèle TTS {personality}...", "🔊")
        
        try:
            # Initialiser Coqui TTS
            self.tts = TTS(model_name=model_name)
            
            # Récupérer le sample rate du modèle
            self.sample_rate = self.tts.synthesizer.output_sample_rate
            
            log.success(f"TTS prêt ! ({self.sample_rate}Hz) - {personality}", "🔊")
            
        except Exception as e:
            log.error(f"Erreur chargement TTS: {e}")
            raise
    
    def speak(self, text: str):
        """
        Version streaming - commence à parler dès les premiers chunks
        Plus rapide et fluide que la version avec fichier
        """
        log.jarvis(f"{self.personality}: {text}")
        
        try:
            log.debug("Génération audio...", "🔊")
            
            # Synthétiser en mémoire (array numpy)
            wav = self.tts.tts(text=text)
            
            # Convertir en numpy array si nécessaire
            if not isinstance(wav, np.ndarray):
                wav = np.array(wav)
            
            log.debug(f"Audio généré : {len(wav)} samples", "🔊")
            
            # Créer un stream de sortie
            stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                blocksize=2048  # Buffer size optimisé
            )
            
            # Chunker l'audio et jouer progressivement
            chunk_size = int(self.sample_rate * 0.1)  # chunks de 100ms
            
            log.debug(f"Streaming en chunks de {chunk_size} samples", "🔊")
            
            with stream:
                for i in range(0, len(wav), chunk_size):
                    chunk = wav[i:i+chunk_size]
                    if len(chunk) > 0:
                        # S'assurer que c'est float32
                        chunk_float = chunk.astype('float32')
                        stream.write(chunk_float)
            
            log.debug("Lecture terminée", "🔊")
            
        except Exception as e:
            log.error(f"Erreur TTS streaming: {e}")
            import traceback
            log.debug(traceback.format_exc())
    
    def speak_fast(self, text: str):
        """
        Version ultra-rapide pour réponses courtes
        Réduit la latence au maximum
        """
        log.jarvis(f"{self.personality}: {text}")
        
        try:
            # Générer
            wav = self.tts.tts(text=text)
            
            if not isinstance(wav, np.ndarray):
                wav = np.array(wav)
            
            # Jouer directement tout le buffer (pas de chunking)
            sd.play(wav.astype('float32'), samplerate=self.sample_rate)
            sd.wait()  # Attendre la fin
            
        except Exception as e:
            log.error(f"Erreur TTS fast: {e}")