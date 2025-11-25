"""
voice_cloner.py - Gestionnaire pur de clonage vocal
REFACTORISÉ: Ne fait plus que du clonage, pas de génération audio
"""

import os
import json
import time
import base64
import shutil
import hashlib
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

# Audio processing
import numpy as np
import wave

# Import logger
import sys
sys.path.append(str(Path(__file__).parent.parent))

try:
    from hypothalamus.logger import log
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    log = logging.getLogger(__name__)


class VoiceCloner:
    """
    Gestionnaire pur de clonage vocal avec intégration voices.json
    RESPONSABILITÉ UNIQUE: Cloner, gérer et configurer les voix
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialise le gestionnaire de clonage vocal"""
        
        # Chemins de configuration
        self.config_dir = Path(__file__).parent.parent / "config"
        self.voices_json_path = self.config_dir / "voices.json"
        self.cloned_voices_dir = self.config_dir / "cloned_voices"
        self.cloned_voices_dir.mkdir(exist_ok=True, parents=True)
        
        # Créer les sous-dossiers
        self.samples_dir = self.cloned_voices_dir / "samples"
        self.models_dir = self.cloned_voices_dir / "models"
        self.samples_dir.mkdir(exist_ok=True)
        self.models_dir.mkdir(exist_ok=True)
        
        # Charger la configuration voices.json
        self.voices_config = self.load_voices_config()
        
        # État XTTS pour calcul embeddings
        self.xtts_model = None
        self.xtts_loaded = False
        self.is_processing = False
        
        log.info(f"VoiceCloner initialisé - {self.count_cloned_voices()} voix clonées")
    
    # ========================================================================
    # GESTION CONFIGURATION VOICES.JSON
    # ========================================================================
    
    def load_voices_config(self) -> Dict[str, Any]:
        """Charge le fichier voices.json"""
        try:
            with open(self.voices_json_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Ajouter sections manquantes
            if 'cloned_voices' not in config:
                config['cloned_voices'] = {}
            if 'voices' not in config:
                config['voices'] = {}
            if 'default_voice' not in config:
                config['default_voice'] = 'jarvis'
            
            return config
        except Exception as e:
            log.error(f"Erreur chargement voices.json: {e}")
            return {
                "voices": {},
                "cloned_voices": {},
                "default_voice": "jarvis",
                "demo_text": "Test de voix clonée"
            }
    
    def save_voices_config(self):
        """Sauvegarde voices.json avec les voix clonées"""
        try:
            with open(self.voices_json_path, 'w', encoding='utf-8') as f:
                json.dump(self.voices_config, f, indent=2, ensure_ascii=False)
            log.debug("Configuration voices.json sauvegardée")
        except Exception as e:
            log.error(f"Erreur sauvegarde voices.json: {e}")
    
    def get_voice_config(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère la configuration complète d'une voix
        
        Args:
            voice_id: ID de la voix (personnalité ou ID technique)
            
        Returns:
            Configuration voix compatible AudioGenerator ou None
        """
        # Chercher dans les voix standards
        for vid, voice_data in self.voices_config.get('voices', {}).items():
            if vid == voice_id or voice_data.get('name') == voice_id:
                return {
                    'model': voice_data.get('model', 'edge-tts'),
                    'edge_voice': voice_data.get('edge_voice'),
                    'personality_config': voice_data.get('personality_config', {
                        'voice_speed': 1.0,
                        'voice_volume': 90
                    })
                }
        
        # Chercher dans les voix clonées
        for vid, voice_data in self.voices_config.get('cloned_voices', {}).items():
            if vid == voice_id or voice_data.get('name') == voice_id:
                config = {
                    'model': 'xtts-v2',
                    'sample_path': voice_data.get('sample_path'),
                    'personality_config': voice_data.get('personality_config', {
                        'voice_speed': 1.0
                    })
                }
                
                # ✅ CORRECTION: Utiliser embedding_path de la config si présent
                if 'embedding_path' in voice_data:
                    config['embedding_path'] = voice_data['embedding_path']
                else:
                    # Fallback: calcul dynamique pour compatibilité
                    config['embedding_path'] = self._get_embedding_path(voice_data.get('sample_path'))
                
                return config
        
        log.warning(f"Voix non trouvée: {voice_id}")
        return None
    
    def _get_embedding_path(self, sample_path: str) -> Optional[str]:
        """Retourne le chemin vers l'embedding pré-calculé si il existe"""
        if not sample_path:
            return None
        
        sample_path = Path(sample_path)
        if not sample_path.is_absolute():
            sample_path = self.config_dir / sample_path
        
        embedding_path = sample_path.with_suffix('.pt')
        return str(embedding_path) if embedding_path.exists() else None
    
    def get_all_voices(self) -> Dict[str, Any]:
        """Retourne toutes les voix (standard + clonées) dans un format unifié"""
        return {
            'success': True, 
            'voices': self.voices_config.get('voices', {}),
            'cloned_voices': self.voices_config.get('cloned_voices', {}),
            'default_voice': self.voices_config.get('default_voice', 'jarvis')
        }
    
    def list_cloned_voices(self) -> List[Dict[str, Any]]:
        """Retourne la liste des voix clonées avec métadonnées"""
        voices_list = []
        
        for voice_id, voice in self.voices_config.get('cloned_voices', {}).items():
            voices_list.append({
                'id': voice_id,
                'name': voice['name'],
                'display_name': voice['display_name'],
                'description': voice['description'],
                'duration': voice.get('duration', 0),
                'status': voice.get('processing_status', 'unknown'),
                'created_at': voice.get('created_at'),
                'model': voice.get('model', 'xtts-v2'),
                'sample_path': voice.get('sample_path'),
                'has_embedding': self._get_embedding_path(voice.get('sample_path')) is not None
            })
        
        # Trier par date de création
        voices_list.sort(key=lambda x: x.get('created_at', 0), reverse=True)
        
        return voices_list
    
    def count_cloned_voices(self) -> int:
        """Compte le nombre de voix clonées"""
        return len(self.voices_config.get('cloned_voices', {}))
    
    def set_default_voice(self, voice_id: str) -> Dict[str, Any]:
        """Définit une voix comme voix par défaut"""
        # Vérifier que la voix existe
        all_voices = {
            **self.voices_config.get('voices', {}),
            **self.voices_config.get('cloned_voices', {})
        }
        
        if voice_id not in all_voices:
            return {'success': False, 'error': 'Voix non trouvée'}
        
        self.voices_config['default_voice'] = voice_id
        self.save_voices_config()
        
        voice_name = all_voices[voice_id]['name']
        log.info(f"Voix par défaut: {voice_name}")
        
        return {
            'success': True,
            'voice_id': voice_id,
            'voice_name': voice_name
        }
    
    # ========================================================================
    # CLONAGE VOCAL
    # ========================================================================
    
    async def clone_voice(
        self,
        audio_data: bytes,
        voice_name: str,
        description: str = "",
        file_type: str = 'audio'
    ) -> Dict[str, Any]:
        """
        Clone une voix et l'ajoute à voices.json
        
        Args:
            audio_data: Données audio WAV/MP4/etc.
            voice_name: Nom de la voix
            description: Description optionnelle
            file_type: 'audio' ou 'video'
            
        Returns:
            Résultat du clonage avec voice_id
        """
        if self.is_processing:
            return {'success': False, 'error': 'Traitement en cours, veuillez patienter'}
        
        self.is_processing = True
        
        try:
            # Valider l'audio
            validation = self.validate_audio_file(audio_data, file_type)
            
            if not validation['valid']:
                return {'success': False, 'error': validation['error']}
            
            # Générer un ID unique
            voice_id = f"cloned_{hashlib.md5(f'{voice_name}_{time.time()}'.encode()).hexdigest()[:8]}"
            
            # Sauvegarder l'échantillon WAV
            sample_path = self.samples_dir / f"{voice_id}.wav"
            with open(sample_path, 'wb') as f:
                f.write(validation['wav_data'])
            
            log.info(f"Échantillon sauvegardé: {sample_path.name}")
            
            # Créer l'entrée dans voices.json
            voice_entry = {
                "id": voice_id,
                "name": voice_name,
                "display_name": f"🎭 {voice_name}",
                "gender": "unknown",
                "model": "xtts-v2",
                "sample_path": str(sample_path.relative_to(self.config_dir)),
                "description": description or f"Voix clonée le {time.strftime('%d/%m/%Y')}",
                "voice_type": "cloned",
                "duration": validation['duration'],
                "sample_rate": validation['sample_rate'],
                "created_at": time.time(),
                "personality_config": {
                    "voice_speed": 1.0,
                    "voice_volume": 90
                },
                "processing_status": "pending"
            }
            
            # Ajouter à la configuration
            self.voices_config['cloned_voices'][voice_id] = voice_entry
            self.save_voices_config()
            log.debug(f"🔍 [TRACE] Voix créée - ID: {voice_id}, Name: {voice_name}")
            
            # Traiter l'embedding si XTTS est disponible
            if await self.initialize_xtts():
                success = await self._process_voice_embedding(voice_id, sample_path)
                if success:
                    voice_entry['processing_status'] = 'ready'
                    # ✅ CORRECTION CLEF: Ajouter embedding_path à la config
                    embedding_path = sample_path.with_suffix('.pt')
                    voice_entry['embedding_path'] = str(embedding_path.relative_to(self.config_dir))
                else:
                    voice_entry['processing_status'] = 'failed'
                self.save_voices_config()
            else:
                voice_entry['processing_status'] = 'no_model'
                log.warning("XTTS non disponible, voix sauvegardée sans embedding")
            
            log.success(f"Voix '{voice_name}' clonée avec succès (ID: {voice_id})")
            
            return {
                'success': True,
                'voice_id': voice_id,
                'voice_name': voice_name,
                'duration': validation['duration'],
                'status': voice_entry['processing_status']
            }
            
        except Exception as e:
            log.error(f"Erreur clonage: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            self.is_processing = False
    
    def validate_audio_file(self, audio_data: bytes, file_type: str = 'audio') -> Dict[str, Any]:
        """
        Valide un fichier audio pour le clonage
        
        Args:
            audio_data: Données binaires du fichier
            file_type: Type de fichier ('audio' ou 'video')
            
        Returns:
            Dictionnaire avec 'valid', 'error', 'wav_data', 'duration', 'sample_rate'
        """
        try:
            # Écrire dans un fichier temporaire pour traitement
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as temp_file:
                temp_file.write(audio_data)
                temp_input_path = temp_file.name
            
            # Fichier de sortie WAV
            temp_output_path = temp_input_path.replace('.tmp', '.wav')
            
            try:
                # Conversion avec ffmpeg
                cmd = [
                    'ffmpeg', '-y', '-i', temp_input_path,
                    '-ar', '22050',  # Fréquence d'échantillonnage pour XTTS
                    '-ac', '1',      # Mono
                    '-f', 'wav',
                    temp_output_path
                ]
                
                # Exécuter ffmpeg silencieusement
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    return {
                        'valid': False,
                        'error': f"Conversion ffmpeg échouée: {result.stderr[:100]}"
                    }
                
                log.debug("Conversion réussie: audio → WAV")
                
                # Lire le fichier converti
                with open(temp_output_path, 'rb') as f:
                    wav_data = f.read()
                
                # Analyser la durée avec wave
                with wave.open(temp_output_path, 'rb') as wav_file:
                    frames = wav_file.getnframes()
                    sample_rate = wav_file.getframerate()
                    duration = frames / float(sample_rate)
                
                # Validation durée
                if duration < 5.0:
                    return {
                        'valid': False,
                        'error': f"Échantillon trop court: {duration:.1f}s (min 5s requis)"
                    }
                
                if duration > 60.0:
                    return {
                        'valid': False,
                        'error': f"Échantillon trop long: {duration:.1f}s (max 60s)"
                    }
                
                return {
                    'valid': True,
                    'wav_data': wav_data,
                    'duration': duration,
                    'sample_rate': sample_rate
                }
                
            finally:
                # Nettoyer les fichiers temporaires
                try:
                    os.remove(temp_input_path)
                except:
                    pass
                try:
                    os.remove(temp_output_path)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            return {'valid': False, 'error': 'Timeout conversion audio'}
        except Exception as e:
            return {'valid': False, 'error': f"Erreur validation: {str(e)}"}
    
    # ========================================================================
    # GESTION EMBEDDINGS XTTS
    # ========================================================================
    
    async def initialize_xtts(self) -> bool:
        """Initialise XTTS pour calcul des embeddings"""
        if self.xtts_loaded:
            return True
        
        try:
            # Réduire verbosité
            import logging
            logging.getLogger('TTS').setLevel(logging.ERROR)
            
            from TTS.api import TTS
            import torch
            
            # Charger le modèle XTTS
            self.xtts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
            
            log.info("XTTS initialisé pour embeddings")
            self.xtts_loaded = True
            return True
            
        except ImportError:
            log.warning("TTS non installé - Embeddings non disponibles")
            return False
        except Exception as e:
            log.error(f"Erreur initialisation XTTS: {e}")
            return False
    
    async def _process_voice_embedding(self, voice_id: str, sample_path: Path) -> bool:
        """
        Calcule et sauvegarde l'embedding vocal pour utilisation rapide
        OPTIMISATION: Évite de recalculer lors de chaque génération
        """
        try:
            if not self.xtts_loaded:
                log.warning("XTTS non chargé, embedding non calculé")
                return False
            
            log.info(f"Calcul embedding pour {voice_id}...")
            
            # Calculer les embeddings avec XTTS
            conditioning_latents = self.xtts_model.synthesizer.tts_model.get_conditioning_latents(
                audio_path=str(sample_path)
            )
            
            # Sauvegarder l'embedding dans un fichier .pt
            import torch
            embedding_path = sample_path.with_suffix('.pt')
            
            torch.save({
                'gpt_cond_latent': conditioning_latents[0],
                'speaker_embedding': conditioning_latents[1],
                'voice_id': voice_id,
                'created_at': time.time()
            }, str(embedding_path))
            
            log.success(f"Embedding sauvegardé : {embedding_path.name}")
            log.info("⚡ Les prochaines générations seront 2-3x plus rapides")
            return True
            
        except Exception as e:
            log.error(f"Erreur calcul embedding: {e}")
            import traceback
            log.debug(traceback.format_exc())
            return False
    
    def has_embedding(self, voice_id: str) -> bool:
        """Vérifie si une voix a un embedding pré-calculé"""
        voice_data = self.voices_config.get('cloned_voices', {}).get(voice_id)
        if not voice_data:
            return False
        
        sample_path = voice_data.get('sample_path')
        if not sample_path:
            return False
        
        return self._get_embedding_path(sample_path) is not None
    
    async def recalculate_embedding(self, voice_id: str) -> Dict[str, Any]:
        """Recalcule l'embedding d'une voix existante"""
        voice_data = self.voices_config.get('cloned_voices', {}).get(voice_id)
        if not voice_data:
            return {'success': False, 'error': 'Voix non trouvée'}
        
        sample_path = self.config_dir / voice_data['sample_path']
        if not sample_path.exists():
            return {'success': False, 'error': 'Fichier échantillon manquant'}
        
        if not await self.initialize_xtts():
            return {'success': False, 'error': 'XTTS non disponible'}
        
        success = await self._process_voice_embedding(voice_id, sample_path)
        
        if success:
            voice_data['processing_status'] = 'ready'
            # ✅ CORRECTION: Ajouter embedding_path après recalcul aussi
            embedding_path = sample_path.with_suffix('.pt')
            voice_data['embedding_path'] = str(embedding_path.relative_to(self.config_dir))
            self.save_voices_config()
            return {'success': True, 'message': 'Embedding recalculé'}
        else:
            return {'success': False, 'error': 'Calcul embedding échoué'}
    
    # ========================================================================
    # GESTION VOIX
    # ========================================================================
    
    def rename_voice(self, voice_id: str, new_name: str, new_description: str = None) -> Dict[str, Any]:
        """Renomme une voix clonée"""
        if voice_id not in self.voices_config.get('cloned_voices', {}):
            return {'success': False, 'error': 'Voix non trouvée'}
        
        try:
            voice = self.voices_config['cloned_voices'][voice_id]
            voice['name'] = new_name
            voice['display_name'] = f"🎭 {new_name}"
            
            if new_description:
                voice['description'] = new_description
            
            self.save_voices_config()
            
            log.info(f"Voix {voice_id} renommée en '{new_name}'")
            return {'success': True, 'message': f"Voix renommée en '{new_name}'"}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def delete_voice(self, voice_id: str) -> Dict[str, Any]:
        """Supprime une voix clonée"""
        if voice_id not in self.voices_config.get('cloned_voices', {}):
            return {'success': False, 'error': 'Voix non trouvée'}
        
        try:
            voice = self.voices_config['cloned_voices'][voice_id]
            voice_name = voice['name']
            
            # Supprimer les fichiers
            sample_path = self.config_dir / voice['sample_path']
            if sample_path.exists():
                os.remove(sample_path)
                log.debug(f"Échantillon supprimé: {sample_path}")
            
            # Supprimer embedding si il existe
            embedding_path = sample_path.with_suffix('.pt')
            if embedding_path.exists():
                os.remove(embedding_path)
                log.debug(f"Embedding supprimé: {embedding_path}")
            
            # Supprimer de la configuration
            del self.voices_config['cloned_voices'][voice_id]
            
            # Changer voix par défaut si nécessaire
            if self.voices_config.get('default_voice') == voice_id:
                self.voices_config['default_voice'] = 'jarvis'
            
            self.save_voices_config()
            
            log.info(f"Voix '{voice_name}' supprimée")
            return {'success': True, 'message': f"Voix '{voice_name}' supprimée"}
            
        except Exception as e:
            log.error(f"Erreur suppression voix: {e}")
            return {'success': False, 'error': str(e)}
    
    # ========================================================================
    # IMPORT/EXPORT
    # ========================================================================
    
    def export_voice(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """Exporte une voix clonée pour sauvegarde/partage"""
        if voice_id not in self.voices_config.get('cloned_voices', {}):
            return None
        
        try:
            voice = self.voices_config['cloned_voices'][voice_id].copy()
            
            # Inclure l'audio en base64
            sample_path = self.config_dir / voice['sample_path']
            if sample_path.exists():
                with open(sample_path, 'rb') as f:
                    voice['audio_base64'] = base64.b64encode(f.read()).decode()
            
            # Métadonnées d'export
            voice['export_date'] = time.time()
            voice['export_version'] = '1.0'
            
            return voice
            
        except Exception as e:
            log.error(f"Erreur export: {e}")
            return None
    
    async def import_voice(self, voice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Importe une voix exportée"""
        try:
            if 'audio_base64' not in voice_data:
                return {'success': False, 'error': 'Données audio manquantes'}
            
            # Décoder l'audio
            audio_data = base64.b64decode(voice_data['audio_base64'])
            
            # Recréer la voix
            result = await self.clone_voice(
                audio_data=audio_data,
                voice_name=voice_data.get('name', 'Voix importée'),
                description=voice_data.get('description', 'Importée') + f" (import {time.strftime('%d/%m/%Y')})"
            )
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ========================================================================
    # STATUT
    # ========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Retourne le statut complet du module"""
        return {
            'xtts_loaded': self.xtts_loaded,
            'is_processing': self.is_processing,
            'total_voices': len(self.get_all_voices()['voices']) + len(self.get_all_voices()['cloned_voices']),
            'cloned_voices': self.count_cloned_voices(),
            'storage_used': self._calculate_storage(),
            'default_voice': self.voices_config.get('default_voice', 'jarvis'),
            'voices_with_embeddings': sum(1 for voice in self.list_cloned_voices() if voice['has_embedding'])
        }
    
    def _calculate_storage(self) -> str:
        """Calcule l'espace utilisé par les voix clonées"""
        try:
            total_size = 0
            
            if self.cloned_voices_dir.exists():
                for file_path in self.cloned_voices_dir.rglob('*'):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
            
            # Convertir en unités lisibles
            if total_size < 1024 * 1024:
                return f"{total_size / 1024:.1f} KB"
            else:
                return f"{total_size / (1024 * 1024):.1f} MB"
                
        except Exception:
            return "Inconnu"
    
    def cleanup(self):
        """Nettoie les ressources"""
        log.debug("Nettoyage VoiceCloner...")
        
        if self.xtts_model:
            del self.xtts_model
            self.xtts_model = None
            self.xtts_loaded = False
        
        log.debug("VoiceCloner nettoyé")


# ============================================================================
# EXEMPLE D'UTILISATION
# ============================================================================

async def example_usage():
    """Exemple d'utilisation du VoiceCloner"""
    
    cloner = VoiceCloner()
    
    # Lister les voix existantes
    voices = cloner.list_cloned_voices()
    print(f"Voix clonées existantes: {len(voices)}")
    
    # Obtenir la config d'une voix pour AudioGenerator
    if voices:
        voice_id = voices[0]['id']
        config = cloner.get_voice_config(voice_id)
        print(f"Config pour {voice_id}: {config}")
    
    # Statut
    status = cloner.get_status()
    print(f"Statut: {status}")


if __name__ == "__main__":
    print("🎭 VoiceCloner - Gestionnaire pur de clonage vocal")
    
    # Test de base
    cloner = VoiceCloner()
    print(f"Initialisation: {cloner.count_cloned_voices()} voix clonées")
    
    # Test config récupération
    config = cloner.get_voice_config('jarvis')
    print(f"Config voix 'jarvis': {config}")
    
    # asyncio.run(example_usage())