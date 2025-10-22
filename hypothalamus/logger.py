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

DEBUG_MODE = config['system']['log_level'] == 'DEBUG'

class JarvisLogger:
    """Logger avec niveaux DEBUG/INFO"""
    
    @staticmethod
    def debug(message, prefix="🔍"):
        """Affiche uniquement en mode DEBUG"""
        if DEBUG_MODE:
            print(f"{Fore.CYAN}{prefix} [DEBUG] {message}{Style.RESET_ALL}")
    
    @staticmethod
    def info(message, prefix="ℹ️"):
        """Affiche toujours"""
        print(f"{Fore.WHITE}{prefix} {message}{Style.RESET_ALL}")
    
    @staticmethod
    def success(message, prefix="✅"):
        """Message de succès"""
        print(f"{Fore.GREEN}{prefix} {message}{Style.RESET_ALL}")
    
    @staticmethod
    def warning(message, prefix="⚠️"):
        """Avertissement"""
        print(f"{Fore.YELLOW}{prefix} {message}{Style.RESET_ALL}")
    
    @staticmethod
    def error(message, prefix="❌"):
        """Erreur"""
        print(f"{Fore.RED}{prefix} {message}{Style.RESET_ALL}")
    
    @staticmethod
    def user(message):
        """Message utilisateur"""
        print(f"{Fore.BLUE}👤 Vous: {message}{Style.RESET_ALL}")
    
    @staticmethod
    def jarvis(message):
        """Message Jarvis"""
        print(f"{Fore.MAGENTA}🤖 Jarvis: {message}{Style.RESET_ALL}")
    
    @staticmethod
    def thinking(message):
        """Réflexion"""
        print(f"{Fore.CYAN}🧠 {message}{Style.RESET_ALL}")
    
    @staticmethod
    def separator():
        """Séparateur visuel"""
        print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

# Instance globale
log = JarvisLogger()