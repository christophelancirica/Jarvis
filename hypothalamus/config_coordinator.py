"""
config_coordinator.py - Coordinateur simplifié
🎯 Utilise SEULEMENT settings.yaml via ConfigManager
"""

import asyncio
from typing import Dict, Any
from hypothalamus.logger import log
from hypothalamus.config_manager import ConfigManager

config = ConfigManager()

class ConfigCoordinator:
    """
    Coordinateur de configuration simplifié
    Utilise SEULEMENT settings.yaml - AUCUN autre fichier
    """
    
    def __init__(self, conversation_flow=None):
        self.conversation_flow = conversation_flow
        log.info("🎯 ConfigCoordinator unifié initialisé")
    
    async def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mise à jour de configuration - VERSION SIMPLIFIÉE
        """
        try:
            # 1. Validation simple
            validated_config = self._validate_config(new_config)
            
            # 2. Application voix si nécessaire
            if 'personality' in validated_config:
                await self._apply_voice_changes(validated_config)
            
            # 3. 🚀 SAUVEGARDE UNIFIÉE - Une seule ligne !
            success = config.update_config(validated_config)
            
            if success:
                return {
                    'success': True,
                    'message': f'Configuration mise à jour: {list(validated_config.keys())}',
                    'config': config.get_config()
                }
            else:
                return {
                    'success': False,
                    'message': 'Erreur sauvegarde',
                    'config': config.get_config()
                }
                
        except Exception as e:
            log.error(f"❌ Erreur update_config: {e}")
            return {
                'success': False,
                'message': f'Erreur: {e}',
                'config': config.get_config()
            }
    
    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validation simple des paramètres"""
        validated = {}
        
        # Mappage direct - plus de conversion compliquée
        if 'personality' in config:
            validated['voice'] = {
                'personality': config['personality']
            }
        
        if 'voice_speed' in config:
            validated['audio'] = validated.get('audio', {})
            validated['audio']['output'] = validated['audio'].get('output', {})
            validated['audio']['output']['speed'] = float(config['voice_speed'])
        
        if 'voice_volume' in config:
            validated['audio'] = validated.get('audio', {})
            validated['audio']['output'] = validated['audio'].get('output', {})
            validated['audio']['output']['volume'] = int(config['voice_volume'])
        
        if 'llm_model' in config:
            validated['llm'] = validated.get('llm', {})
            validated['llm']['model'] = config['llm_model']
        
        if 'llm_temperature' in config:
            validated['llm'] = validated.get('llm', {})
            validated['llm']['temperature'] = float(config['llm_temperature'])
        
        if 'theme' in config:
            validated['interface'] = validated.get('interface', {})
            validated['interface']['theme'] = config['theme']
        
        if 'background' in config:
            validated['interface'] = validated.get('interface', {})
            validated['interface']['background'] = config['background']
        
        if 'background_opacity' in config:
            validated['interface'] = validated.get('interface', {})
            validated['interface']['background_opacity'] = int(config['background_opacity'])
        
        return validated
    
    async def _apply_voice_changes(self, config: Dict[str, Any]):
        """Application des changements de voix"""
        try:
            if not self.conversation_flow:
                log.warning("ConversationFlow non disponible")
                return
            
            voice_config = config.get('voice', {})
            personality = voice_config.get('personality')
            
            if personality:
                # Charger la nouvelle voix
                result = await self.conversation_flow.change_voice(personality)
                log.success(f"🔊 Voix appliquée: {result}")
                
        except Exception as e:
            log.error(f"❌ Erreur application voix: {e}")
    
    def get_current_config(self) -> Dict[str, Any]:
        """Retourne la configuration actuelle"""
        return config.get_config()
    
    def get_available_voices(self) -> Dict[str, Any]:
        """Retourne les voix disponibles"""
        # TODO: Interface avec voice_manager ou liste fixe
        return {
            "standard": {
                "Jarvis": {"name": "Jarvis", "model": "edge-tts"},
                "Samantha": {"name": "Samantha", "model": "edge-tts"},
                "Eloise": {"name": "Eloise", "model": "edge-tts"}
            },
            "cloned": {}  # TODO: Scanner dossier cloned_voices
        }

# Factory function pour remplacer l'ancienne classe
def create_config_coordinator(conversation_flow=None):
    """Crée une instance du coordinateur unifié"""
    return ConfigCoordinator(conversation_flow)

if __name__ == "__main__":
    # Test
    coordinator = ConfigCoordinator()
    print("✅ ConfigCoordinator unifié créé")