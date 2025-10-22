"""
Voice Manager - Gestion des voix TTS
Permet de choisir la voix et la personnalité associée
"""

import json
from pathlib import Path
from TTS.api import TTS

class VoiceManager:
    def __init__(self):
        self.config_file = Path("config/voice_config.json")
        self.config_file.parent.mkdir(exist_ok=True)
        
        # Voix disponibles avec métadonnées
        self.available_voices = {
            "1": {
                "name": "Jarvis (Homme - Français)",
                "model": "tts_models/fr/css10/vits",
                "personality": "Jarvis",
                "gender": "male",
                "description": "Voix masculine française, style assistant"
            },
            "2": {
                "name": "Samantha (Femme - Français)",
                "model": "tts_models/multilingual/multi-dataset/xtts_v2",
                "personality": "Samantha",
                "gender": "female",
                "description": "Voix féminine française, chaleureuse"
            }
        }
    
    def load_saved_voice(self):
        """Charge la voix sauvegardée"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('voice_id'), config.get('personality'), config.get('model')
        return None, None, None
    
    def save_voice(self, voice_id, personality, model):
        """Sauvegarde le choix de voix"""
        config = {
            'voice_id': voice_id,
            'personality': personality,
            'model': model
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"✅ Voix sauvegardée : {personality}")
    
    def select_voice(self):
        """
        Sélection de la voix par l'utilisateur
        Retourne (personality, model)
        """
        print("\n" + "="*60)
        print("🎤 CONFIGURATION VOIX")
        print("="*60)
        
        # Vérifier si une voix est déjà sauvegardée
        saved_id, saved_personality, saved_model = self.load_saved_voice()
        
        if saved_id and saved_id in self.available_voices:
            voice_info = self.available_voices[saved_id]
            print(f"\n📁 Voix sauvegardée : {voice_info['name']}")
            print(f"   Personnalité : {saved_personality}")
            
            choice = input("Utiliser cette voix ? (O/n) : ").strip().lower()
            if choice in ['', 'o', 'oui', 'y', 'yes']:
                return saved_personality, saved_model
        
        # Afficher les voix disponibles
        print("\n🎙️  Voix disponibles :\n")
        for voice_id, info in self.available_voices.items():
            gender_icon = "👨" if info['gender'] == 'male' else "👩"
            print(f"{voice_id}. {gender_icon} {info['name']}")
            print(f"   {info['description']}")
            print()
        
        # Choix utilisateur
        while True:
            try:
                choice = input(f"Choisis une voix (1-{len(self.available_voices)}) : ").strip()
                
                if choice in self.available_voices:
                    voice_info = self.available_voices[choice]
                    personality = voice_info['personality']
                    model = voice_info['model']
                    
                    print(f"\n✅ Voix sélectionnée : {voice_info['name']}")
                    print(f"   Personnalité : {personality}")
                    print(f"   Téléchargement du modèle si nécessaire...")
                    
                    # Sauvegarder
                    self.save_voice(choice, personality, model)
                    
                    return personality, model
                else:
                    print(f"❌ Choix invalide (1-{len(self.available_voices)})")
                    
            except (ValueError, KeyboardInterrupt):
                print("\n❌ Annulé")
                return None, None