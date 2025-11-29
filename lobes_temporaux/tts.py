"""
tts.py - Orchestrateur TTS simplifié et unifié
REFACTORISÉ: Utilise AudioGenerator + AudioPipeline + VoiceCloner
"""

from pathlib import Path
import asyncio
import tempfile
import time
from typing import Optional, List, Dict, Any

# Import logger
import sys
sys.path.append(str(Path(__file__).parent.parent))

try:
    from hypothalamus.logger import log
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger(__name__)

# Modules de gestions des voix
from .audio_generator import AudioGenerator
from .audio_pipeline import AudioPipeline, split_text_for_streaming
from .voice_cloner import VoiceCloner
from hypothalamus.config_manager import ConfigManager


class TextToSpeech:
    """
    Orchestrateur TTS unifié et simplifié
    RESPONSABILITÉS:
    - Initialiser et configurer les composants
    - Coordonner génération + pipeline + clonage
    - API publique pour l'application
    """
    
    def __init__(self, model_name=None, personality="Jarvis", edge_voice=None, sample_path=None):
        """
        Initialise le TTS unifié
        
        Args:
            model_name: Type de modèle (pour compatibilité legacy)
            personality: Nom de la voix/personnalité
            edge_voice: Voix Edge-TTS (pour compatibilité legacy)
            sample_path: Chemin échantillon (pour compatibilité legacy)
        """
        self.personality = personality
        
        # NOUVEAU: Modules unifiés
        self.voice_cloner = VoiceCloner()
        self.audio_generator = AudioGenerator()
        
        # Résoudre la configuration voix
        self.voice_config = self._resolve_voice_config(model_name, personality, edge_voice, sample_path)
        
        if not self.voice_config:
            log.error(f"Configuration voix impossible pour '{personality}'")
            raise ValueError(f"Voix '{personality}' non trouvée")
        
        # Initialiser le pipeline avec la config
        self.pipeline = AudioPipeline(self.audio_generator, self.voice_config)
        
        # Statistiques et état
        self.stats = {
            'conversations_handled': 0,
            'total_chunks_processed': 0,
            'errors': 0
        }
        
        log.success(f"TTS initialisé - {personality} ({self.voice_config.get('model', 'unknown')})")
        log.info(f"Voice config: {self.voice_config}")
    
    def _resolve_voice_config(self, model_name, personality, edge_voice, sample_path):
        """
        Résout la configuration voix depuis les paramètres
        Priorité: VoiceCloner > Paramètres legacy > Défaut
        """
        config_manager = ConfigManager()
        global_config = config_manager.get_config()
        audio_output_config = global_config.get('audio', {}).get('output', {})

        base_config = None
        
        # PRIORITÉ 1: Chercher dans VoiceCloner (voix configurées)
        base_config = self.voice_cloner.get_voice_config(personality)
        if base_config:
            log.debug(f"Configuration trouvée dans VoiceCloner pour '{personality}'")
        
        # PRIORITÉ 2: Construire depuis paramètres legacy
        elif model_name:
            log.debug(f"Construction config depuis paramètres legacy: {model_name}")
            base_config = self._build_legacy_voice_config(model_name, personality, edge_voice, sample_path)
        
        # PRIORITÉ 3: Essayer voix par défaut
        else:
            default_voice = self.voice_cloner.voices_config.get('default_voice', 'jarvis')
            base_config = self.voice_cloner.get_voice_config(default_voice)
            if base_config:
                log.warning(f"Utilisation voix par défaut '{default_voice}' au lieu de '{personality}'")

        if not base_config:
            # PRIORITÉ 4: Fallback Edge-TTS
            log.warning(f"Fallback Edge-TTS pour '{personality}'")
            base_config = {
                'model': 'edge-tts',
                'edge_voice': 'fr-FR-DeniseNeural',
                'personality_config': {}
            }

        # Fusionner avec la configuration globale pour la vitesse et le volume
        if 'personality_config' not in base_config:
            base_config['personality_config'] = {}

        base_config['personality_config']['voice_speed'] = audio_output_config.get('speed', 1.0)
        base_config['personality_config']['voice_volume'] = audio_output_config.get('volume', 90) / 100.0

        return base_config
    
    def _build_legacy_voice_config(self, model_name, personality, edge_voice, sample_path):
        """Construit voice_config depuis paramètres legacy"""
        
        if model_name == "edge-tts":
            return {
                'model': 'edge-tts',
                'edge_voice': edge_voice or "fr-FR-DeniseNeural",
            }
        
        elif model_name == "xtts-v2":
            if not sample_path:
                log.error("sample_path requis pour XTTS-v2")
                return None
                
            return {
                'model': 'xtts-v2',
                'sample_path': sample_path,
            }
        
        else:
            # Coqui
            return {
                'model': model_name,
            }
    
    # ========================================================================
    # API PUBLIQUE - STREAMING INTELLIGENT
    # ========================================================================
    
    async def speak_streaming(self, text: str, chunk_size: int = 150):
        """
        API principale - Parle avec streaming intelligent
        
        Args:
            text: Texte à synthétiser
            chunk_size: Taille max des chunks pour streaming
        """
        if not text.strip():
            return
        
        try:
            self.stats['conversations_handled'] += 1
            
            log.jarvis(f"🗣️ {self.personality}: {text}")
            
            # Découper en chunks optimaux
            chunks = split_text_for_streaming(text, chunk_size)
            self.stats['total_chunks_processed'] += len(chunks)
            
            log.debug(f"Streaming: {len(chunks)} chunks")
            
            # Démarrer pipeline si nécessaire
            if not self.pipeline.pipeline_active:
                self.pipeline.start_streaming_workers()
            
            # Envoyer tous les chunks en parallèle
            chunk_ids = await self.pipeline.queue_text_chunks(chunks)
            
            # Attendre que tous soient traités (optionnel pour debug)
            await self._wait_for_chunks_completion(chunk_ids)
            
        except Exception as e:
            log.error(f"Erreur speak_streaming: {e}")
            self.stats['errors'] += 1
    
    async def speak_simple(self, text: str):
        """
        API simple - Une seule génération sans streaming
        Utile pour courts textes ou tests
        """
        try:
            log.debug(f"Génération simple: {text[:50]}...")
            
            # Générer directement
            audio_data = await self.audio_generator.generate_audio(text, self.voice_config)
            
            if audio_data:
                # Jouer immédiatement
                await self._play_audio_data(audio_data)
                log.success("Lecture simple terminée")
            else:
                log.error("Génération simple échouée")
                
        except Exception as e:
            log.error(f"Erreur speak_simple: {e}")
            self.stats['errors'] += 1
    
    async def _wait_for_chunks_completion(self, chunk_ids: list, timeout: float = 30.0):
        """Attend que tous les chunks soient traités (pour debug/sync)"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.pipeline.get_status()
            
            # Si plus rien en queue, c'est probablement fini
            if (status['chunks_in_generation_queue'] == 0 and 
                status['chunks_in_playback_queue'] == 0):
                break
            
            await asyncio.sleep(0.5)
    
    async def _play_audio_data(self, audio_data: bytes):
        """Joue des données audio directement avec pygame"""
        try:
            import pygame
            
            # Pré-init pygame si nécessaire
            if not pygame.mixer.get_init():
                pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
                pygame.mixer.init()
            
            # Fichier temporaire
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_file.write(audio_data)
            temp_file.close()
            
            # Jouer
            pygame.mixer.music.load(temp_file.name)
            pygame.mixer.music.play()
            
            # Attendre fin
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
            
            pygame.mixer.music.stop()
            
            # Nettoyer
            import os
            try:
                os.unlink(temp_file.name)
            except:
                pass
                
        except Exception as e:
            log.error(f"Erreur lecture audio: {e}")
    
    # ========================================================================
    # GESTION DYNAMIQUE DES VOIX
    # ========================================================================
    
    async def switch_voice(self, new_personality: str):
        """Change de voix dynamiquement"""
        try:
            log.info(f"Changement voix: {self.personality} → {new_personality}")
            
            # Résoudre nouvelle config
            new_voice_config = self.voice_cloner.get_voice_config(new_personality)
            
            if not new_voice_config:
                log.error(f"Voix '{new_personality}' non trouvée")
                return False
            
            # Mettre à jour
            self.personality = new_personality
            self.voice_config = new_voice_config
            
            # Mettre à jour le pipeline
            self.pipeline.update_voice_config(new_voice_config)
            
            log.success(f"Voix changée: {new_personality}")
            return True
            
        except Exception as e:
            log.error(f"Erreur changement voix: {e}")
            return False
    
    def list_available_voices(self) -> Dict[str, List]:
        """Liste toutes les voix disponibles"""
        voices_data = self.voice_cloner.get_all_voices()
        
        # Séparer standard et clonées pour l'affichage
        standard_voices = []
        cloned_voices = []
        
        # Voix standard
        for voice_id, voice_data in voices_data['voices'].items():
            standard_voices.append({
                'id': voice_id,
                'name': voice_data.get('name', voice_id),
                'display_name': voice_data.get('display_name', voice_data.get('name', voice_id)),
                'model': voice_data.get('model', 'edge-tts')
            })
        
        # Voix clonées
        for voice_id, voice_data in voices_data['cloned_voices'].items():
            if voice_data.get('processing_status') == 'ready':
                cloned_voices.append({
                    'id': voice_id,
                    'name': voice_data.get('name', voice_id),
                    'display_name': voice_data.get('display_name', voice_data.get('name', voice_id)),
                    'model': 'xtts-v2',
                    'status': voice_data.get('processing_status', 'unknown')
                })
        
        return {
            'standard_voices': standard_voices,
            'cloned_voices': cloned_voices,
            'default_voice': voices_data.get('default_voice', 'jarvis')
        }
    
    # ========================================================================
    # MÉTHODES LEGACY (COMPATIBILITÉ)
    # ========================================================================
    
    async def speak(self, text: str):
        """Méthode legacy - Délègue à speak_streaming"""
        await self.speak_streaming(text)
    
    async def add_to_queue(self, text: str):
        """Méthode legacy - Queue un chunk"""
        if self.pipeline:
            await self.pipeline.queue_text_chunk(text)
        else:
            await self.speak_simple(text)
    
    def start_tts_worker(self):
        """Méthode legacy - Démarre le pipeline"""
        if self.pipeline:
            self.pipeline.start_streaming_workers()
    
    def stop_tts_worker(self):
        """Méthode legacy - Arrête le pipeline"""
        if self.pipeline:
            self.pipeline.stop_pipeline()
    
    # ========================================================================
    # STATUT ET DEBUG
    # ========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Retourne le statut complet du système TTS"""
        base_status = {
            'personality': self.personality,
            'voice_config': self.voice_config,
            'stats': self.stats.copy()
        }
        
        # Ajouter statuts des composants
        if hasattr(self, 'audio_generator'):
            base_status['audio_generator'] = self.audio_generator.get_status()
        
        if hasattr(self, 'pipeline'):
            base_status['pipeline'] = self.pipeline.get_status()
        
        if hasattr(self, 'voice_cloner'):
            base_status['voice_cloner'] = self.voice_cloner.get_status()
        
        return base_status
    
    def get_personality(self) -> str:
        """Retourne la personnalité actuelle"""
        return self.personality
    
    def get_display_name(self) -> str:
        """Retourne le nom d'affichage formaté"""
        voice_data = self.voice_cloner.get_voice_config(self.personality)
        if voice_data and 'display_name' in voice_data:
            return voice_data['display_name']
        else:
            return f"Assistant virtuel - {self.personality}"
    
    # ========================================================================
    # OPTIMISATIONS ET RÉGLAGES
    # ========================================================================
    
    def update_voice_settings(self, speed: float = None, volume: int = None):
        """Met à jour les réglages voix dynamiquement"""
        if 'personality_config' not in self.voice_config:
            self.voice_config['personality_config'] = {}
        
        if speed is not None:
            self.voice_config['personality_config']['voice_speed'] = max(0.5, min(2.0, speed))
            log.debug(f"Vitesse voix: {speed}")
        
        if volume is not None:
            self.voice_config['personality_config']['voice_volume'] = max(0, min(100, volume))
            log.debug(f"Volume voix: {volume}")
        
        # Propager au pipeline
        if self.pipeline:
            self.pipeline.update_voice_config(self.voice_config)
    
    def set_chunk_size(self, size: int):
        """Configure la taille des chunks pour streaming"""
        self.chunk_size = max(50, min(300, size))
        log.debug(f"Taille chunks: {self.chunk_size}")
    
    # ========================================================================
    # NETTOYAGE
    # ========================================================================
    
    def cleanup(self):
        """Nettoie toutes les ressources"""
        log.debug("Nettoyage TTS...")
        
        # Arrêter pipeline
        if hasattr(self, 'pipeline'):
            self.pipeline.stop_pipeline()
        
        # Nettoyer composants
        if hasattr(self, 'audio_generator'):
            self.audio_generator.cleanup()
        
        if hasattr(self, 'voice_cloner'):
            self.voice_cloner.cleanup()
        
        log.debug("TTS nettoyé")
    
    def __del__(self):
        """Destructeur - Nettoyage automatique"""
        try:
            self.cleanup()
        except:
            pass


