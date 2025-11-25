"""
Système de logs pour Jarvis
"""

from colorama import Fore, Style
import yaml
from pathlib import Path

# Charger config
config_path = Path("config/settings.yaml")
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

LOG_LEVEL = config['system'].get('log_level', 'STANDARD').upper()
LEVELS = {"STANDARD": 0, "INFO": 1, "DEBUG": 2}

class JarvisLogger:
    """Logger avec niveaux DEBUG/INFO/STANDARD"""
    
    @staticmethod
    def debug(message, prefix="🔍"):
        """Affiche uniquement en mode DEBUG"""
        if LEVELS.get(LOG_LEVEL, 0) >= LEVELS["DEBUG"]:
            print(f"{Fore.CYAN}{prefix} [DEBUG] {message}{Style.RESET_ALL}")
    
    @staticmethod
    def info(message, prefix="ℹ️"):
        """Affiche si niveau >= STANDARD pour les information de base"""
        if LEVELS.get(LOG_LEVEL, 0) >= LEVELS["STANDARD"]:
            print(f"{Fore.WHITE}{prefix} {message}{Style.RESET_ALL}")
    
    @staticmethod
    def success(message, prefix="✅"):
        """Message de succès"""
        if LEVELS.get(LOG_LEVEL, 0) >= LEVELS["INFO"]:
            print(f"{Fore.GREEN}{prefix} {message}{Style.RESET_ALL}")
    
    @staticmethod
    def warning(message, prefix="⚠️"):
        """Avertissement"""
        if LEVELS.get(LOG_LEVEL, 0) >= LEVELS["INFO"]:
            print(f"{Fore.YELLOW}{prefix} {message}{Style.RESET_ALL}")
    
    @staticmethod
    def error(message, prefix="❌"):
        """Erreur"""
        # Toujours afficher les erreurs, même en mode STANDARD
        print(f"{Fore.RED}{prefix} {message}{Style.RESET_ALL}")
    
    @staticmethod
    def user(message):
        """Message utilisateur"""
        if LEVELS.get(LOG_LEVEL, 0) >= LEVELS["STANDARD"]:
            print(f"{Fore.BLUE}👤 Vous: {message}{Style.RESET_ALL}")
    
    @staticmethod
    def jarvis(message):
        """Message Jarvis"""
        if LEVELS.get(LOG_LEVEL, 0) >= LEVELS["STANDARD"]:
            print(f"{Fore.MAGENTA}🤖 Jarvis: {message}{Style.RESET_ALL}")
    
    @staticmethod
    def thinking(message):
        """Réflexion"""
        if LEVELS.get(LOG_LEVEL, 0) >= LEVELS["DEBUG"]:
            print(f"{Fore.CYAN}🧠 {message}{Style.RESET_ALL}")
    
    @staticmethod
    def separator():
        """Séparateur visuel"""
        if LEVELS.get(LOG_LEVEL, 0) >= LEVELS["DEBUG"]:
            print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

# Instance globale
log = JarvisLogger()
