"""
audio_pipeline.py - Pipeline de streaming audio avec workers intelligents
VERSION CORRIGÉE ET COMPLÈTE
"""

import asyncio
import tempfile
import time
import psutil
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

# Import logger
import sys
sys.path.append(str(Path(__file__).parent.parent))

try:
    from hypothalamus.logger import log
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    """Représente un chunk audio avec métadonnées pour le pipeline"""
    text: str
    audio_path: Optional[str] = None
    audio_data: Optional[bytes] = None 
    is_generated: bool = False
    is_played: bool = False
    generation_time: float = 0.0
    play_start_time: float = 0.0
    chunk_id: int = 0


class AudioPipeline:
    """
    Pipeline de streaming audio intelligent avec workers parallèles
    VERSION CORRIGÉE
    """
    
    def __init__(self, audio_generator, voice_config):
        """
        Initialise le pipeline avec générateur audio et config voix
        
        Args:
            audio_generator: Instance d'AudioGenerator
            voice_config: Configuration voix pour génération
        """
        self.audio_generator = audio_generator
        self.voice_config = voice_config
        
        # Files d'attente pour streaming
        self.text_chunks_queue = asyncio.Queue(maxsize=50)
        self.audio_ready_queue = asyncio.Queue(maxsize=10)
        
        # État du pipeline
        self.pipeline_active = False
        self.chunk_counter = 0
        
        # Statistiques
        self.stats = {
            'chunks_generated': 0,
            'chunks_played': 0,
            'total_generation_time': 0.0,
            'total_playback_time': 0.0,
            'conversations_handled': 0,
            'pipeline_efficiency': 0.0
        }
        
        # État de connectivité (pour Edge-TTS)
        self.edge_warmed_up = False
        
        log.info("AudioPipeline initialisé")
    
    def start_streaming_workers(self):
        """Démarre les workers de streaming en arrière-plan"""
        if self.pipeline_active:
            log.debug("Pipeline déjà actif")
            return
        
        self.pipeline_active = True
        
        # Optimiser les priorités processus si nécessaire
        self._optimize_process_priorities()
        
        # Pré-initialiser pygame
        self._preinit_pygame()
        
        # ⚡ PRÉ-CHARGER EMBEDDINGS XTTS - CORRECTION ICI
        if self.voice_config.get('model') == 'xtts-v2' and self.voice_config.get('embedding_path'):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Appel CORRECT à la méthode de audio_generator
                    loop.create_task(self.audio_generator.preload_xtts_embeddings(self.voice_config))
                    log.debug("⚡ Pré-chargement embeddings XTTS lancé")
            except Exception as e:
                log.warning(f"Pré-chargement embeddings impossible: {e}")
        
        # Démarrer workers
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self._generation_worker())
                loop.create_task(self._playback_worker())
                log.success("Workers de streaming démarrés")
            else:
                raise RuntimeError("Pas de loop active")
        except RuntimeError:
            # Démarrer dans thread séparé
            def start_workers_thread():
                worker_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(worker_loop)
                worker_loop.create_task(self._generation_worker())
                worker_loop.create_task(self._playback_worker())
                worker_loop.run_forever()
            
            worker_thread = threading.Thread(target=start_workers_thread, daemon=True)
            worker_thread.start()
            log.success("Workers démarrés en thread séparé")
        
        # Warm-up pour Edge-TTS si applicable
        if self.voice_config.get('model') == 'edge-tts':
            asyncio.create_task(self._warm_up_edge_tts())
    
    async def queue_text_chunk(self, text: str) -> int:
        """
        Ajoute un chunk de texte à traiter
        
        Returns:
            chunk_id: ID du chunk pour suivi
        """
        if not self.pipeline_active:
            self.start_streaming_workers()
        
        self.chunk_counter += 1
        chunk = AudioChunk(
            text=text,
            chunk_id=self.chunk_counter
        )
        
        await self.text_chunks_queue.put(chunk)
        log.debug(f"Chunk #{chunk.chunk_id} en queue: {text[:30]}...")
        
        return chunk.chunk_id
    
    async def queue_text_chunks(self, texts: list) -> list:
        """
        Queue plusieurs chunks en série
        
        Returns:
            List des chunk_ids
        """
        chunk_ids = []
        for text in texts:
            chunk_id = await self.queue_text_chunk(text)
            chunk_ids.append(chunk_id)
        
        return chunk_ids
    
    async def _generation_worker(self):
        """Worker de génération audio parallèle"""
        log.debug("🎵 Worker génération démarré")
        
        while self.pipeline_active:
            try:
                # Attendre chunk à traiter
                chunk = await asyncio.wait_for(
                    self.text_chunks_queue.get(),
                    timeout=30.0
                )
                
                if chunk is None:  # Signal d'arrêt
                    break
                
                # Générer audio
                await self._generate_chunk_audio(chunk)
                
                # Envoyer vers lecture si succès
                if chunk.is_generated:
                    await self.audio_ready_queue.put(chunk)
                else:
                    log.warning(f"Chunk #{chunk.chunk_id} ignoré (génération échouée)")
                
            except asyncio.TimeoutError:
                # Pas de nouveau chunk depuis 30s
                log.debug("Worker génération en attente...")
            except Exception as e:
                log.error(f"Erreur worker génération: {e}")
        
        log.debug("🎵 Worker génération arrêté")
    
    async def _playback_worker(self):
        """Worker de lecture audio séquentielle"""
        log.debug("🔊 Worker lecture démarré")
        
        while self.pipeline_active:
            try:
                # Attendre chunk prêt
                chunk = await asyncio.wait_for(
                    self.audio_ready_queue.get(),
                    timeout=30.0
                )
                
                if chunk is None:  # Signal d'arrêt
                    break
                
                # Lire audio
                await self._play_chunk_audio(chunk)
                
            except asyncio.TimeoutError:
                # Pas de nouveau chunk depuis 30s
                log.debug("Worker lecture en attente...")
            except Exception as e:
                log.error(f"Erreur worker lecture: {e}")
        
        log.debug("🔊 Worker lecture arrêté")
    
    async def _generate_chunk_audio(self, chunk: AudioChunk):
        """Génère l'audio pour un chunk"""
        start_time = time.time()
        
        log.debug(f"🔍 [VOICE DEBUG] Config utilisée: {self.voice_config.get('model')} - {self.voice_config.get('personality', 'inconnu')}")
        if 'edge_voice' in self.voice_config:
            log.debug(f"🔍 [VOICE DEBUG] Edge voice: {self.voice_config.get('edge_voice')}")
        if 'sample_path' in self.voice_config:
            log.debug(f"🔍 [VOICE DEBUG] Sample path: {self.voice_config.get('sample_path')}")
        
        # Retry avec délai progressif
        max_retries = 2
        retry_delay = 1.0
        
        for attempt in range(max_retries + 1):
            try:
                log.debug(f"🎵 Génération #{chunk.chunk_id}: {chunk.text[:30]}...")
                
                # Utiliser AudioGenerator
                audio_data = await self.audio_generator.generate_audio(
                    chunk.text, 
                    self.voice_config
                )
                
                if audio_data is None:
                    raise RuntimeError("Génération audio échouée")
                
                chunk.audio_data = audio_data  # Stocker les bytes
                chunk.audio_path = None  # Pas de fichier
                chunk.generation_time = time.time() - start_time
                chunk.is_generated = True
                
                # Mise à jour stats
                self.stats['chunks_generated'] += 1
                self.stats['total_generation_time'] += chunk.generation_time
                
                log.debug(f"✅ Génération #{chunk.chunk_id} terminée ({chunk.generation_time:.2f}s)")
                return  # Succès
                
            except Exception as e:
                log.warning(f"⚠️ Erreur génération chunk #{chunk.chunk_id} (tentative {attempt + 1}): {e}")
            
            # Retry si pas le dernier essai
            if attempt < max_retries:
                await asyncio.sleep(retry_delay * (attempt + 1))
        
        # Échec définitif
        log.error(f"❌ Échec génération chunk #{chunk.chunk_id} après {max_retries + 1} tentatives")
        chunk.is_generated = False
        chunk.audio_path = None
    
    async def _play_chunk_audio(self, chunk: AudioChunk):
        """Lit un chunk audio directement depuis les bytes"""
        if not chunk.is_generated or not hasattr(chunk, 'audio_data') or not chunk.audio_data:
            log.warning(f"⚠️ Chunk #{chunk.chunk_id} ignoré (génération échouée)")
            return
        
        try:
            import pygame
            import io
            
            chunk.play_start_time = time.time()
            
            log.debug(f"🔊 Lecture #{chunk.chunk_id}: {chunk.text[:30]}...")
            log.jarvis(f"Assistant: {chunk.text}")
            
            # ✅ Lecture directe depuis bytes
            audio_buffer = io.BytesIO(chunk.audio_data)
            pygame.mixer.music.load(audio_buffer)
            pygame.mixer.music.play()
            
            # Attendre fin de lecture
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
            
            # Stats
            play_duration = time.time() - chunk.play_start_time
            self.stats['chunks_played'] += 1
            self.stats['total_playback_time'] += play_duration
            chunk.is_played = True
            
            log.debug(f"✅ Lecture #{chunk.chunk_id} terminée ({play_duration:.2f}s)")
            
        except Exception as e:
            log.error(f"❌ Erreur lecture chunk #{chunk.chunk_id}: {e}")
    
    async def _warm_up_edge_tts(self):
        """Pré-chauffe Edge-TTS pour éliminer la latence du premier chunk"""
        if self.edge_warmed_up or self.voice_config.get('model') != 'edge-tts':
            return
        
        try:
            log.debug("🔥 Warm-up Edge-TTS...")
            
            # Génération silencieuse pour préchauffage
            warmup_config = self.voice_config.copy()
            warmup_audio = await self.audio_generator.generate_audio(
                "Test", warmup_config
            )
            
            if warmup_audio:
                self.edge_warmed_up = True
                log.success("🔥 Edge-TTS préchauffé")
            else:
                log.warning("⚠️ Warm-up Edge-TTS échoué")
                
        except Exception as e:
            log.warning(f"⚠️ Erreur warm-up Edge-TTS: {e}")
    
    def _optimize_process_priorities(self):
        """Optimise les priorités processus pour audio temps-réel"""
        try:
            current_process = psutil.Process()
            
            # Augmenter priorité si possible
            if hasattr(psutil, 'HIGH_PRIORITY_CLASS'):
                current_process.nice(psutil.HIGH_PRIORITY_CLASS)
            else:
                current_process.nice(-5)  # Unix
            
            log.debug("🚀 Priorité processus optimisée pour audio")
            
        except Exception as e:
            log.debug(f"Impossible d'optimiser priorités: {e}")
    
    def _preinit_pygame(self):
        """Pré-initialise pygame pour éliminer latence démarrage"""
        try:
            import pygame
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            log.debug("🚀 pygame pré-initialisé")
        except Exception as e:
            log.warning(f"Impossible de pré-init pygame: {e}")
    
    def stop_pipeline(self):
        """Arrête proprement le pipeline"""
        if not self.pipeline_active:
            return
        
        log.debug("🛑 Arrêt pipeline...")
        self.pipeline_active = False
        
        # Signaler arrêt aux workers
        try:
            asyncio.create_task(self.text_chunks_queue.put(None))
            asyncio.create_task(self.audio_ready_queue.put(None))
        except:
            pass  # Loop peut être fermée
        
        # Statistiques finales
        self._log_pipeline_stats()
        
        log.success("🛑 Pipeline arrêté proprement")
    
    def _log_pipeline_stats(self):
        """Affiche les statistiques du pipeline"""
        stats = self.stats
        
        if stats['chunks_generated'] > 0:
            total_time = max(stats['total_generation_time'], stats['total_playback_time'])
            sequential_time = stats['total_generation_time'] + stats['total_playback_time']
            efficiency = ((sequential_time - total_time) / sequential_time * 100) if sequential_time > 0 else 0
            
            log.success("📊 Pipeline Stats:", "📈")
            log.info(f"   Chunks générés: {stats['chunks_generated']}")
            log.info(f"   Chunks lus: {stats['chunks_played']}")
            log.info(f"   Gain parallélisme: {efficiency:.1f}%")
            log.info(f"   Conversations: {stats['conversations_handled']}")
    
    def get_status(self) -> Dict[str, Any]:
        """Retourne le statut du pipeline"""
        return {
            'pipeline_active': self.pipeline_active,
            'chunks_in_generation_queue': self.text_chunks_queue.qsize(),
            'chunks_in_playback_queue': self.audio_ready_queue.qsize(),
            'edge_warmed_up': self.edge_warmed_up,
            'stats': self.stats.copy()
        }
    
    def update_voice_config(self, new_voice_config: Dict[str, Any]):
        """Met à jour la configuration voix dynamiquement"""
        self.voice_config = new_voice_config
        self.edge_warmed_up = False  # Reset warm-up si changement
        log.info(f"Configuration voix mise à jour: {new_voice_config.get('model', 'unknown')}")


# ============================================================================
# UTILITAIRES POUR DÉCOUPAGE TEXTE
# ============================================================================

def split_text_for_streaming(text: str, max_length: int = 150) -> list:
    """
    Découpe un texte en chunks optimaux pour le streaming
    
    Args:
        text: Texte à découper
        max_length: Taille maximale d'un chunk
        
    Returns:
        Liste de chunks texte
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    
    # Découper par phrases d'abord
    sentences = text.replace('. ', '.|').replace('! ', '!|').replace('? ', '?|').split('|')
    
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # Si ajouter cette phrase dépasse la limite
        if len(current_chunk) + len(sentence) > max_length:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                # Phrase trop longue, découper par mots
                words = sentence.split()
                for word in words:
                    if len(current_chunk) + len(word) > max_length:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = word
                    else:
                        current_chunk += " " + word if current_chunk else word
        else:
            current_chunk += " " + sentence if current_chunk else sentence
    
    # Ajouter le dernier chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks