"""
config_coordinator.py - Coordination configuration temps réel (Hypothalamus) - VERSION CORRIGÉE
Responsabilité : Paramètres, voix, et configuration système unifiée
"""

import json
import time
from pathlib import Path
from typing import Dict, Any
import sys

# Imports des modules existants hypothalamus (RÉUTILISATION)
sys.path.append(str(Path(__file__).parent.parent))
from hypothalamus.voice_manager import VoiceManager
from hypothalamus.device_manager import DeviceManager
from hypothalamus.logger import log

class ConfigCoordinator:
    """Coordinateur de configuration unifié (Hypothalamus)"""
    
    def __init__(self):
        self.current_config = {
            'personality': 'Samantha',
            'display_name': 'Assistant virtuel - Samantha',
            'tts_model': 'edge-tts',
            'edge_voice': 'fr-FR-DeniseNeural',
            'device_index': None,
            'llm_model': 'llama3.1:8b',
            'theme': 'light',
            'voice_speed': 1.0,
            'voice_volume': 90,
            'audio_sensitivity': 5,
            'llm_temperature': 0.7,
            'interface_animations': True
        }
        
        # RÉUTILISATION des modules existants au lieu de dupliquer
        self.voice_manager = VoiceManager()
        self.device_manager = DeviceManager()
        
        # État des instances actuelles (pour reload)
        self.current_conversation_flow = None
        
        log.info("ConfigCoordinator initialisé (Hypothalamus - Réutilise modules existants)")
    
    def get_current_config(self) -> Dict[str, Any]:
        """Retourne la configuration actuelle"""
        return {
            'success': True,
            'config': self.current_config.copy()
        }
    
    async def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Met à jour la configuration (sans appliquer immédiatement)"""
        try:
            # Valider et fusionner les nouveaux paramètres
            validated_config = self._validate_config(new_config)
            
            # Mettre à jour la config interne
            self.current_config.update(validated_config)
            
            log.info(f"Configuration mise à jour: {list(validated_config.keys())}")
            
            return {
                'success': True,
                'message': 'Configuration mise à jour (cliquez Appliquer pour activer)',
                'config': self.current_config.copy()
            }
            
        except Exception as e:
            log.error(f"Erreur mise à jour config: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def apply_config(self, config_changes: Dict[str, Any]) -> Dict[str, Any]:
        """Applique la configuration en temps réel"""
        try:
            results = []
            
            # 1. Changements de personnalité/voix (RÉUTILISE voice_manager)
            if 'personality' in config_changes or 'edge_voice' in config_changes:
                result = await self._apply_voice_changes(config_changes)
                results.append(result)
            
            # 2. Changements d'interface
            if 'theme' in config_changes:
                self.current_config['theme'] = config_changes['theme']
                results.append("Thème mis à jour")
            
            # 3. Changements audio
            if any(key in config_changes for key in ['voice_speed', 'voice_volume', 'audio_sensitivity']):
                result = self._apply_audio_changes(config_changes)
                results.append(result)
            
            # 4. Sauvegarde persistante (RÉUTILISE modules existants)
            self._save_config()
            
            success_message = "; ".join(results)
            log.success(f"Configuration appliquée: {success_message}")
            
            return {
                'success': True,
                'message': f'Paramètres appliqués: {success_message}',
                'config': self.current_config.copy()
            }
            
        except Exception as e:
            log.error(f"Erreur application config: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _apply_voice_changes(self, changes: Dict[str, Any]) -> str:
        """Applique les changements de voix/personnalité (RÉUTILISE voice_manager)"""
        
        if 'personality' in changes:
            new_personality = changes['personality']
            
            # 🔧 FIX: Mapping des noms de personnalités vers les clés du voice_manager
            personality_to_id = {
                'Jarvis': '1',
                'Samantha': '2',
                'Eloise': '3',
                'Josephine': '4'
            }
            
            # Trouver la clé correspondante
            voice_id = personality_to_id.get(new_personality)
            
            if voice_id and voice_id in self.voice_manager.available_voices:
                voice_info = self.voice_manager.available_voices[voice_id]
                
                # Mettre à jour la config
                self.current_config.update({
                    'personality': new_personality,
                    'display_name': f'Assistant virtuel - {new_personality}',
                    'tts_model': voice_info['model'],
                    'edge_voice': voice_info.get('edge_voice') or voice_info.get('voice')
                })
                
                # Sauvegarder avec le voice_manager existant
                self.voice_manager.save_voice(
                    voice_id=voice_id,
                    personality=new_personality,
                    model=voice_info['model'],
                    edge_voice=voice_info.get('edge_voice') or voice_info.get('voice')
                )
                
                # Notifier le gestionnaire de conversation du changement
                if self.current_conversation_flow:
                    await self.current_conversation_flow.reload_tts(
                        voice_info['model'], 
                        new_personality, 
                        voice_info.get('edge_voice') or voice_info.get('voice')
                    )
                
                return f"Voix changée vers {new_personality}"
            else:
                raise ValueError(f"Personnalité inconnue: {new_personality}")
        
        return "Voix mise à jour"
    
    def _apply_audio_changes(self, changes: Dict[str, Any]) -> str:
        """Applique les changements audio"""
        audio_changes = []
        
        if 'voice_speed' in changes:
            self.current_config['voice_speed'] = float(changes['voice_speed'])
            audio_changes.append("vitesse")
        
        if 'voice_volume' in changes:
            self.current_config['voice_volume'] = int(changes['voice_volume'])
            audio_changes.append("volume")
        
        if 'audio_sensitivity' in changes:
            self.current_config['audio_sensitivity'] = int(changes['audio_sensitivity'])
            audio_changes.append("sensibilité")
        
        return f"Audio mis à jour ({', '.join(audio_changes)})"
    
    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Valide une configuration avant application"""
        validated = {}
        
        # Validation personnalité
        if 'personality' in config:
            valid_personalities = ['Jarvis', 'Samantha', 'Eloise', 'Josephine']
            if config['personality'] in valid_personalities:
                validated['personality'] = config['personality']
        
        # Validation thème
        if 'theme' in config:
            valid_themes = ['light', 'dark', 'jarvis']
            if config['theme'] in valid_themes:
                validated['theme'] = config['theme']
        
        # Validation ranges numériques
        if 'voice_speed' in config:
            speed = float(config['voice_speed'])
            validated['voice_speed'] = max(0.5, min(2.0, speed))
        
        if 'voice_volume' in config:
            volume = int(config['voice_volume'])
            validated['voice_volume'] = max(0, min(100, volume))
        
        if 'audio_sensitivity' in config:
            sensitivity = int(config['audio_sensitivity'])
            validated['audio_sensitivity'] = max(1, min(10, sensitivity))
        
        if 'llm_temperature' in config:
            temp = float(config['llm_temperature'])
            validated['llm_temperature'] = max(0.1, min(1.0, temp))
        
        # Validation boolean
        if 'interface_animations' in config:
            validated['interface_animations'] = bool(config['interface_animations'])
        
        return validated
    
    def _save_config(self):
        """Sauvegarde la configuration de manière persistante (RÉUTILISE modules)"""
        try:
            # Sauvegarder la voix avec le voice_manager existant
            if self.current_config.get('personality'):
                # 🔧 FIX: Utiliser le bon voice_id
                personality_to_id = {
                    'Jarvis': '1',
                    'Samantha': '2',
                    'Eloise': '3',
                    'Josephine': '4'
                }
                voice_id = personality_to_id.get(self.current_config['personality'], '2')
                
                self.voice_manager.save_voice(
                    voice_id=voice_id,
                    personality=self.current_config['personality'],
                    model=self.current_config['tts_model'],
                    edge_voice=self.current_config.get('edge_voice')
                )
            
            log.debug("Configuration sauvegardée (modules hypothalamus)")
            
        except Exception as e:
            log.error(f"Erreur sauvegarde config: {e}")
    
    def get_available_voices(self) -> Dict[str, Any]:
        """Retourne les voix disponibles (RÉUTILISE voice_manager)"""
        return {
            'success': True,
            'voices': self.voice_manager.available_voices
        }
    
    def get_available_devices(self) -> Dict[str, Any]:
        """Retourne les périphériques audio disponibles (RÉUTILISE device_manager)"""
        try:
            # Utiliser le device manager existant
            import pyaudio
            p = pyaudio.PyAudio()
            
            devices = []
            for i in range(p.get_device_count()):
                try:
                    info = p.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        devices.append({
                            'index': i,
                            'name': info['name'],
                            'channels': info['maxInputChannels']
                        })
                except:
                    continue
            
            p.terminate()
            
            return {
                'success': True,
                'devices': devices
            }
            
        except Exception as e:
            log.error(f"Erreur récupération devices: {e}")
            return {
                'success': False,
                'error': str(e),
                'devices': []
            }
    
    def set_conversation_flow(self, flow):
        """Définit le gestionnaire de conversation pour reload TTS"""
        self.current_conversation_flow = flow
    
    def get_display_name(self) -> str:
        """Retourne le nom d'affichage formaté"""
        return self.current_config.get('display_name', 'Assistant virtuel')