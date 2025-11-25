"""
model_manager.py - Gestionnaire des modèles LLM avec Ollama
Responsabilité : Installation, changement, et vérification des modèles
Adapté pour l'architecture plate de Jarvis
"""

import ollama
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Callable
from hypothalamus.logger import log


class ModelManager:
    """Gestionnaire des modèles LLM pour Ollama"""
    
    def __init__(self, models_config_path: str = "models.json"):
        self.config_path = Path(__file__).parent.parent / "config/models.json"
        self.current_model = None
        self.download_callbacks = {}  # Pour les callbacks de progression
        
    def load_available_models(self) -> Dict:
        """Charge la liste des modèles disponibles depuis la config"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Erreur chargement config modèles: {e}")
            return {"llm_models": {}, "config": {"default_model": "llama3.1:8b"}}
    
    def get_installed_models(self) -> List[str]:
        """Récupère la liste des modèles installés dans Ollama"""
        try:
            models = ollama.list()
            result = []
            for model in models.get('models', []):
                # Essayer plusieurs champs possibles
                model_name = model.get('name') or model.get('model') or str(model)
                if model_name:
                    result.append(model_name)
            return result
        except Exception as e:
            log.error(f"Erreur récupération modèles installés: {e}")
            return []
    
    def get_model_status(self) -> Dict:
        """Retourne le statut de tous les modèles (installé/non installé)"""
        config = self.load_available_models()
        installed = self.get_installed_models()
        
        # Si pas de modèle actuel défini, prendre celui par défaut s'il est installé
        if not self.current_model and installed:
            default_model = config.get('config', {}).get('default_model')
            if default_model and default_model in installed:
                self.current_model = default_model
        
        status = {}
        for model_id, model_info in config['llm_models'].items():
            status[model_id] = {
                **model_info,
                'installed': model_id in installed,
                'current': model_id == self.current_model
            }
        
        return {
            'models': status,
            'current_model': self.current_model,
            'installed_count': len(installed)
        }
    
    def is_model_available(self, model_id: str) -> bool:
        """Vérifie si un modèle est installé dans Ollama"""
        installed = self.get_installed_models()
        return model_id in installed
    
    async def download_model(self, model_id: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        Télécharge un modèle avec Ollama (asynchrone)
        
        Args:
            model_id: ID du modèle à télécharger
            progress_callback: Fonction appelée pour les updates de progression
        
        Returns:
            bool: Succès du téléchargement
        """
        try:
            config = self.load_available_models()
            if model_id not in config['llm_models']:
                log.error(f"Modèle {model_id} non trouvé dans la config")
                return False
            
            install_command = config['llm_models'][model_id].get('install_command')
            if not install_command:
                log.error(f"Commande d'installation manquante pour {model_id}")
                return False
            
            log.info(f"📥 Début téléchargement {model_id}...")
            if progress_callback:
                progress_callback({"status": "starting", "model": model_id})
            
            # Lancer ollama pull de manière asynchrone
            process = await asyncio.create_subprocess_shell(
                install_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Monitorer la progression (basique)
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                line_str = line.decode().strip()
                log.debug(f"Ollama pull: {line_str}")
                
                if progress_callback:
                    # Parsing basique de la progression d'Ollama
                    if "pulling" in line_str.lower():
                        progress_callback({
                            "status": "downloading", 
                            "model": model_id, 
                            "message": line_str
                        })
                    elif "verifying" in line_str.lower():
                        progress_callback({
                            "status": "verifying", 
                            "model": model_id, 
                            "message": line_str
                        })
            
            # Attendre la fin du processus
            await process.wait()
            
            if process.returncode == 0:
                log.success(f"✅ Modèle {model_id} téléchargé avec succès")
                if progress_callback:
                    progress_callback({"status": "completed", "model": model_id})
                return True
            else:
                error_output = await process.stderr.read()
                log.error(f"❌ Échec téléchargement {model_id}: {error_output.decode()}")
                if progress_callback:
                    progress_callback({
                        "status": "error", 
                        "model": model_id, 
                        "error": error_output.decode()
                    })
                return False
                
        except Exception as e:
            log.error(f"Erreur téléchargement {model_id}: {e}")
            if progress_callback:
                progress_callback({"status": "error", "model": model_id, "error": str(e)})
            return False
    
    def set_current_model(self, model_id: str) -> bool:
        """
        Change le modèle actuel (sans redémarrer tout le système)
        
        Args:
            model_id: ID du nouveau modèle
            
        Returns:
            bool: Succès du changement
        """
        try:
            # Vérifier que le modèle est installé
            if not self.is_model_available(model_id):
                log.warning(f"Modèle {model_id} non installé, impossible de basculer")
                return False
            
            # Test rapide du modèle
            try:
                test_response = ollama.generate(
                    model=model_id,
                    prompt="Test",
                    options={"num_predict": 1}
                )
                if not test_response:
                    log.error(f"Test du modèle {model_id} échoué")
                    return False
            except Exception as e:
                log.error(f"Erreur test modèle {model_id}: {e}")
                return False
            
            # Mettre à jour le modèle actuel
            self.current_model = model_id
            log.success(f"✅ Modèle basculé vers {model_id}")
            return True
            
        except Exception as e:
            log.error(f"Erreur changement modèle vers {model_id}: {e}")
            return False
    
    def get_current_model(self) -> Optional[str]:
        """Retourne le modèle actuellement utilisé"""
        return self.current_model
    
    def update_llm_client_model(self, llm_client, model_id: str) -> bool:
        """
        Met à jour le modèle d'un client LLM existant
        
        Args:
            llm_client: Instance de JarvisLLM
            model_id: Nouveau modèle à utiliser
            
        Returns:
            bool: Succès de la mise à jour
        """
        try:
            if not self.is_model_available(model_id):
                log.warning(f"Modèle {model_id} non disponible")
                return False
            
            # Mettre à jour le modèle dans le client LLM
            llm_client.model = model_id
            self.current_model = model_id
            
            log.success(f"✅ Client LLM mis à jour avec {model_id}")
            return True
            
        except Exception as e:
            log.error(f"Erreur mise à jour client LLM: {e}")
            return False


# Test standalone
if __name__ == "__main__":
    import asyncio
    
    async def test_manager():
        manager = ModelManager()
        
        print("📋 Statut des modèles:")
        status = manager.get_model_status()
        for model_id, info in status['models'].items():
            installed = "✅" if info['installed'] else "❌"
            print(f"  {installed} {model_id} - {info['display_name']}")
        
        print(f"\n🎯 Modèle actuel: {manager.get_current_model()}")
        
    asyncio.run(test_manager())