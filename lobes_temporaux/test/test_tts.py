import pyttsx3

engine = pyttsx3.init()

# Lister les voix
voices = engine.getProperty('voices')
print("Voix disponibles :")
for i, voice in enumerate(voices):
    print(f"{i}: {voice.name} - {voice.languages}")

# Test simple
engine.say("Bonjour, je suis Jarvis")
engine.runAndWait()