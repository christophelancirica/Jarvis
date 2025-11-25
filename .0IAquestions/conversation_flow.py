"""
conversation_flow.py - Flux de conversation unifié (Lobes Temporaux)
Responsabilité : Messages, streaming LLM, STT/TTS
Migré depuis web_modules/conversation_handler.py et adapté pour lobes_temporaux
"""

import time
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional
import sys

# Imports des modules - Réutilisation modules existants
sys.path.append(str(Path(__file__).parent.parent))
from cortex_prefrontal.llm_client import JarvisLLM  # LLM unifié avec streaming
from lobes_temporaux.stt import SpeechToText  # Module local
from lobes_temporaux.tts import TextToSpeech  # Module local
from hypothalamus.device_manager import DeviceManager
from hypothalamus.voice_manager import VoiceManager
from hypothalamus.logger import log

class ConversationFlow:
    """Flux de conversation unifié avec vrai streaming (Lobes Temporaux)"""
    
    def __init__(self):
        # Instances des modules (RÉUTILISATION maximale)
        self.llm = None  # LLM unifié
        self.stt = None  # Module local lobes_temporaux
        self.tts = None  # Module local lobes_temporaux
        
        # Configuration actuelle
        self.personality = None
        self.is_initialized = False
        
        # Historique de conversation
        self.conversation_history = []
        
        # Callback WebSocket
        self.websocket_callback: Optional[Callable] = None
        
        # Stats de session
        self.session_stats = {
            'messages_count': 0,
            'total_tokens': 0,
            'total_time': 0.0,
            'avg_response_time': 0.0,
            'avg_ttft': 0.0
        }
        
        log.info("ConversationFlow créé (Lobes Temporaux - Réutilise modules)")
    
    async def auto_initialize(self) -> bool:
        """Initialisation automatique sans interaction utilisateur"""
        try:
            log.info("Initialisation automatique ConversationFlow...")
            
            # 1. Configuration microphone automatique (RÉUTILISE device_manager)
            device_mgr = DeviceManager()
            saved_index, saved_name = device_mgr.load_saved_device()
            
            if saved_index is not None:
                exists, _ = device_mgr.verify_device(saved_index)
                device_index = saved_index if exists else None
            else:
                device_index = self._find_first_microphone()
            
            if device_index is None:
                log.error("Aucun microphone disponible")
                return False
            
            # 2. Configuration voix automatique (RÉUTILISE voice_manager)
            voice_mgr = VoiceManager()
            saved_id, saved_personality, saved_model, edge_voice = voice_mgr.load_saved_voice()
            
            if saved_personality and saved_model:
                personality, tts_model = saved_personality, saved_model
            else:
                # Configuration par défaut
                personality = "Samantha"
                tts_model = "edge-tts"
                edge_voice = "fr-FR-DeniseNeural"
            
            # 3. Initialiser les modules (RÉUTILISATION COMPLÈTE)
            self.llm = JarvisLLM(personality=personality)  # Cortex préfrontal
            self.stt = SpeechToText(device_index=device_index)  # Module local
            self.tts = TextToSpeech(  # Module local
                model_name=tts_model, 
                personality=personality, 
                edge_voice=edge_voice
            )
            
            self.personality = personality
            self.is_initialized = True
            
            log.success(f"ConversationFlow initialisé - {personality} prêt (streaming actif)")
            return True
            
        except Exception as e:
            log.error(f"Erreur initialisation ConversationFlow: {e}")
            return False
    
    def _find_first_microphone(self) -> Optional[int]:
        """Trouve le premier microphone disponible"""
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            
            for i in range(p.get_device_count()):
                try:
                    info = p.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        p.terminate()
                        log.info(f"Microphone trouvé: {info['name']}")
                        return i
                except:
                    continue
            
            p.terminate()
            return None
            
        except Exception as e:
            log.error(f"Erreur recherche microphone: {e}")
            return None
    
    async def process_text_message(self, message: str):
        """Traite un message texte utilisateur avec VRAI streaming"""
        if not self.is_initialized:
            await self._send_error("Système non initialisé")
            return
        
        try:
            log.info(f"Message texte reçu: {message[:50]}...")
            
            # Ajouter à l'historique
            self._add_to_history('user', message)
            
            # Notifier le début de traitement
            await self._send_event('message_processing_start', message)
            
            # 🔥 VRAI STREAMING depuis Ollama (LLM unifié)
            session_start = time.time()
            full_response = ""
            token_count = 0
            first_token_time = None
            
            # Stream les tokens un par un
            for token in self.llm.generate_response_stream(message):
                # Premier token - mesurer TTFT
                if first_token_time is None:
                    first_token_time = time.time() - session_start
                    await self._send_event('first_token', token, {
                        'ttft': first_token_time
                    })
                
                # Envoyer chaque token à l'interface
                await self._send_event('llm_token', token)
                
                # Construire la réponse complète
                full_response += token
                token_count += 1
                
                # Petite pause pour éviter l'inondation WebSocket
                if token_count % 10 == 0:
                    await asyncio.sleep(0.001)
            
            # Fin du streaming
            total_time = time.time() - session_start
            tokens_per_second = token_count / max(total_time, 0.001)
            
            await self._send_event('llm_complete', full_response, {
                'total_time': total_time,
                'token_count': token_count,
                'ttft': first_token_time or 0,
                'tokens_per_second': tokens_per_second
            })
            
            # Ajouter la réponse complète à l'historique
            self._add_to_history('assistant', full_response, token_count)
            
            # Mettre à jour les stats
            self._update_session_stats({
                'total_time': total_time,
                'token_count': token_count,
                'ttft': first_token_time or 0
            })
            
            # TTS de la réponse complète (en parallèle, module local)
            if self.tts and full_response.strip():
                asyncio.create_task(self._speak_response(full_response))
            
            log.success(f"Message traité: {token_count} tokens en {total_time:.2f}s ({tokens_per_second:.1f} tok/s)")
            
        except Exception as e:
            log.error(f"Erreur traitement message: {e}")
            await self._send_error(f"Erreur traitement: {str(e)}")
    
    async def _speak_response(self, text: str):
        """Fait parler le TTS en arrière-plan (module local)"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, 
                self.tts.speak, 
                text
            )
        except Exception as e:
            log.error(f"Erreur TTS: {e}")
    
    async def process_voice_input(self):
        """Traite l'entrée vocale (module STT local)"""
        if not self.is_initialized or not self.stt:
            await self._send_error("STT non disponible")
            return
        
        try:
            log.info("Début de l'écoute vocale")
            
            # Signal de début d'écoute
            await self._send_event('listening_start', '')
            
            # Écouter (bloquant, mais dans un thread séparé, module local)
            loop = asyncio.get_event_loop()
            transcription = await loop.run_in_executor(
                None, 
                self.stt.listen_with_vad, 
                30,  # timeout
                1.5  # silence_duration
            )
            
            # Signal de fin d'écoute
            await self._send_event('listening_end', '')
            
            if transcription and transcription.strip():
                log.success(f"Transcription: '{transcription}'")
                
                # Envoyer la transcription
                await self._send_event('transcription', transcription)
                
                # Traiter comme un message normal
                await self.process_text_message(transcription)
            else:
                log.info("Aucune voix détectée (silence)")
                # Pas d'erreur visible, juste un log
            
        except Exception as e:
            log.error(f"Erreur STT: {e}")
            await self._send_event('listening_end', '')
            await self._send_error(f"Erreur microphone: {str(e)}")
    
    async def reload_tts(self, tts_model: str, personality: str, edge_voice: str = None):
        """Recharge le TTS avec une nouvelle configuration (RÉUTILISE modules)"""
        try:
            log.info(f"Rechargement TTS: {personality} ({tts_model})")
            
            # Créer nouveau TTS (module local)
            self.tts = TextToSpeech(
                model_name=tts_model,
                personality=personality,
                edge_voice=edge_voice
            )
            
            # Recharger aussi le LLM avec nouvelle personnalité (cortex_prefrontal)
            self.llm = JarvisLLM(personality=personality)
            
            # Mettre à jour la personnalité
            self.personality = personality
            
            log.success(f"TTS et LLM rechargés: {personality}")
            
        except Exception as e:
            log.error(f"Erreur rechargement TTS: {e}")
            raise
    
    def get_personality(self) -> str:
        """Retourne la personnalité actuelle"""
        return self.personality or "Samantha"
    
    def get_history(self) -> Dict[str, Any]:
        """Retourne l'historique de conversation"""
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
            'avg_ttft': 0.0
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
            'token_count': token_count
        }
        
        self.conversation_history.append(entry)
        
        # Limiter l'historique (garder les 100 derniers messages)
        if len(self.conversation_history) > 100:
            self.conversation_history = self.conversation_history[-100:]
    
    def _update_session_stats(self, result: Dict[str, Any]):
        """Met à jour les statistiques de session"""
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
    
    async def initialize(self):
        """Point d'entrée d'initialisation"""
        # L'initialisation réelle se fait dans auto_initialize()
        pass
    
    def stop(self):
        """Arrête proprement le gestionnaire"""
        log.info("ConversationFlow arrêté")