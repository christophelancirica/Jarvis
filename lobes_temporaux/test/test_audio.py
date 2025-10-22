import pyaudio

p = pyaudio.PyAudio()

print("Devices disponibles :")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    print(f"{i}: {info['name']} (in={info['maxInputChannels']})")

p.terminate()