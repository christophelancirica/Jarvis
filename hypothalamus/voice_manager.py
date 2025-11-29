"""
Voice Manager - Gestion des voix TTS
VERSION CORRIGÉE ET COMPLÈTE
"""

import json
from pathlib import Path

import warnings
# Petit problème de futur incompatibilité. On va enlever le warning qui sert à rien (vu qu'on est en librairie fixe)
warnings.filterwarnings("ignore", category=UserWarning, module='jieba')

from TTS.api import TTS

# Ajoutez ces deux imports
import torch.serialization

class VoiceManager:
    def __init__(self):
        self.config_file = Path("config/voice_config.json")
        self.voices_json = Path("config/voices.json")
        self.config_file.parent.mkdir(exist_ok=True)
        
        # Charger toutes les voix depuis voices.json
        self.available_voices = self._load_all_voices()
        
    def _load_all_voices(self):
        """Charge les voix standard + clonées depuis voices.json"""
        voices = {}
        
        try:
            if self.voices_json.exists():
                with open(self.voices_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Voix standard (Edge-TTS + Coqui + gTTS)
                for voice_id, voice_data in data.get('voices', {}).items():
                    # On utilise l'ID réel (ex: "Jarvis", "GoogleFR") comme clé
                    key = voice_id
                    voices[key] = {
                        "name": voice_data.get('display_name', voice_data['name']),
                        "display_name": voice_data.get('display_name', voice_data['name']),
                        "model": voice_data['model'],
                        "voice": voice_data.get('edge_voice'),
                        "edge_voice": voice_data.get('edge_voice'),
                        "lang": voice_data.get('lang'), # Important pour gTTS
                        "personality": voice_data['name'], # Ou voice_id si name != id
                        "gender": voice_data.get('gender', 'unknown'),
                        "description": voice_data.get('description', ''),
                        "voice_id": voice_id,
                        "type": "standard"
                    }
                
                # Voix clonées (XTTS) - AVEC NORMALISATION DES CHEMINS
                for voice_id, voice_data in data.get('cloned_voices', {}).items():
                    if voice_data.get('processing_status') == 'ready':
                        key = voice_id
                        voices[key] = {
                            "name": voice_data.get('display_name', voice_data['name']),
                            "display_name": voice_data.get('display_name', voice_data['name']),
                            "model": "xtts-v2",
                            # ⚡ NORMALISATION des chemins en format Unix
                            "sample_path": Path(voice_data['sample_path']).as_posix(),
                            "embedding_path": Path(voice_data.get('embedding_path', '')).as_posix() if voice_data.get('embedding_path') else None,
                            "personality": voice_data['name'],
                            "gender": voice_data.get('gender', 'unknown'),
                            "description": voice_data.get('description', ''),
                            "voice_id": voice_id,
                            "type": "cloned"
                        }
            
            # Fallback si voices.json n'existe pas
            if not voices:
                voices = self._get_default_voices()
                
        except Exception as e:
            print(f"⚠️ Erreur chargement voices.json: {e}")
            voices = self._get_default_voices()
        
        return voices

    def _get_default_voices(self):
        """Voix par défaut si voices.json absent"""
        # On utilise des IDs stables
        return {
            "Jarvis": {
                "name": "Jarvis (Homme - Français)",
                "display_name": "Jarvis (Masculin - Russe)",
                "model": "tts_models/fr/css10/vits",
                "personality": "Jarvis",
                "voice_id": "Jarvis",
                "gender": "male",
                "description": "Voix masculine française, style assistant",
                "type": "standard"
            },
            "Samantha": {
                "name": "Samantha (Femme - Français)",
                "display_name": "Samantha (Féminin)",
                "model": "edge-tts",
                "voice": "fr-FR-DeniseNeural",
                "edge_voice": "fr-FR-DeniseNeural",
                "personality": "Samantha",
                "voice_id": "Samantha",
                "gender": "female",
                "description": "Voix féminine française, chaleureuse",
                "type": "standard"
            },
            "Eloise": {
                "name": "Eloise (jeune fille- Edge)",
                "display_name": "Eloise (Petite fille)",
                "model": "edge-tts",
                "edge_voice": "fr-FR-EloiseNeural", 
                "personality": "Eloise",
                "voice_id": "Eloise",
                "gender": "female", 
                "description": "Voix féminine jeune et dynamique"
            }
        }
    
    def load_saved_voice(self):
        """Charge la voix sauvegardée"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return (
                    config.get('voice_id'), 
                    config.get('personality'), 
                    config.get('model'), 
                    config.get('edge_voice'),
                    config.get('sample_path'),
                    config.get('embedding_path')  # AJOUT du embedding_path
                )
        return None, None, None, None, None, None
    
    def save_voice(self, voice_id, personality, model, edge_voice, sample_path=None, embedding_path=None):
        """Sauvegarde le choix de voix avec normalisation des chemins"""
        config = {
            'voice_id': voice_id,
            'personality': personality,
            'model': model,
            'edge_voice': edge_voice,
            # ⚡ NORMALISATION des chemins en format Unix
            'sample_path': Path(sample_path).as_posix() if sample_path else None,
            'embedding_path': Path(embedding_path).as_posix() if embedding_path else None
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"✅ Voix sauvegardée : {personality}")
    
    def get_current_personality(self):
        """Retourne la personnalité actuellement sauvegardée"""
        _, personality, _, _, _, _ = self.load_saved_voice()
        return personality or "Jarvis"
    
    def select_voice(self):
        """
        Sélection de la voix par l'utilisateur
        Retourne (personality, model, edge_voice, sample_path, embedding_path)
        """
        print("\n" + "="*60)
        print("🎤 CONFIGURATION VOIX")
        print("="*60)
        
        # Vérifier si une voix est déjà sauvegardée
        saved_id, saved_personality, saved_model, edge_voice, sample_path, embedding_path = self.load_saved_voice()
        
        if saved_id and saved_id in self.available_voices:
            voice_info = self.available_voices[saved_id]
            print(f"\n🔍 Voix sauvegardée : {voice_info['name']}")
            print(f"   Personnalité : {saved_personality}")
            
            choice = input("Utiliser cette voix ? (O/n) : ").strip().lower()
            if choice in ['', 'o', 'oui', 'y', 'yes']:
                # Retourner avec les paths des embeddings si disponibles
                return (saved_personality, saved_model, edge_voice, sample_path, embedding_path)
        
        # Afficher les voix disponibles
        print("\n🎙️  Voix disponibles :\n")
        for voice_id, info in self.available_voices.items():
            gender_icon = "👨" if info['gender'] == 'male' else "👩"
            type_icon = "🎭" if info['type'] == 'cloned' else "🎤"
            print(f"{voice_id}. {gender_icon} {type_icon} {info['name']}")
            print(f"   {info['description']}")
            if info.get('embedding_path'):
                print(f"   ⚡ Embeddings optimisés disponibles")
            print()
        
        # Choix utilisateur
        while True:
            try:
                choice = input(f"Choisis une voix (1-{len(self.available_voices)}) : ").strip()
                
                if choice in self.available_voices:
                    voice_info = self.available_voices[choice]
                    personality = voice_info['personality']
                    model = voice_info['model']
                    edge_voice = voice_info.get('edge_voice')
                    sample_path = voice_info.get('sample_path')
                    embedding_path = voice_info.get('embedding_path')
                    
                    print(f"\n✅ Voix sélectionnée : {voice_info['name']}")
                    print(f"   Personnalité : {personality}")
                    if embedding_path:
                        print(f"   ⚡ Avec embeddings optimisés")
                    print(f"   Téléchargement du modèle si nécessaire...")
                    
                    # Sauvegarder avec embedding_path
                    self.save_voice(choice, personality, model, edge_voice, sample_path, embedding_path)
                    
                    return personality, model, edge_voice, sample_path, embedding_path
                else:
                    print(f"❌ Choix invalide (1-{len(self.available_voices)})")
                    
            except (ValueError, KeyboardInterrupt):
                print("\n❌ Annulé")
                return None, None, None, None, None
    
    def get_voice_by_id(self, voice_id):
        """Retourne les infos d'une voix par son ID"""
        return self.available_voices.get(voice_id)
    
    def get_voice_by_personality(self, personality):
        """Retourne les infos d'une voix par sa personnalité"""
        for voice_id, voice_info in self.available_voices.items():
            if voice_info['personality'] == personality:
                return voice_info
        return None