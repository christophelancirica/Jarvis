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
        config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        if not config_path.exists():
            # Fallback si pas de config projet
            config_path = Path(__file__).parent / "settings.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.model = self.config['llm']['model_default']
        self.personality = personality
        
        log.success(f"LLM prêt ({self.model}) - Mode: {personality}", "🧠")

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
        🔥 STREAMING NATIF - Yield les tokens un par un depuis Ollama
        Utilisé par l'interface web pour affichage temps réel
        """
        # 1️⃣ Estimation de la complexité locale
        complexity = self.estimate_complexity(user_input)

        # 2️⃣ Réglages dynamiques selon complexité
        if complexity == "Express":
            temperature = 0.3
            max_tokens = 500
        elif complexity == "Standard":
            temperature = 0.5
            max_tokens = 1200
        else:  # Expert
            temperature = 0.7
            max_tokens = 3000

        log.info(f"Complexité estimée : {complexity} ({temperature=}, {max_tokens=})")

        # 3️⃣ Description du ton selon la personnalité
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

        # 4️⃣ Construire le prompt complet
        prompt = f"""{assistant_desc}

Question ({complexity}): {user_input}

Réponse:"""

        # 5️⃣ Appel à Ollama avec streaming natif
        try:
            log.debug("Démarrage streaming Ollama...")
            
            # 🔥 STREAMING NATIF OLLAMA
            stream = ollama.generate(
                model=self.model,
                prompt=prompt,
                stream=True,  # ⚡ STREAMING ACTIVÉ
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            )
            
            # Yield chaque token reçu en temps réel
            token_count = 0
            for chunk in stream:
                if 'response' in chunk:
                    token = chunk['response']
                    if token:  # Ignorer les tokens vides
                        token_count += 1
                        yield token
            
            log.debug(f"Streaming terminé: {token_count} tokens")

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