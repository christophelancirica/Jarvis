"""
Client LLM  pour Jarvis avec streaming natif
Avec support streaming web et CMD
"""

import ollama
import yaml
from pathlib import Path
from hypothalamus.logger import log


class JarvisLLM:
    """LLM Jarvis unifié avec support streaming natif"""
    
    def __init__(self, personality="Jarvis"):
        # Charger config
        config_path = Path(__file__).parent.parent / "config/settings.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.model = self.config['llm']['model']
        self.personality = personality
        self.conversation_history = []
        self._initialize_system_prompt()
        self._warmup_model()
        
        log.success(f"LLM prêt ({self.model}) - Mode: {personality}", "🧠")

    def _warmup_model(self):
        """Envoie une requête silencieuse pour charger le modèle en mémoire."""
        try:
            log.info(f"🔥 Préchauffage du modèle LLM: {self.model}...")
            ollama.generate(model=self.model, prompt=".", options={"num_predict": 1}, keep_alive=0)
            log.success(f"✅ Modèle {self.model} préchauffé.")
        except Exception as e:
            log.error(f"❌ Échec du préchauffage du modèle {self.model}: {e}")

    def _initialize_system_prompt(self):
        if self.personality == "Jarvis":
            assistant_desc = (
                "Tu es Jarvis, un assistant français intelligent, précis et un peu ironique. "
                "Réponds toujours en français, de façon claire, naturelle et concise."
            )
        else:
            assistant_desc = (
                "Tu es Samantha, une assistante française douce, empathique et professionnelle. "
                "Réponds toujours en français, de façon fluide, naturelle et concise."
            )

        self.conversation_history = [{'role': 'system', 'content': assistant_desc}]

    def estimate_complexity(self, text: str) -> str:
        """Analyse simple de la complexité (mots-clés + longueur)"""
        text_lower = text.lower()
        word_count = len(text_lower.split())

        expert_keywords = [
            "analyse", "explique", "pourquoi", "comment", "comparer", "théorie",
            "concept", "quantique", "algorithme", "développe", "projet", "plan",
            "fonctionnement", "mécanisme", "histoire", "impact", "différence"
        ]

        simple_keywords = [
            "salut", "bonjour", "heure", "merci", "date",
            "température", "météo", "au revoir"
        ]

        # Cas simples : social / commande
        if any(k in text_lower for k in simple_keywords):
            return "Express"

        # Cas complexes : question profonde / notion avancée
        if any(k in text_lower for k in expert_keywords):
            return "Expert"

        # Sinon on se base sur la longueur
        if word_count <= 8:
            return "Express"
        elif word_count <= 30:
            return "Standard"
        else:
            return "Expert"

    def generate_response_stream(self, user_input: str):
        """
        🔥 STREAMING NATIF avec CONTEXTE - Yield les tokens un par un depuis Ollama
        Utilise ollama.chat pour maintenir l'historique.
        """
        try:
            # Ajouter le message de l'utilisateur à l'historique
            self.conversation_history.append({'role': 'user', 'content': user_input})

            log.debug("Démarrage streaming Ollama avec contexte...")
            
            # Utiliser ollama.chat pour le streaming avec historique
            stream = ollama.chat(
                model=self.model,
                messages=self.conversation_history,
                stream=True
            )
            
            assistant_response = ""
            for chunk in stream:
                token = chunk['message']['content']
                if token:
                    assistant_response += token
                    yield token
            
            # Ajouter la réponse complète de l'assistant à l'historique
            self.conversation_history.append({'role': 'assistant', 'content': assistant_response})
            log.debug("Streaming terminé et contexte mis à jour.")

        except Exception as e:
            log.error(f"Erreur streaming Ollama: {e}")
            yield "Désolé, une erreur est survenue pendant la réponse."

    def generate_response(self, user_input: str) -> str:
        """
        Méthode de compatibilité (non-streaming)
        Récupère tout le stream et le joint pour retourner une string complète
        Utilisé pour compatibilité avec ancien code ou usage simple
        """
        # Récupérer tout le stream et le joindre
        tokens = list(self.generate_response_stream(user_input))
        return ''.join(tokens)

    def ask(self, user_input: str) -> str:
        """Méthode courte (compatibilité)"""
        return self.generate_response(user_input)

    def change_model(self, new_model: str):
        """Change le modèle LLM à la volée, réinitialise l'historique et préchauffe le nouveau modèle."""
        old_model = self.model
        self.model = new_model
        self.clear_history()
        self._warmup_model()
        log.info(f"🔄 Modèle changé: {old_model} → {new_model}. L'historique de la conversation a été réinitialisé.")
        return True

    def clear_history(self):
        """Réinitialise l'historique de la conversation en ne gardant que le prompt système."""
        self._initialize_system_prompt()
        log.info("Historique de la conversation LLM réinitialisé.")

    def get_current_model(self) -> str:
        """Retourne le modèle actuellement utilisé"""
        return self.model

# Test standalone
if __name__ == "__main__":
    print("🧪 Test LLM Unifié")
    
    try:
        llm = JarvisLLM("Samantha")
        
        print("\n🔥 Test streaming:")
        print("Question: Raconte-moi une blague")
        print("Réponse: ", end="", flush=True)
        
        for token in llm.generate_response_stream("Raconte-moi une blague"):
            print(token, end="", flush=True)
        
        print("\n\n✅ Test terminé")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")