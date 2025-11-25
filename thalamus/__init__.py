"""
thalamus - Hub de communication central (Gare de triage neurologique)
Rôle : Router les informations entre l'interface web et les modules Jarvis
"""

from .websocket_relay import WebSocketRelay
from .message_router import MessageRouter
from .interface_bridge import InterfaceBridge

__all__ = ['WebSocketRelay', 'MessageRouter', 'InterfaceBridge']