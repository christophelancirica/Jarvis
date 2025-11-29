"""
audio_generator.py - Moteurs de synthèse audio purs
Optimisation embeddings XTTS pré-calculés
VERSION CORRIGÉE ET COMPLÈTE
"""

import os
import tempfile
import asyncio
import time
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, Union

# Import logger
import sys
sys.path.append(str(Path(__file__).parent.parent))

try:
    from hypothalamus.logger import log
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger(__name__)

# Nouveaux imports pour gTTS et pyttsx3
from gtts import gTTS
import pyttsx3


class AudioGenerator:
    """
    Moteurs de synthèse audio purs - Interface unifiée
    Optimisation embeddings XTTS
    """
    
    def __init__(self):
        """Initialise les moteurs disponibles"""
        self.xtts_model = None
        self.xtts_loaded = False
        self.coqui_models = {}  # Cache des modèles Coqui
    
        # 🚀 Cache des embeddings optimisés
        self.xtts_embeddings_cache = {
            'gpt_cond_latent': None,
            'speaker_embedding': None,
            'sample_path': None  # Pour vérifier si on a les bons embeddings
        }

        log.info("AudioGenerator initialisé")
    
    async def generate_audio(
        self, 
        text: str, 
        voice_config: Dict[str, Any]
    ) -> Optional[bytes]:
        """
        Interface unifiée de génération audio
        
        Args:
            text: Texte à synthétiser
            voice_config: Configuration voix avec model, params, etc.
            
        Returns:
            bytes: Données audio WAV ou None si échec
        """
        model = voice_config.get('model', 'edge-tts')
        
        try:
            if model == 'edge-tts':
                return await self._generate_edge_tts(text, voice_config)
            elif model == 'xtts-v2':
                return await self._generate_xtts(text, voice_config)
            elif model.startswith('tts_models/'):  # Coqui
                return await self._generate_coqui(text, voice_config)
            elif model == 'gtts':
                return await self._generate_gtts(text, voice_config)
            elif model == 'system':
                return await self._generate_system(text, voice_config)
            else:
                log.error(f"Modèle non supporté: {model}")
                return None
                
        except Exception as e:
            log.error(f"Erreur génération audio ({model}): {e}")
            return None

    async def _generate_gtts(self, text: str, voice_config: Dict[str, Any]) -> Optional[bytes]:
        """Génération Google Translate TTS (gTTS) avec post-traitement de la vitesse."""
        try:
            from pydub import AudioSegment
            import io

            lang = voice_config.get('lang', 'fr')
            speed = voice_config.get('personality_config', {}).get('voice_speed', 1.0)
            log.debug(f"gTTS: lang={lang}, speed={speed}")

            tts = gTTS(text=text, lang=lang, slow=False)

            # Sauvegarder l'audio dans un buffer en mémoire
            mp3_fp = io.BytesIO()
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)

            # Post-traitement Pydub (Nouvelle version : Resampling pur)
            # Snippet de Resampling pour gTTS
            if speed != 1.0:
                log.debug(f"🎛️ Application vitesse via Resampling: {speed}x")
                
                audio = AudioSegment.from_file(mp3_fp, format="mp3")
                
                # On change le frame_rate pour altérer la vitesse (et le pitch) mathématiquement
                new_frame_rate = int(audio.frame_rate * speed)
                audio = audio._spawn(audio.raw_data, overrides={"frame_rate": new_frame_rate})
                audio = audio.set_frame_rate(24000) # Reset au standard gTTS

                output_fp = io.BytesIO()
                audio.export(output_fp, format="mp3")
                output_fp.seek(0)
                audio_data = output_fp.read()

            else:
                # Vitesse normale (1.0) - Pas de modification
                audio_data = mp3_fp.read()
            
            log.debug(f"✅ gTTS généré: {len(audio_data)} bytes")
            return audio_data

        except Exception as e:
            log.error(f"Erreur gTTS: {e}")
            return None

    async def _generate_system(self, text: str, voice_config: Dict[str, Any]) -> Optional[bytes]:
        """Génération TTS système (pyttsx3)"""
        try:
            engine = pyttsx3.init()
            
            # Vitesse
            rate = engine.getProperty('rate')
            voice_speed = voice_config.get('personality_config', {}).get('voice_speed', 1.0)
            engine.setProperty('rate', int(rate * voice_speed))

            # Volume
            volume = voice_config.get('personality_config', {}).get('volume', 1.0)
            engine.setProperty('volume', volume)

            log.debug(f"System TTS: rate={int(rate * voice_speed)}, volume={volume}")

            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tmp_path = tmp.name
            
            engine.save_to_file(text, tmp_path)
            engine.runAndWait()
            
            with open(tmp_path, 'rb') as f:
                audio_data = f.read()
            
            os.unlink(tmp_path)
            
            log.debug(f"✅ System TTS généré: {len(audio_data)} bytes")
            return audio_data

        except Exception as e:
            log.error(f"Erreur System TTS: {e}")
            return None
    
    async def _generate_edge_tts(
        self, 
        text: str, 
        voice_config: Dict[str, Any]
    ) -> Optional[bytes]:
        """Génération Edge-TTS directe en mémoire (sans fichier temporaire)"""
        try:
            import edge_tts
            
            # Configuration voix
            edge_voice = voice_config.get('edge_voice', 'fr-FR-DeniseNeural')
            
            # Calcul vitesse (de voice_speed vers format Edge-TTS)
            voice_speed = voice_config.get('personality_config', {}).get('voice_speed', 1.0)
            rate = f"{int((voice_speed - 1) * 100):+d}%"
            
            log.debug(f"Edge-TTS: {edge_voice}, rate: {rate}")
            
            # Créer communication
            communicate = edge_tts.Communicate(text, edge_voice, rate=rate)
            
            # Stream directement en mémoire (AUCUN fichier temporaire)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            
            log.debug(f"✅ Edge-TTS généré: {len(audio_data)} bytes (direct)")
            return audio_data
            
        except Exception as e:
            log.error(f"Erreur Edge-TTS: {e}")
            return None

    async def preload_xtts_embeddings(self, voice_config: Dict[str, Any]):
        """Pré-charge les embeddings XTTS pour optimisation"""
        try:
            sample_path = voice_config.get('sample_path')
            embedding_path = voice_config.get('embedding_path')
            
            if not embedding_path or not sample_path:
                log.debug("🔧 Pas d'embeddings à pré-charger")
                return
            
            # ⚡ NORMALISER les chemins (fix Windows/Linux)
            sample_path = Path(sample_path).as_posix()
            embedding_path = Path(embedding_path).as_posix()
            
            # Construire chemins absolus
            config_dir = Path(__file__).parent.parent / "config"
            
            if not Path(embedding_path).is_absolute():
                embedding_abs = config_dir / embedding_path
            else:
                embedding_abs = Path(embedding_path)
            
            if not Path(sample_path).is_absolute():
                sample_abs = config_dir / sample_path
            else:
                sample_abs = Path(sample_path)
            
            if not embedding_abs.exists():
                log.warning(f"🔧 Embeddings non trouvés: {embedding_abs}")
                return
            
            # Charger les embeddings
            import torch
            embedding_data = torch.load(str(embedding_abs))
            
            # 🚀 Stocker dans le cache avec chemins normalisés
            self.xtts_embeddings_cache = {
                'gpt_cond_latent': embedding_data.get('gpt_cond_latent'),
                'speaker_embedding': embedding_data.get('speaker_embedding'), 
                'sample_path': sample_path  # Chemin normalisé
            }
            
            log.success(f"⚡ Embeddings XTTS pré-chargés: {embedding_abs.name}")
            log.debug(f"   Cache sample_path: {sample_path}")
            
        except Exception as e:
            log.warning(f"Erreur pré-chargement embeddings: {e}")
            # Reset cache en cas d'erreur
            self.xtts_embeddings_cache = {
                'gpt_cond_latent': None, 
                'speaker_embedding': None, 
                'sample_path': None
            }
            
    async def _generate_xtts(self, text: str, voice_config: Dict[str, Any]) -> Optional[bytes]:
        """Génération XTTS directe en mémoire avec embeddings optimisés"""
        try:
            # ✅ Initialisation XTTS si nécessaire
            if not await self._init_xtts():
                log.error("XTTS non disponible")
                return None

            # ✅ Récupérer et normaliser les chemins
            sample_path = voice_config.get("sample_path")
            if not sample_path:
                log.error("sample_path manquant pour voix XTTS")
                return None

            # Normaliser le chemin
            sample_path = Path(sample_path).as_posix()
            
            # ✅ Construire chemin complet si relatif
            if not Path(sample_path).is_absolute():
                config_dir = Path(__file__).parent.parent / "config"
                sample_path = config_dir / sample_path
            
            if not Path(sample_path).exists():
                log.error(f"Échantillon audio non trouvé: {sample_path}")
                return None

            log.debug(f"🎤 Génération XTTS avec {sample_path}")

            # 🚀 Utiliser embeddings du cache si disponibles
            cache = self.xtts_embeddings_cache
            sample_path_normalized = Path(sample_path).as_posix()

            if (cache['gpt_cond_latent'] is not None and 
                cache['speaker_embedding'] is not None and 
                cache['sample_path'] == sample_path_normalized):
                
                log.debug("⚡ Utilisation embeddings cachés")
                
                # Génération avec embeddings pré-calculés
                try:
                    # Créer fichier temporaire pour l'audio
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                        tmp_path = tmp.name
                    
                    # Générer avec embeddings
                    wav = self.xtts_model.synthesizer.tts(
                        text=text.strip(),
                        language_name="fr",
                        gpt_cond_latent=cache['gpt_cond_latent'],
                        speaker_embedding=cache['speaker_embedding'],
                        temperature=0.7,
                        length_penalty=1.0,
                        repetition_penalty=2.0,
                        top_k=50,
                        top_p=0.85
                    )
                    
                    # Convertir et sauver
                    import numpy as np
                    from scipy.io import wavfile
                    
                    if hasattr(wav, 'cpu'):
                        wav = wav.cpu().numpy()
                    
                    if isinstance(wav, (list, np.ndarray)):
                        wav = np.array(wav)
                        if wav.dtype == np.float32 or wav.dtype == np.float64:
                            wav = (wav * 32767).astype(np.int16)
                    
                    wavfile.write(tmp_path, 22050, wav)
                    
                    # Lire en bytes
                    with open(tmp_path, 'rb') as f:
                        audio_data = f.read()
                    
                    # Nettoyer
                    os.unlink(tmp_path)
                    
                except Exception as e:
                    log.warning(f"Échec méthode embeddings optimisée: {e}")
                    # Fallback sur méthode standard
                    audio_data = await self._generate_xtts_standard(text, sample_path)
            else:
                log.debug("🐌 XTTS standard (pas d'embeddings cachés)")
                audio_data = await self._generate_xtts_standard(text, sample_path)
            
            if audio_data:
                log.debug(f"✅ XTTS généré ({len(audio_data)} bytes)")
            
            return audio_data
            
        except Exception as e:
            log.error(f"Erreur XTTS: {e}")
            import traceback
            log.debug(traceback.format_exc())
            return None
    
    async def _generate_xtts_standard(self, text: str, sample_path) -> Optional[bytes]:
        """Génération XTTS standard avec fichier audio"""
        try:
            # Génération standard avec fichier temporaire
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tmp_path = tmp.name
            
            self.xtts_model.tts_to_file(
                text=text.strip(),
                language="fr",
                speaker_wav=str(sample_path),
                file_path=tmp_path
            )
            
            # Lire le fichier généré
            with open(tmp_path, 'rb') as f:
                audio_data = f.read()
            
            # Nettoyer
            os.unlink(tmp_path)
            
            return audio_data
            
        except Exception as e:
            log.error(f"Erreur génération XTTS standard: {e}")
            return None
    
    async def _generate_coqui(
        self, 
        text: str, 
        voice_config: Dict[str, Any]
    ) -> Optional[bytes]:
        """Génération Coqui TTS locale"""
        try:
            model_name = voice_config.get('model', 'tts_models/fr/css10/vits')
            
            # Charger modèle si pas en cache
            if model_name not in self.coqui_models:
                log.debug(f"Chargement modèle Coqui: {model_name}")
                from TTS.api import TTS
                self.coqui_models[model_name] = TTS(model_name)
            
            model = self.coqui_models[model_name]
            
            # Générer avec fichier temporaire
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tmp_path = tmp.name
            
            model.tts_to_file(
                text=text,
                file_path=tmp_path
            )
            
            # Lire et retourner les bytes
            with open(tmp_path, 'rb') as f:
                audio_data = f.read()
            
            # Nettoyer
            os.unlink(tmp_path)
            
            log.debug(f"✅ Coqui généré: {len(audio_data)} bytes")
            return audio_data
            
        except Exception as e:
            log.error(f"Erreur Coqui TTS: {e}")
            return None
    
    async def _init_xtts(self):
        """Initialise XTTS avec optimisations maximales"""
        if self.xtts_loaded:
            return True
            
        try:
            from TTS.api import TTS
            import torch
            
            log.info("⏳ Chargement du modèle XTTS...")
            
            # Détection du device optimal
            if torch.cuda.is_available():
                device = "cuda"
                log.info("🎮 CUDA disponible - utilisation du GPU")
            else:
                device = "cpu"
                # Sur CPU, limiter les threads pour éviter la surcharge
                torch.set_num_threads(4)
                log.info("💻 Utilisation du CPU (4 threads)")
            
            # Charger le modèle
            self.xtts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
            
            # Optimisations si sur GPU
            if device == "cuda":
                self.xtts_model = self.xtts_model.to(device)
            
            # Mode évaluation (désactive dropout, batch norm, etc.)
            if hasattr(self.xtts_model, 'synthesizer'):
                if hasattr(self.xtts_model.synthesizer, 'tts_model'):
                    self.xtts_model.synthesizer.tts_model.eval()
            
            # Warm-up du modèle
            try:
                log.debug("🔥 Warm-up du modèle XTTS...")
                # Créer un sample audio temporaire pour le warm-up
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=True) as tmp:
                    # Créer un fichier WAV minimal
                    import wave
                    import struct
                    
                    with wave.open(tmp.name, 'wb') as wav_file:
                        wav_file.setnchannels(1)  # Mono
                        wav_file.setsampwidth(2)   # 16 bits
                        wav_file.setframerate(22050)  # 22kHz
                        # Générer 1 seconde de silence
                        for _ in range(22050):
                            wav_file.writeframes(struct.pack('h', 0))
                    
                    # Warm-up avec ce fichier
                    _ = self.xtts_model.tts(
                        text="Test",
                        language="fr",
                        speaker_wav=tmp.name
                    )
                log.debug("✅ Warm-up terminé")
            except Exception as e:
                log.warning(f"Warm-up échoué (non critique): {e}")
            
            self.xtts_loaded = True
            log.success(f"✅ XTTS initialisé sur {device}")
            return True
            
        except Exception as e:
            log.error(f"Impossible de charger XTTS: {e}")
            self.xtts_loaded = False
            return False
    
    def cleanup(self):
        """Nettoyage des ressources"""
        try:
            # Libérer modèles Coqui
            self.coqui_models.clear()
            
            # Libérer XTTS
            if self.xtts_model:
                del self.xtts_model
                self.xtts_model = None
                self.xtts_loaded = False
            
            # Vider cache embeddings
            self.xtts_embeddings_cache = {
                'gpt_cond_latent': None,
                'speaker_embedding': None,
                'sample_path': None
            }
            
            log.info("AudioGenerator nettoyé")
            
        except Exception as e:
            log.warning(f"Erreur nettoyage AudioGenerator: {e}")