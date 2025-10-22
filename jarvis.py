"""
Jarvis - Assistant Vocal
Point d'entrée principal
"""

import time
import yaml
from pathlib import Path
from colorama import init

from cortex_prefrontal.llm_client import JarvisLLM
from lobes_temporaux.stt import SpeechToText
from lobes_temporaux.tts import TextToSpeech
from hypothalamus.device_manager import DeviceManager
from hypothalamus.logger import log

# Initialiser colorama
init()

# Charger config globale
config_path = Path("config/settings.yaml")
with open(config_path, 'r', encoding='utf-8') as f:
    GLOBAL_CONFIG = yaml.safe_load(f)

DEBUG_MODE = GLOBAL_CONFIG['system']['log_level'] == 'DEBUG'

def print_banner():
    from colorama import Fore, Style
    print(f"""{Fore.CYAN}
╔═══════════════════════════════════╗
║         🤖 JARVIS v0.1            ║
║    Assistant Vocal Intelligent    ║
╚═══════════════════════════════════╝
{Style.RESET_ALL}""")
    
    if DEBUG_MODE:
        log.warning("MODE DEBUG ACTIVÉ", "🔍")

def main():
    print_banner()
    
    # ÉTAPE 1 : Configuration microphone
    device_mgr = DeviceManager()
    device_index = device_mgr.setup_microphone()
    
    if device_index is None:
        log.error("Impossible de configurer un microphone")
        log.info("Jarvis ne peut pas démarrer sans micro.")
        return
    
    # ÉTAPE 2 : Configuration voix
    from hypothalamus.voice_manager import VoiceManager
    voice_mgr = VoiceManager()
    personality, tts_model = voice_mgr.select_voice()
    
    if personality is None:
        log.error("Impossible de configurer la voix")
        return
    
    # ÉTAPE 3 : Initialisation modules avec personnalité
    log.info("Initialisation des modules...")
    
    llm = JarvisLLM(personality=personality)  # ← Passe la personnalité
    stt = SpeechToText(device_index=device_index)
    tts = TextToSpeech(model_name=tts_model, personality=personality)  # ← Passe modèle + personnalité
    
    log.success("Tous les modules sont prêts !")
    print()
    
    # Salutation adaptée
    if personality == "Jarvis":
        greeting = "Bonjour, je suis Jarvis. Mes systèmes sont opérationnels. Comment puis-je vous assister ?"
    else:  # Samantha
        greeting = "Bonjour, je suis Samantha. Je suis heureuse de vous parler aujourd'hui. Comment puis-je vous aider ?"
    
    tts.speak(greeting)
    
    # Boucle principale
    while True:
        try:
            log.separator()
            log.info("Prêt à écouter (Ctrl+C pour quitter)")
            
            # Écoute avec VAD (détection automatique)
            user_input = stt.listen_with_vad(timeout=30, silence_duration=1.5)
            
            if not user_input:
                log.warning("Rien détecté, micro toujours actif...")
                continue
            
            log.user(user_input)
            
            # Analyse complexité
            log.thinking("Analyse de la complexité...")
            start_time = time.time()
            
            analysis = llm.analyze_complexity(user_input)
            complexity = analysis['complexity']
            
            elapsed = time.time() - start_time
            log.success(f"Complexité: {complexity} ({elapsed:.2f}s)", "📊")
            
            if DEBUG_MODE:
                log.debug(f"Analyse LLM: {analysis['analyse']}", "💭")
            
            # Réponse
            response = analysis['reponse']
            
            if complexity == "Expert":
                log.thinking("Traitement Expert...", "🔬")
                response = llm.generate_response(user_input, "Expert")
            
            # Parler
            tts.speak(response)
            
        except KeyboardInterrupt:
            log.warning("Interruption détectée")
            tts.speak("Au revoir !")
            break
        except Exception as e:
            log.error(f"Erreur: {e}")
            if DEBUG_MODE:
                import traceback
                log.debug(traceback.format_exc())
            tts.speak("Désolé, j'ai rencontré un problème")

if __name__ == "__main__":
    main()