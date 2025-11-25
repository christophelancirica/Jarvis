""" Text-to-Speech avec Coqui TTS et Edge-TTS FIXED """
from pathlib import Path
import numpy as np
import sounddevice as sd
import asyncio
import tempfile
import os

# Import logger
import sys
sys.path.append(str(Path(__file__).parent.parent))
from hypothalamus.logger import log

class TextToSpeech:
    def __init__(self, model_name, personality="Jarvis", edge_voice=None):
        self.personality = personality
        self.model_name = model_name
        
        log.info(f"Chargement modèle TTS {personality}...", "🔊")
        
        # Détection du mode Edge-TTS
        if model_name == "edge-tts":
            try:
                import edge_tts
                self.is_edge = True
                self.edge_voice = edge_voice or "fr-FR-DeniseNeural"
                self.tts = None
                self.sample_rate = 24000  # Edge utilise 24kHz par défaut
                log.success(f"Edge-TTS prêt ! Voix: {self.edge_voice} - {personality}", "🔊")
            except ImportError:
                log.error("edge-tts non installé ! pip install edge-tts")
                raise
        else:
            # Mode Coqui normal
            self.is_edge = False
            try:
                from TTS.api import TTS
                self.tts = TTS(model_name=model_name)
                self.sample_rate = self.tts.synthesizer.output_sample_rate
                log.success(f"Coqui TTS prêt ! ({self.sample_rate}Hz) - {personality}", "🔊")
            except Exception as e:
                log.error(f"Erreur chargement TTS: {e}")
                raise
    
    def speak(self, text: str):
        """Méthode principale qui route vers la bonne implémentation"""
        if self.is_edge:
            # Edge est async, on doit créer un event loop si nécessaire
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            loop.run_until_complete(self._speak_edge(text))
        else:
            self._speak_coqui(text)
    
    async def _speak_edge(self, text: str):
        """Version Edge-TTS (async) FIXED"""
        log.jarvis(f"{self.personality}: {text}")
        
        try:
            import edge_tts
            import pygame
            
            log.debug("Génération audio avec Edge-TTS...", "🔊")
            
            # Créer un fichier temporaire
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                tmp_path = tmp_file.name
            
            # Générer l'audio
            communicate = edge_tts.Communicate(text, self.edge_voice)
            await communicate.save(tmp_path)
            
            # 🔧 FIX pygame mixer robuste
            try:
                # Vérifier si pygame mixer est déjà initialisé
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                    log.debug("Pygame mixer initialisé", "🔊")
                
                # Charger et jouer
                pygame.mixer.music.load(tmp_path)
                pygame.mixer.music.play()
                
                # Attendre la fin avec timeout de sécurité
                timeout_counter = 0
                max_timeout = 30  # 30 secondes max
                
                while pygame.mixer.music.get_busy() and timeout_counter < max_timeout:
                    pygame.time.Clock().tick(10)  # 100ms
                    timeout_counter += 0.1
                
                if timeout_counter >= max_timeout:
                    log.warning("Timeout lecture Edge-TTS, arrêt forcé")
                    pygame.mixer.music.stop()
                
                # ✅ Arrêter la musique mais GARDER le mixer initialisé
                pygame.mixer.music.stop()
                
            except pygame.error as pe:
                log.error(f"Erreur pygame: {pe}")
                # Réinitialiser pygame en cas d'erreur
                try:
                    pygame.mixer.quit()
                    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                    pygame.mixer.music.load(tmp_path)
                    pygame.mixer.music.play()
                    
                    while pygame.mixer.music.get_busy():
                        pygame.time.Clock().tick(10)
                    
                    pygame.mixer.music.stop()
                    
                except Exception as retry_error:
                    log.error(f"Impossible de récupérer pygame: {retry_error}")
            
            # Nettoyer le fichier temporaire
            try:
                os.unlink(tmp_path)
            except:
                pass  # Pas grave si on ne peut pas supprimer
            
            log.debug("Lecture Edge-TTS terminée", "🔊")
            
        except Exception as e:
            log.error(f"Erreur Edge-TTS: {e}")
            import traceback
            log.debug(traceback.format_exc())
    
    def _speak_coqui(self, text: str):
        """Version Coqui TTS avec streaming"""
        log.jarvis(f"{self.personality}: {text}")
        
        try:
            log.debug("Génération audio avec Coqui...", "🔊")
            
            # Synthétiser en mémoire
            wav = self.tts.tts(text=text)
            
            if not isinstance(wav, np.ndarray):
                wav = np.array(wav)
            
            log.debug(f"Audio généré : {len(wav)} samples", "🔊")
            
            # Streaming par chunks pour fluidité
            stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                blocksize=2048
            )
            
            chunk_size = int(self.sample_rate * 0.05)  # 50ms chunks
            
            with stream:
                for i in range(0, len(wav), chunk_size):
                    chunk = wav[i:i+chunk_size]
                    if len(chunk) > 0:
                        stream.write(chunk.astype('float32'))
            
            log.debug("Lecture Coqui terminée", "🔊")
            
        except Exception as e:
            log.error(f"Erreur Coqui TTS: {e}")
            import traceback
            log.debug(traceback.format_exc())