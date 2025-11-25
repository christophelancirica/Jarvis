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
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Router les messages vers les bons modules
                await self._route_message(message, conversation_flow, config_coordinator)
                
            except Exception as e:
                log.error(f"Erreur message loop: {e}")
                break
    
    async def _route_message(self, message: dict, conversation_flow, config_coordinator):
        """Route les messages vers les bons modules (Thalamus routing)"""
        
        message_type = message.get('type')
        
        if message_type == 'text_message':
            # Message texte → ConversationFlow (lobes_temporaux)
            await conversation_flow.process_text_message(message['content'])
            
        elif message_type == 'voice_input':
            # Entrée vocale → ConversationFlow (lobes_temporaux)
            await conversation_flow.process_voice_input()
            
        elif message_type == 'config_update':
            # Mise à jour config → ConfigCoordinator (hypothalamus)
            result = await config_coordinator.apply_config(message['config'])
            await self.broadcast_to_all({
                'type': 'config_updated',
                'success': result['success'],
                'message': result.get('message', '')
            })
            
        elif message_type == 'ping':
            # Keep-alive
            await self.broadcast_to_all({'type': 'pong'})
        
        else:
            log.warning(f"Type de message inconnu: {message_type}")
    
    async def send_to_client(self, websocket: WebSocket, message: dict):
        """Envoie un message à un client spécifique"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            log.error(f"Erreur envoi message: {e}")
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
    
    async def broadcast_to_all(self, message: dict):
        """Diffuse un message à tous les clients connectés"""
        if not self.active_connections:
            return
        
        # Envoyer à tous les clients connectés
        disconnected = []
        for websocket in self.active_connections:
            try:
                await websocket.send_text(json.dumps(message))
            except:
                disconnected.append(websocket)
        
        # Nettoyer les connexions fermées
        for websocket in disconnected:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
    
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