"""
Device Manager - Gestion des périphériques audio
Détecte et sauvegarde le meilleur microphone
"""

import pyaudio
import wave
import json
from pathlib import Path
import audioop

class DeviceManager:
    def __init__(self):
        self.config_file = Path("config/audio_device.json")
        self.config_file.parent.mkdir(exist_ok=True)
    
    def load_saved_device(self):
        """Charge le device sauvegardé"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('device_index'), config.get('device_name')
        return None, None
    
    def save_device(self, device_index, device_name):
        """Sauvegarde le device choisi"""
        config = {
            'device_index': device_index,
            'device_name': device_name
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"✅ Micro sauvegardé : {device_name} (index {device_index})")
    
    def get_available_devices(self):
        """Retourne une liste de tous les périphériques d'entrée audio disponibles."""
        devices = []
        p = pyaudio.PyAudio()
        try:
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info.get('maxInputChannels') > 0:
                    devices.append({
                        'index': i,
                        'name': info.get('name')
                    })
        finally:
            p.terminate()
        return devices

    def verify_device(self, device_index):
        """Vérifie qu'un device existe toujours"""
        try:
            p = pyaudio.PyAudio()
            info = p.get_device_info_by_index(device_index)
            p.terminate()
            
            if info['maxInputChannels'] > 0:
                return True, info['name']
            return False, None
        except:
            return False, None
    
    def test_device(self, device_index, device_name):
        """
        Teste un device en enregistrant 3 secondes
        Retourne (success, volume_max)
        """
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        DURATION = 3
        
        print(f"\n🎤 Test : {device_name}")
        print(f"   Parle FORT pendant 3 secondes...")
        
        p = pyaudio.PyAudio()
        
        try:
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=CHUNK
            )
            
            frames = []
            for i in range(0, int(RATE / CHUNK * DURATION)):
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            
            # Analyser le volume
            volumes = [audioop.rms(frame, 2) for frame in frames]
            volume_max = max(volumes)
            volume_avg = sum(volumes) / len(volumes)
            
            print(f"   📊 Volume max: {volume_max}, moyen: {volume_avg:.0f}")
            
            # Considérer comme fonctionnel si volume > 100
            if volume_max > 100:
                print(f"   ✅ FONCTIONNE (volume suffisant)")
                return True, volume_max
            else:
                print(f"   ⚠️  Trop silencieux")
                return False, volume_max
                
        except Exception as e:
            print(f"   ❌ Erreur: {e}")
            return False, 0
        finally:
            p.terminate()
    
    def find_best_microphone(self):
        """
        Scanne tous les devices et trouve le meilleur micro
        Retourne (device_index, device_name)
        """
        print("\n" + "="*60)
        print("🔍 Recherche du meilleur microphone...")
        print("="*60)
        
        p = pyaudio.PyAudio()
        
        # Lister tous les devices d'entrée
        input_devices = []
        for i in range(p.get_device_count()):
            try:
                info = p.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    input_devices.append((i, info['name']))
            except:
                pass
        
        p.terminate()
        
        if not input_devices:
            print("❌ Aucun microphone détecté !")
            return None, None
        
        print(f"\n📋 {len(input_devices)} microphone(s) détecté(s)")
        
        # Tester chaque device
        working_devices = []
        for device_index, device_name in input_devices:
            success, volume = self.test_device(device_index, device_name)
            if success:
                working_devices.append((device_index, device_name, volume))
        
        if not working_devices:
            print("\n❌ Aucun microphone ne fonctionne correctement !")
            print("Vérifiez :")
            print("  - Que le micro est branché")
            print("  - Les permissions Windows")
            print("  - Que vous parlez assez fort")
            return None, None
        
        # Si un seul fonctionne, le choisir automatiquement
        if len(working_devices) == 1:
            device_index, device_name, volume = working_devices[0]
            print(f"\n✅ Micro sélectionné automatiquement : {device_name}")
            return device_index, device_name
        
        # Si plusieurs fonctionnent, demander à l'utilisateur
        print(f"\n✅ {len(working_devices)} microphone(s) fonctionnel(s) :")
        for i, (idx, name, volume) in enumerate(working_devices, 1):
            print(f"   {i}. {name} (volume: {volume})")
        
        while True:
            try:
                choice = input(f"\nChoisis un micro (1-{len(working_devices)}) : ").strip()
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(working_devices):
                    device_index, device_name, _ = working_devices[choice_idx]
                    return device_index, device_name
                else:
                    print(f"❌ Choix invalide (1-{len(working_devices)})")
            except (ValueError, KeyboardInterrupt):
                print("\n❌ Annulé")
                return None, None
    
    def setup_microphone(self):
        """
        Configuration complète du microphone
        Retourne device_index ou None
        """
        print("\n🎙️  CONFIGURATION MICROPHONE")
        
        # Vérifier si un device est déjà sauvegardé
        saved_index, saved_name = self.load_saved_device()
        
        if saved_index is not None:
            print(f"\n📁 Micro sauvegardé : {saved_name} (index {saved_index})")
            
            # Vérifier qu'il existe toujours
            exists, current_name = self.verify_device(saved_index)
            
            if exists:
                print(f"✅ Le micro est toujours disponible")
                
                # Demander si on veut le garder ou refaire le test
                choice = input("Utiliser ce micro ? (O/n) : ").strip().lower()
                if choice in ['', 'o', 'oui', 'y', 'yes']:
                    return saved_index
            else:
                print(f"⚠️  Le micro n'est plus disponible !")
        
        # Rechercher un nouveau micro
        device_index, device_name = self.find_best_microphone()
        
        if device_index is not None:
            self.save_device(device_index, device_name)
            return device_index
        
        return None