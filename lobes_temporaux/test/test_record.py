import pyaudio
import wave
from pathlib import Path

def test_device(device_index):
    """Test un device spécifique"""
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    DURATION = 3
    
    audio_path = Path(f"test_device_{device_index}.wav")
    
    p = pyaudio.PyAudio()
    
    # Info du device
    try:
        info = p.get_device_info_by_index(device_index)
        print(f"\n{'='*60}")
        print(f"Test Device {device_index}: {info['name']}")
        print(f"Max Input Channels: {info['maxInputChannels']}")
        
        if info['maxInputChannels'] == 0:
            print("❌ Pas un device d'entrée, skip")
            p.terminate()
            return False
        
        # Enregistrement
        print(f"🎙️  Enregistrement 3 secondes...")
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
        
        # Sauvegarder
        wf = wave.open(str(audio_path), 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        size = audio_path.stat().st_size
        print(f"✅ Fichier créé: {audio_path.name} ({size} bytes)")
        
        # Analyser le volume
        import audioop
        volume = max([audioop.rms(frame, 2) for frame in frames])
        print(f"📊 Volume max détecté: {volume}")
        
        if volume > 100:
            print(f"✅✅✅ MICRO FONCTIONNE ! Volume = {volume}")
            return True
        else:
            print(f"⚠️  Micro silencieux (volume = {volume})")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    finally:
        p.terminate()

# Tester les devices probables
print("Test des microphones...")
print("Parle FORT pendant chaque test de 3 secondes !")

# Devices à tester (ceux avec 'Microphone' dans le nom)
devices_to_test = [1, 2, 3, 8, 9, 16, 17, 20, 23, 28]

working_devices = []
for device_id in devices_to_test:
    if test_device(device_id):
        working_devices.append(device_id)

print(f"\n{'='*60}")
print(f"✅ Micros qui FONCTIONNENT: {working_devices}")
print(f"\n👉 Utilise un de ces numéros dans ton config !")