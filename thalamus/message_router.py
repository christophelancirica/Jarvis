"""
message_router.py - Routage intelligent des messages (Thalamus)
Responsabilité : Router les messages vers les bons modules selon leur type
"""

from pathlib import Path
import sys

# Import logger depuis hypothalamus
sys.path.append(str(Path(__file__).parent.parent))
from hypothalamus.logger import log

class MessageRouter:
    """Routeur intelligent de messages (Gare de triage thalamique)"""
    
    def __init__(self):
        # Mapping des types de messages vers les modules cibles
        self.route_map = {
            # Messages de conversation → lobes_temporaux
            'text_message': 'conversation_flow',
            'voice_input': 'conversation_flow',
            'transcription': 'conversation_flow',
            
            # Messages de configuration → hypothalamus
            'config_update': 'config_coordinator',
            'voice_change': 'config_coordinator',
            'device_change': 'config_coordinator',
            
            # Messages système → hypothalamus
            'system_status': 'system_monitor',
            'health_check': 'system_monitor',
            
            # Messages de contrôle → thalamus
            'ping': 'local',
            'connection_test': 'local'
        }
        
        log.info("MessageRouter initialisé (Thalamus)")
    
    def get_target_module(self, message_type: str) -> str:
        """Détermine le module cible pour un type de message"""
        target = self.route_map.get(message_type, 'unknown')
        
        if target == 'unknown':
            log.warning(f"Type de message non routé: {message_type}")
        else:
            log.debug(f"Route: {message_type} → {target}")
        
        return target
    
    def is_local_message(self, message_type: str) -> bool:
        """Vérifie si le message doit être traité localement par le thalamus"""
        return self.route_map.get(message_type) == 'local'
    
    def get_module_priority(self, message_type: str) -> int:
        """Retourne la priorité de traitement (1=urgent, 3=normal, 5=différé)"""
        priority_map = {
            # Messages urgents
            'voice_input': 1,
            'transcription': 1,
            'connection_test': 1,
            
            # Messages normaux
            'text_message': 3,
            'config_update': 3,
            'ping': 3,
            
            # Messages différés
            'health_check': 5,
            'system_status': 5
        }
        
        return priority_map.get(message_type, 3)  # Normal par défaut
    
    def validate_message(self, message: dict) -> tuple[bool, str]:
        """Valide la structure d'un message"""
        if not isinstance(message, dict):
            return False, "Message doit être un dictionnaire"
        
        if 'type' not in message:
            return False, "Champ 'type' manquant"
        
        message_type = message['type']
        
        # Validation spécifique par type
        if message_type in ['text_message', 'transcription']:
            if 'content' not in message or not message['content'].strip():
                return False, "Champ 'content' manquant ou vide"
        
        elif message_type == 'config_update':
            if 'config' not in message:
                return False, "Champ 'config' manquant"
        
        return True, "Message valide"
    
    def get_routing_stats(self) -> dict:
        """Retourne les statistiques de routage"""
        module_counts = {}
        for target in self.route_map.values():
            module_counts[target] = module_counts.get(target, 0) + 1
        
        return {
            'total_routes': len(self.route_map),
            'modules_count': len(set(self.route_map.values())),
            'distribution': module_counts
        }

# Test standalone
if __name__ == "__main__":
    router = MessageRouter()
    
    # Test routing
    test_messages = [
        {'type': 'text_message', 'content': 'Hello'},
        {'type': 'config_update', 'config': {'voice': 'Jarvis'}},
        {'type': 'ping'},
        {'type': 'unknown_type'}
    ]
    
    for msg in test_messages:
        valid, reason = router.validate_message(msg)
        if valid:
            target = router.get_target_module(msg['type'])
            priority = router.get_module_priority(msg['type'])
            print(f"✅ {msg['type']} → {target} (priorité: {priority})")
        else:
            print(f"❌ {msg}: {reason}")
    
    print(f"\n📊 Stats: {router.get_routing_stats()}")