# ============================================================================
# UTILITAIRES ET HELPERS
# ============================================================================

def create_tts_from_voice_name(voice_name: str) -> TextToSpeech:
    """
    Factory function - Crée un TTS depuis un nom de voix
    Remplace les anciens appels directs au constructeur
    """
    return TextToSpeech(personality=voice_name)


def create_edge_tts(voice_name: str, edge_voice: str) -> TextToSpeech:
    """Factory function - Crée un TTS Edge-TTS"""
    return TextToSpeech(
        model_name="edge-tts",
        personality=voice_name,
        edge_voice=edge_voice
    )


def create_xtts(voice_name: str, sample_path: str) -> TextToSpeech:
    """Factory function - Crée un TTS XTTS"""
    return TextToSpeech(
        model_name="xtts-v2",
        personality=voice_name,
        sample_path=sample_path
    )


# ============================================================================
# EXEMPLE D'UTILISATION
# ============================================================================

async def example_usage():
    """Exemple d'utilisation du nouveau TTS"""
    
    print("🎤 Nouveau TTS unifié - Exemple")
    
    # Créer TTS depuis nom de voix (cherche dans VoiceCloner)
    tts = create_tts_from_voice_name("jarvis")
    
    # Lister voix disponibles
    voices = tts.list_available_voices()
    print(f"Voix standard: {len(voices['standard_voices'])}")
    print(f"Voix clonées: {len(voices['cloned_voices'])}")
    
    # Parler avec streaming
    await tts.speak_streaming("Bonjour ! Ceci est un test du nouveau système TTS unifié. Il utilise AudioGenerator pour la génération et AudioPipeline pour le streaming.")
    
    # Changer de voix si disponible
    if voices['cloned_voices']:
        cloned_voice = voices['cloned_voices'][0]
        success = await tts.switch_voice(cloned_voice['name'])
        if success:
            await tts.speak_streaming("Maintenant je parle avec une voix clonée !")
    
    # Statut final
    status = tts.get_status()
    print(f"Statistiques: {status['stats']}")
    
    # Nettoyage
    tts.cleanup()


if __name__ == "__main__":
    print("🗣️ TTS Unifié - Architecture complète")
    
    # Test simple
    try:
        tts = create_edge_tts("Test", "fr-FR-DeniseNeural")
        print(f"TTS créé: {tts.personality}")
        print(f"Config: {tts.voice_config}")
        print(f"Statut: {tts.get_status()}")
        
        # Test voix disponibles
        voices = tts.list_available_voices()
        print(f"Voix disponibles: {len(voices['standard_voices']) + len(voices['cloned_voices'])}")
        
    except Exception as e:
        print(f"Erreur test: {e}")
    
    # Test async complet (décommenté si voulu)
    # asyncio.run(example_usage())