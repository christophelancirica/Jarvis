"""
websocket_relay.py - Relais WebSocket central (Thalamus)
Responsabilité : Communication temps réel client/serveur
Migré depuis web_modules/websocket_handler.py
"""

import json
import asyncio
from typing import List
from fastapi import WebSocket
from pathlib import Path
import sys

# Import logger depuis hypothalamus
sys.path.append(str(Path(__file__).parent.parent))
from hypothalamus.logger import log

class WebSocketRelay:
    """Relais centralisé des connexions WebSocket (Thalamus)"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.is_initialized = False
        self.connection_lock = asyncio.Lock()
    
    async def handle_connection(self, websocket: WebSocket, conversation_flow, config_coordinator):
        """Gère une nouvelle connexion WebSocket"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        try:
            # Initialisation automatique
            if not self.is_initialized:
                await self.send_to_client(websocket, {
                    'type': 'status',
                    'content': 'Initialisation automatique...'
                })
                
                success = await conversation_flow.auto_initialize()
                
                if success:
                    personality = conversation_flow.get_personality()
                    await self.send_to_client(websocket, {
                        'type': 'status',
                        'content': 'Prêt !',
                        'personality': f'Assistant virtuel - {personality}'
                    })
                    self.is_initialized = True
                else:
                    await self.send_to_client(websocket, {
                        'type': 'error',
                        'content': 'Échec de l\'initialisation automatique'
                    })
                    return
            else:
                # Déjà initialisé, envoyer le statut
                personality = conversation_flow.get_personality()
                await self.send_to_client(websocket, {
                    'type': 'status',
                    'content': 'Connexion établie',
                    'personality': f'Assistant virtuel - {personality}'
                })
            
            # Connecter les événements de conversation
            conversation_flow.set_websocket_callback(self.broadcast_to_all)
            
            # Boucle de réception des messages
            await self._message_loop(websocket, conversation_flow, config_coordinator)
            
        except Exception as e:
            log.error(f"Erreur WebSocket: {e}")
        finally:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
    
    async def _message_loop(self, websocket: WebSocket, conversation_flow, config_coordinator):
        """Boucle de traitement des messages"""
        try:
            while websocket in self.active_connections:
                try:
                    # Vérifier l'état de la connexion
                    if websocket.client_state.value != 1:  # CONNECTED
                        break
                        
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    # Traitement des messages...
                    await self._route_message(message, conversation_flow, config_coordinator)
                    
                except Exception as e:
                    log.error(f"Erreur message loop: {e}")
                    break
                    
        except Exception as e:
            log.error(f"Erreur critique message loop: {e}")
        finally:
            # Nettoyage garanti
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            log.debug("Connexion WebSocket nettoyée")
    
    async def _route_message(self, message: dict, conversation_flow, config_coordinator):
        """Route les messages vers les bons modules (Thalamus routing)"""
        
        message_type = message.get('type')
        
        if message_type == 'voice_input':
            # Entrée vocale → ConversationFlow (lobes_temporaux)
            await conversation_flow.process_voice_input()    
        elif message_type == 'text_message':  # ✅ AJOUTER CE BLOC
            # Message texte → ConversationFlow
            text = message.get('text', '')
            print(f"🔍 [DEBUG] Message reçu: '{text}' (longueur: {len(text)})")
            if text:
                await conversation_flow.process_text_message(text)
            else:
                log.warning("Message texte vide reçu")
                    
        elif message_type == 'config_update':
            # Mise à jour config → ConfigCoordinator (hypothalamus)
            try:
                print(f"🔍 [DEBUG] AVANT config_coordinator.update_config")
                result = await config_coordinator.update_config(message['config'])
                print(f"🔍 [DEBUG] APRÈS config_coordinator.update_config") 
            except Exception as e:
                print(f"❌ [DEBUG] EXCEPTION dans update_config: {e}")
                import traceback
                traceback.print_exc()
                result = {'success': False, 'message': f'Erreur: {e}'}

            await self.broadcast_to_all({
                'type': 'config_updated',
                'success': result['success'],
                'message': result.get('message', '')
            })
            
            print(f"🔍 RÉPONSE envoyée au client") 
            
        elif message_type == 'ping':
            # Keep-alive
            await self.broadcast_to_all({'type': 'pong'})
        
        else:
            log.warning(f"Type de message inconnu: {message_type}")
    
    async def send_to_client(self, websocket: WebSocket, message: dict):
        """Envoie un message à un client spécifique"""
        try:
            # Vérifier l'état de la connexion AVANT d'envoyer
            if websocket.client_state.value != 1:  # 1 = CONNECTED
                log.debug("WebSocket fermée, suppression de la liste")
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)
                return False
                
            await websocket.send_text(json.dumps(message))
            return True
            
        except Exception as e:
            log.error(f"Erreur envoi message: {e}")
            # Nettoyer immédiatement les connexions fermées
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            return False
    
    async def broadcast_to_all(self, message: dict):
        """Diffuse un message à tous les clients connectés"""
        if not self.active_connections:
            return
        
        # Copier la liste pour éviter les modifications pendant l'itération
        connections_copy = self.active_connections.copy()
        
        for websocket in connections_copy:
            success = await self.send_to_client(websocket, message)
            if not success:
                # La connexion a été nettoyée dans send_to_client
                pass
    
    def get_connection_count(self) -> int:
        """Retourne le nombre de connexions actives"""
        return len(self.active_connections)
    
    async def shutdown(self):
        """Ferme toutes les connexions proprement"""
        for websocket in self.active_connections[:]:
            try:
                await websocket.close()
            except:
                pass
        self.active_connections.clear()
        log.info("WebSocket Relay fermé proprement")