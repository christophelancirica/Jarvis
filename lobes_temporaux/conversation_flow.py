"""
conversation_flow.py - Flux de conversation unifié (Lobes Temporaux) - VERSION FINALE
Responsabilité : Messages, streaming LLM, STT/TTS
MODIFIÉ pour supporter AudioGenerator + AudioPipeline + VoiceCloner
INCLUDES: auto_initialize(), stop(), et toutes les méthodes requises
"""

import time
import asyncio
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional
import sys

# Imports des modules - Réutilisation modules existants
sys.path.append(str(Path(__file__).parent.parent))
from cortex_prefrontal.llm_client import JarvisLLM  # LLM unifié avec streaming
from lobes_temporaux.stt import SpeechToText  # Module local
from lobes_temporaux.tts import TextToSpeech  # Module local (maintenant avec NOUVELLE architecture)
from hypothalamus.device_manager import DeviceManager
from hypothalamus.voice_manager import VoiceManager
from hypothalamus.config_manager import ConfigManager
from hypothalamus.logger import log

class ConversationFlow:
    """Flux de conversation unifié avec vrai streaming (Lobes Temporaux)"""
    
    def __init__(self):
        # Instances des modules (RÉUTILISATION maximale)
        self.llm = None  # LLM unifié
        self.stt = None  # Module local lobes_temporaux
        self.tts = None  # Module local lobes_temporaux avec NOUVELLE architecture
        
        # Configuration actuelle
        self.personality = None
        self.display_name = None
        self.is_initialized = False
        
        # Queue TTS pour streaming séquentiel (LEGACY - pour compatibilité)
        self.tts_queue = asyncio.Queue()
        self.tts_worker_running = False

        # Historique de conversation
        self.conversation_history = []

        # Système anti-duplication
        self.processing_lock = asyncio.Lock()
        self.recent_messages = {}  # Hash -> timestamp

        # Callback WebSocket
        self.websocket_callback: Optional[Callable] = None
        
        # Stats de session (ajout métriques pipeline)
        self.session_stats = {
            'messages_count': 0,
            'total_tokens': 0,
            'total_time': 0.0,
            'avg_response_time': 0.0,
            'avg_ttft': 0.0,
            'pipeline_efficiency': 0.0
        }
        
        log.info("ConversationFlow créé (Lobes Temporaux - Pipeline parallèle)")
    
    async def auto_initialize(self) -> bool:
        """Initialisation automatique sans interaction utilisateur"""
        try:
            log.info("Initialisation automatique ConversationFlow...")
            
            # 1. Configuration microphone automatique (RÉUTILISE device_manager)
            device_mgr = DeviceManager()
            saved_index, _ = device_mgr.load_saved_device()
            device_index = saved_index if saved_index and device_mgr.verify_device(saved_index)[0] else None
            
            if device_index is None:
                log.error("Aucun microphone disponible")
                return False
            
            # 2. Configuration voix automatique (RÉUTILISE voice_manager)
            voice_mgr = VoiceManager()
            _, personality, tts_model, edge_voice, sample_path, embedding_path = voice_mgr.load_saved_voice()
            if not personality:  # Pas de config sauvée
                personality, tts_model, edge_voice, sample_path, embedding_path = "Samantha", "edge-tts", "fr-FR-DeniseNeural", None, None
            
            # 3. Initialiser les modules (RÉUTILISATION COMPLÈTE)
            self.llm = JarvisLLM(personality=personality)  # Cortex préfrontal
            self.stt = SpeechToText(device_index=device_index)  # Module local
            
            # NOUVEAU: Initialisation TTS avec nouvelle architecture
            try:
                # PRIORITÉ 1: Nouvelle architecture
                self.tts = TextToSpeech(personality=personality)
                log.success(f"TTS nouvelle architecture initialisé: {personality}")
            except Exception as tts_error:
                log.warning(f"Fallback ancienne architecture: {tts_error}")
                # PRIORITÉ 2: Ancienne architecture
                if sample_path:
                    from pathlib import Path
                    sample_path_obj = Path(sample_path)
                    if not sample_path_obj.is_absolute():
                        sample_path = str(Path('config') / sample_path)
                self.tts = TextToSpeech(
                    model_name=tts_model, 
                    personality=personality, 
                    edge_voice=edge_voice,
                    sample_path=sample_path,
                    embedding_path=embedding_path
                )
                log.success(f"TTS fallback initialisé: {personality}")
            
            self.personality = personality
            self.display_name = f"Assistant virtuel - {personality}"
            self.is_initialized = True
            
            log.success(f"ConversationFlow initialisé - {personality} prêt (pipeline actif)")
            return True
            
        except Exception as e:
            log.error(f"Erreur initialisation ConversationFlow: {e}")
            return False
    
    async def initialize(self, personality: str = "Jarvis") -> bool:
        """Initialise tous les modules requis pour la conversation"""
        try:
            self.personality = personality
            
            # 1. Configuration microphone automatique (RÉUTILISE device_manager)
            device_mgr = DeviceManager()
            saved_index, _ = device_mgr.load_saved_device()
            device_index = saved_index if saved_index and device_mgr.verify_device(saved_index)[0] else None
            
            if device_index is None:
                log.error("Aucun microphone disponible")
                return False
            
            # 2. Configuration voix automatique (RÉUTILISE voice_manager)
            voice_mgr = VoiceManager()
            _, personality, tts_model, edge_voice, sample_path, embedding_path = voice_mgr.load_saved_voice()
            if not personality:  # Pas de config sauvée
                personality, tts_model, edge_voice, sample_path, embedding_path = "Samantha", "edge-tts", "fr-FR-DeniseNeural", None, None
            
            # 3. Initialisation LLM (Ollama unifié)
            self.llm = JarvisLLM()
            if not await self.llm.initialize():
                log.error("Échec initialisation LLM")
                return False
            
            # 4. Initialisation STT (local)
            self.stt = SpeechToText(device_index=device_index)
            if not self.stt.initialize():
                log.error("Échec initialisation STT")
                return False
            
            # 5. Initialisation TTS (NOUVELLE ARCHITECTURE)
            try:
                # NOUVEAU: Utiliser factory function ou constructeur direct
                self.tts = TextToSpeech(personality=personality)
                log.success(f"TTS nouvelle architecture initialisé: {personality}")
            except Exception as tts_error:
                log.warning(f"Échec nouvelle architecture TTS: {tts_error}")
                # Fallback vers ancienne méthode si nécessaire
                self.tts = TextToSpeech(tts_model, personality, edge_voice, sample_path, embedding_path)
                log.info(f"TTS fallback initialisé: {personality}")
            
            self.is_initialized = True
            
            log.success(f"ConversationFlow initialisé - {personality} prêt (pipeline actif)")
            return True
            
        except Exception as e:
            log.error(f"Erreur initialisation ConversationFlow: {e}")
            return False
    
    async def process_voice_input(self):
        """Traite un message vocal complet : écoute + traitement + réponse"""
        if not self.is_initialized or not self.stt:
            await self._send_error("STT non disponible")
            return
        
        try:
            log.info("Début de l'écoute vocale")
            await self._send_event('listening_start', '')
            
            # Écouter
            loop = asyncio.get_event_loop()
            transcription = await loop.run_in_executor(
                None, 
                self.stt.listen_with_whisper_vad, 
                15
            )
            
            await self._send_event('listening_end', '')
            
            if transcription and transcription.strip():
                await self._send_event('transcription', transcription)
                
                # TRAITER DIRECTEMENT LE MESSAGE (évite la double transcription)
                await self.process_text_message(transcription)
            else:
                log.info("Aucune voix détectée")
                
        except Exception as e:
            log.error(f"Erreur STT: {e}")
            await self._send_event('listening_end', '')
            await self._send_error(f"Erreur microphone: {str(e)}")
            
    async def process_text_message(self, message: str):
        """Traite un message texte utilisateur avec VRAI streaming + Pipeline TTS"""
        # Anti-duplication
        message_hash = hashlib.md5(message.encode()).hexdigest()
        current_time = time.time()
        
        # Vérifier les doublons
        if message_hash in self.recent_messages:
            if current_time - self.recent_messages[message_hash] < 2.0:
                log.warning(f"Message dupliqué ignoré: {message[:30]}...")
                return
        
        self.recent_messages[message_hash] = current_time
        
        # Nettoyer les vieux hashes (>10s)
        self.recent_messages = {
            h: t for h, t in self.recent_messages.items() 
            if current_time - t < 10
        }
        
        # Lock pour éviter les traitements simultanés
        async with self.processing_lock:
                
            if not self.is_initialized:
                await self._send_error("Système non initialisé")
                return
            
            try:
                log.info(f"Message texte reçu: {message[:50]}...")
                
                # Ajouter à l'historique
                self._add_to_history('user', message)
                
                # Notifier le début de traitement
                await self._send_event('message_processing_start', message)
                
                # 🚀 NOUVEAU: Pipeline complet LLM + TTS parallèle
                await self._process_with_parallel_pipeline(message)
                
            except Exception as e:
                log.error(f"Erreur traitement message: {e}")
                await self._send_error(f"Erreur traitement: {str(e)}")
    
    def _supports_pipeline(self) -> bool:
        """Détermine si le TTS supporte le pipeline parallèle - ADAPTÉ NOUVELLE ARCHITECTURE"""
        # PRIORITÉ 1: Vérifier si c'est la NOUVELLE architecture
        if hasattr(self.tts, 'pipeline') and hasattr(self.tts.pipeline, 'queue_text_chunk'):
            log.debug("✅ NOUVELLE architecture TTS détectée", "🔊")
            return True
        
        # PRIORITÉ 2: Compatibilité avec ancienne architecture
        if (hasattr(self.tts, 'is_edge') and 
            self.tts.is_edge and 
            hasattr(self.tts, 'add_text_chunk')):
            log.debug("⚠️ Ancienne architecture TTS détectée", "🔊")
            return True
            
        log.debug("❌ Aucune architecture pipeline détectée", "⚠️")
        return False

    async def _send_to_tts(self, text: str):
        """Envoie du texte au TTS - ADAPTÉ NOUVELLE ARCHITECTURE"""
        # Vérifier si l'audio est en sourdine
        config_manager = ConfigManager()
        is_muted = config_manager.get_config().get('audio', {}).get('output', {}).get('muted', False)

        if is_muted:
            log.debug("🔇 Audio en sourdine, chunk TTS ignoré.", "🔊")
            return

        # PRIORITÉ 1: Nouvelle architecture avec AudioPipeline
        if hasattr(self.tts, 'pipeline') and hasattr(self.tts.pipeline, 'queue_text_chunk'):
            await self.tts.pipeline.queue_text_chunk(text)
            log.debug(f"✅ NOUVEAU pipeline: chunk envoyé", "🔊")
        
        # PRIORITÉ 2: Ancienne architecture pipeline
        elif (hasattr(self.tts, 'is_edge') and 
              self.tts.is_edge and 
              hasattr(self.tts, 'add_text_chunk')):
            await self.tts.add_text_chunk(text)
            log.debug(f"✅ ANCIEN pipeline: chunk envoyé", "🔊")
        
        # PRIORITÉ 3: Fallback legacy
        else:
            await self.tts_queue.put(text)
            if not self.tts_worker_running:
                asyncio.create_task(self._tts_worker())
            log.debug(f"⚠️ Legacy: chunk envoyé", "⚠️")

    async def _process_with_parallel_pipeline(self, message: str):
        """Pipeline complet LLM streaming + TTS parallèle ADAPTÉ NOUVELLE ARCHITECTURE"""
        session_start = time.time()
        full_response = ""
        token_count = 0
        first_token_time = None
        first_audio_time = None
        sentence_buffer = ""
        
        try:
            log.debug("🚀 Démarrage pipeline complet LLM + TTS", "🔊")

            # 🔇 Vérification mode muet (Optimisation P1)
            config_manager = ConfigManager()
            is_muted = config_manager.get_config().get('audio', {}).get('output', {}).get('muted', False)

            if is_muted:
                log.debug("🔇 Mode Muet activé : Pipeline TTS désactivé (Optimisation)", "🔊")
            
            # Démarrer le pipeline TTS si supporté ET non muet
            if not is_muted and self._supports_pipeline():
                log.debug("🚀 PIPELINE: Démarrage workers...", "🔊")
                
                # NOUVEAU: Démarrage pipeline selon architecture
                if hasattr(self.tts, 'pipeline'):
                    self.tts.pipeline.start_streaming_workers()
                    log.debug("✅ NOUVEAU pipeline TTS démarré", "🔊")
                elif hasattr(self.tts, '_start_parallel_workers'):
                    await self.tts._start_parallel_workers()
                    log.debug("✅ ANCIEN pipeline TTS démarré", "🔊")
                
                log.debug("✅ Pipeline TTS démarré", "🔊")
            elif is_muted:
                log.debug("🔇 Pas de démarrage workers (Muet)", "🔊")
            else:
                log.debug("⚠️ Utilisation ancien système TTS", "⚠️")
            
            # 🔥 STREAMING depuis Ollama (LLM unifié)
            # 🧠 NOUVEAU: Préchauffer TTS pendant que LLM démarre sa réflexion
            if not is_muted and self._supports_pipeline():
                # NOUVEAU: Warm-up selon architecture
                if hasattr(self.tts, 'pipeline'):
                    # Le warm-up est automatique dans AudioPipeline
                    log.debug("🔥 Warm-up automatique NOUVEAU pipeline", "🔊")
                elif hasattr(self.tts, 'warm_up_during_llm_thinking'):
                    asyncio.create_task(self.tts.warm_up_during_llm_thinking())
                    log.debug("🔥 Warm-up ANCIEN pipeline", "🔊")
            
            for token in self.llm.generate_response_stream(message):
                # Premier token - mesurer TTFT
                if first_token_time is None:
                    first_token_time = time.time() - session_start
                    await self._send_event('first_token', token, {
                        'ttft': first_token_time
                    })
                
                # Envoyer chaque token à l'interface
                await self._send_event('llm_token', token)
                full_response += token
                token_count += 1
                sentence_buffer += token
                
                # 🔥 OPTIMISATION: Détection phrase complète → Envoi IMMÉDIAT TTS
                # Ne traiter pour le TTS que si non muet
                if not is_muted and self._is_sentence_complete(sentence_buffer):
                    sentence_to_process = sentence_buffer.strip()
                    
                    if sentence_to_process:
                        # Nettoyer le texte pour le TTS
                        clean_sentence = self._clean_text_for_tts(sentence_to_process)
                        
                        if clean_sentence:
                            # Mesurer temps premier audio
                            if first_audio_time is None:
                                first_audio_time = time.time() - session_start

                            # Envoi au TTS (nouvelle architecture compatible)
                            await self._send_to_tts(clean_sentence)
                            log.debug(f"✅ Chunk envoyé: {clean_sentence[:40]}...", "🔊")
                    
                    sentence_buffer = ""  # Reset buffer
                
                # Petite pause pour éviter l'inondation WebSocket
                if token_count % 10 == 0:
                    await asyncio.sleep(0.001)
            
            # Traiter le reste du buffer s'il y a du contenu
            if not is_muted and sentence_buffer.strip():
                clean_last_chunk = self._clean_text_for_tts(sentence_buffer.strip())
                if clean_last_chunk:
                    await self._send_to_tts(clean_last_chunk)
                    log.debug("✅ Dernier chunk envoyé", "🔊")
            
            # Finaliser le pipeline si actif avec timeout dynamique
            if not is_muted and self._supports_pipeline():
                # Timeout adaptatif selon la longueur de la réponse
                estimated_time = token_count * 0.3  # 0.3s par token
                dynamic_timeout = max(60.0, estimated_time)  # Minimum 60s
                
                log.debug(f"⏳ Attente fin conversation ({dynamic_timeout:.0f}s max)...", "🔊")
                
                # NOUVEAU: Finalisation selon architecture
                if hasattr(self.tts, 'pipeline'):
                    # Attendre que le NOUVEAU pipeline se vide
                    start_wait = time.time()
                    while (time.time() - start_wait) < dynamic_timeout:
                        status = self.tts.pipeline.get_status()
                        if (status['chunks_in_generation_queue'] == 0 and 
                            status['chunks_in_playback_queue'] == 0):
                            break
                        await asyncio.sleep(0.5)
                    log.debug("✅ NOUVEAU pipeline terminé", "🔊")
                    
                elif hasattr(self.tts, 'finalize_pipeline'):
                    await self.tts.finalize_pipeline(timeout=dynamic_timeout)
                    log.debug("✅ ANCIEN pipeline terminé", "🔊")
                
                log.debug("✅ Conversation terminée", "🔊")
            
            total_time = time.time() - session_start
            tokens_per_second = token_count / max(total_time, 0.001)
            
            # Calculer efficacité du pipeline
            pipeline_efficiency = 0.0
            
            # NOUVEAU: Stats selon architecture
            if hasattr(self.tts, 'pipeline'):
                status = self.tts.pipeline.get_status()
                if status.get('stats', {}).get('chunks_generated', 0) > 0:
                    stats = status['stats']
                    if stats['total_generation_time'] > 0 and stats['total_playback_time'] > 0:
                        sequential_time = stats['total_generation_time'] + stats['total_playback_time']
                        parallel_time = max(stats['total_generation_time'], stats['total_playback_time'])
                        pipeline_efficiency = ((sequential_time - parallel_time) / sequential_time * 100)
            
            # ANCIEN: Stats ancienne architecture
            elif hasattr(self.tts, 'is_edge') and self.tts.is_edge and hasattr(self.tts, 'pipeline_stats'):
                stats = self.tts.pipeline_stats
                if stats['total_generation_time'] > 0 and stats['total_playback_time'] > 0:
                    sequential_time = stats['total_generation_time'] + stats['total_playback_time']
                    parallel_time = max(stats['total_generation_time'], stats['total_playback_time'])
                    pipeline_efficiency = ((sequential_time - parallel_time) / sequential_time * 100)
            
            await self._send_event('llm_complete', full_response, {
                'total_time': total_time,
                'token_count': token_count,
                'ttft': first_token_time or 0,
                'first_audio_time': first_audio_time or 0,
                'tokens_per_second': tokens_per_second,
                'pipeline_efficiency': pipeline_efficiency
            })
            
            # Ajouter la réponse complète à l'historique
            self._add_to_history('assistant', full_response, token_count)
            
            # Mettre à jour les stats
            self._update_session_stats({
                'total_time': total_time,
                'token_count': token_count,
                'ttft': first_token_time or 0,
                'first_audio_time': first_audio_time or 0,
                'tokens_per_second': tokens_per_second,
                'pipeline_efficiency': pipeline_efficiency
            })
            
            log.success(f"Message traité: {token_count} tokens en {total_time:.2f}s ({tokens_per_second:.1f} tok/s, gain: {pipeline_efficiency:.1f}%)")
            
        except Exception as e:
            log.error(f"Erreur pipeline parallèle: {e}")
            raise
    
    def _is_sentence_complete(self, text: str) -> bool:
        """Détecte si une phrase est complète pour envoyer au TTS"""
        if not text.strip():
            return False
        
        # Délimiteurs de fin de phrase
        sentence_enders = ['.', '!', '?', ':', ';']
        
        # Vérifier fin de phrase
        if any(text.rstrip().endswith(ender) for ender in sentence_enders):
            return True
        
        # Phrases courtes (questions, exclamations)
        if len(text.split()) >= 4 and text.rstrip().endswith(('?', '!')):
            return True
        
        return False

    def _clean_text_for_tts(self, text: str) -> str:
        """Nettoie le texte avant de l'envoyer au TTS."""
        import re
        # Supprime le contenu entre les balises <think> et </think>
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # Supprime les émojis
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE,
        )
        text = emoji_pattern.sub(r"", text)
        # Supprime les astérisques d'action (ex: *sourit*)
        text = re.sub(r'\*.*?\*', '', text)
        return text.strip()
    
    async def reload_tts(self, model_name, personality, edge_voice=None, sample_path=None, embedding_path=None):
        """Recharge le TTS avec une nouvelle voix"""
        try:
            log.info(f"Rechargement TTS : {personality}")
            
            # Arrêter pipeline actuel si nécessaire
            if hasattr(self.tts, 'pipeline') and self.tts.pipeline.pipeline_active:
                self.tts.pipeline.stop_pipeline()
                await asyncio.sleep(0.5)  # Laisser temps d'arrêt
            elif hasattr(self.tts, 'parallel_pipeline_active') and self.tts.parallel_pipeline_active:
                self.tts.parallel_pipeline_active = False
                await asyncio.sleep(0.5)  # Laisser temps d'arrêt
            
            # NOUVEAU: Créer nouvelle instance TTS avec nouvelle architecture
            try:
                self.tts = TextToSpeech(personality=personality)
                log.success(f"TTS nouvelle architecture rechargé: {personality}")
            except Exception as e:
                log.warning(f"Fallback ancienne architecture: {e}")
                # Fallback vers ancienne méthode
                self.tts = TextToSpeech(
                    model_name=model_name,
                    personality=personality,
                    edge_voice=edge_voice,
                    sample_path=sample_path,
                    embedding_path=embedding_path
                )
                log.success(f"TTS fallback rechargé: {personality}")
            
            log.success(f"TTS rechargé avec pipeline : {personality}")
            
        except Exception as e:
            log.error(f"Erreur rechargement TTS: {e}")
            raise

    async def reload_llm(self, model_name: str):
        """Change le modèle du client LLM existant."""
        try:
            if self.llm:
                log.info(f"Changement du modèle LLM vers : {model_name}")
                self.llm.change_model(model_name)
                log.success(f"Modèle LLM changé vers : {model_name}")
            else:
                log.warning("Le client LLM n'est pas initialisé, impossible de changer de modèle.")
        except Exception as e:
            log.error(f"Erreur lors du changement de modèle LLM : {e}")
            raise
    
    def get_personality(self) -> str:
        """Retourne la personnalité actuelle"""
        return self.personality or "Samantha"
    
    def get_display_name(self) -> str:
        """Retourne le nom d'affichage formaté"""
        if hasattr(self, 'display_name') and self.display_name:
            return self.display_name
        else:
            personality = self.get_personality()
            return f"Assistant virtuel - {personality}"
        
    def update_voice_settings(self, speed: float = None, volume: int = None):
        """Met à jour les paramètres de voix en direct"""
        if self.tts:
            self.tts.update_voice_settings(speed, volume)
            log.info(f"🔊 Paramètres voix mis à jour: Speed={speed}, Volume={volume}")

    def get_history(self) -> Dict[str, Any]:
        """Retourne l'historique de conversation avec stats pipeline"""
        return {
            'success': True,
            'history': self.conversation_history,
            'stats': self.session_stats
        }
    
    def clear_history(self) -> Dict[str, Any]:
        """Efface l'historique de conversation"""
        self.conversation_history.clear()
        self.session_stats = {
            'messages_count': 0,
            'total_tokens': 0,
            'total_time': 0.0,
            'avg_response_time': 0.0,
            'avg_ttft': 0.0,
            'pipeline_efficiency': 0.0
        }
        
        log.info("Historique de conversation effacé")
        return {'success': True}
    
    def set_websocket_callback(self, callback: Callable):
        """Définit le callback WebSocket pour les événements"""
        self.websocket_callback = callback
    
    def _add_to_history(self, sender: str, content: str, token_count: int = 0):
        """Ajoute un message à l'historique"""
        entry = {
            'sender': sender,
            'content': content,
            'timestamp': time.time(),
            'token_count': token_count if sender == 'assistant' else 0
        }
        
        self.conversation_history.append(entry)
        
        # Limiter l'historique (garder les 100 derniers messages)
        if len(self.conversation_history) > 100:
            self.conversation_history = self.conversation_history[-100:]
    
    def _update_session_stats(self, result: Dict[str, Any]):
        """Met à jour les statistiques de session avec métriques pipeline"""
        self.session_stats['messages_count'] += 1
        self.session_stats['total_tokens'] += result.get('token_count', 0)
        self.session_stats['total_time'] += result.get('total_time', 0)
        
        # TTFT moyen
        if 'ttft' in result:
            current_ttft = self.session_stats.get('avg_ttft', 0)
            count = self.session_stats['messages_count']
            self.session_stats['avg_ttft'] = (current_ttft * (count - 1) + result['ttft']) / count
        
        # Temps de réponse moyen
        if self.session_stats['messages_count'] > 0:
            self.session_stats['avg_response_time'] = (
                self.session_stats['total_time'] / self.session_stats['messages_count']
            )
        
        # NOUVEAU: Efficacité pipeline moyenne
        if 'pipeline_efficiency' in result and result['pipeline_efficiency'] > 0:
            current_eff = self.session_stats.get('pipeline_efficiency', 0)
            count = self.session_stats['messages_count']
            self.session_stats['pipeline_efficiency'] = (current_eff * (count - 1) + result['pipeline_efficiency']) / count
    
    async def _send_event(self, event_type: str, content: str, metadata: Dict = None):
        """Envoie un événement via WebSocket"""
        if self.websocket_callback:
            event_data = {
                'type': event_type,
                'content': content,
                'timestamp': time.time(),
                'metadata': metadata or {}
            }
            await self.websocket_callback(event_data)
        else:
            log.warning(f"⚠️ WebSocket callback non défini pour: {event_type}")
    
    async def _send_error(self, error_message: str):
        """Envoie une erreur via WebSocket"""
        await self._send_event('error', error_message)
    
    def stop(self):
        """Arrête proprement le gestionnaire et le pipeline"""
        # Arrêter pipeline TTS si actif
        if hasattr(self.tts, 'pipeline') and hasattr(self.tts.pipeline, 'stop_pipeline'):
            self.tts.pipeline.stop_pipeline()
        elif hasattr(self.tts, 'parallel_pipeline_active') and self.tts.parallel_pipeline_active:
            self.tts.parallel_pipeline_active = False
        
        log.info("ConversationFlow arrêté avec pipeline")
    
    # === MÉTHODES LEGACY (pour compatibilité) ===
    
    async def _tts_worker(self):
        """Worker TTS simplifié et robuste (LEGACY - pour compatibilité)"""
        if self.tts_worker_running:
            return  # Déjà actif
            
        self.tts_worker_running = True
        log.debug("🔊 TTS worker legacy démarré")
        
        try:
            while self.tts_worker_running:
                try:
                    # Attendre segment (timeout plus long pour le streaming LLM)
                    segment = await asyncio.wait_for(self.tts_queue.get(), timeout=10.0)
                    
                    log.debug(f"🔊 TTS traite (legacy): {segment[:30]}...")
                    
                    # Utiliser l'ancienne méthode fiable OU la nouvelle
                    if hasattr(self.tts, 'speak'):
                        # NOUVEAU système: utiliser speak() async
                        await self.tts.speak(segment)
                    elif hasattr(self.tts, '_speak_response'):
                        # ANCIEN système: utiliser _speak_response
                        await self.tts._speak_response(segment)
                    else:
                        log.error("Aucune méthode TTS disponible")
                    
                    self.tts_queue.task_done()
                    
                except asyncio.TimeoutError:
                    # Plus rien depuis 10s → arrêter
                    log.debug("🔊 TTS timeout - arrêt propre")
                    break
                    
        except Exception as e:
            log.error(f"❌ Erreur TTS worker legacy: {e}")
        finally:
            self.tts_worker_running = False
            log.debug("🔊 TTS worker legacy arrêté proprement")