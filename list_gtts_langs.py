
from gtts.lang import tts_langs

langs = tts_langs()
print("Available languages:")
for lang_code, lang_name in langs.items():
    print(f"{lang_code}: {lang_name}")

print("\nChecking for 'en' and 'es':")
print(f"'en' available: {'en' in langs}")
print(f"'es' available: {'es' in langs}")
