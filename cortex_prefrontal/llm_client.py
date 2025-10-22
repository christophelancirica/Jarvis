
"""
Client LLM pour Jarvis
Gère la connexion à Ollama et l'analyse de complexité
"""

import ollama
import json
import yaml
from pathlib import Path
from hypothalamus.logger import log

import torch
torch.serialization.add_safe_globals(['RAdam', 'AdamW'])

class JarvisLLM:
    def __init__(self, personality="Jarvis"):
        # Charger config
        config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.model = self.config['llm']['model_default']
        self.personality = personality
        
        log.success(f"LLM prêt ({self.model}) - Personnalité: {personality}", "🧠")
    
    def analyze_complexity(self, user_input: str) -> dict:
        """
        Analyse la complexité de la demande utilisateur
        """
        
        # Adapter le prompt selon la personnalité
        if self.personality == "Jarvis":
            assistant_description = "Tu es Jarvis, un assistant masculin intelligent et direct, inspiré de Iron Man. Ton ton est professionnel mais amical."
        else:  # Samantha
            assistant_description = "Tu es Samantha, une assistante féminine intelligente et direct, inspiré de Iron Man. Ton ton est professionnel mais doux et bienveillant."
        
        prompt = f"""{assistant_description}

Tu analyses la complexité des questions pour optimiser le temps de réponse.

Niveaux:
- Express: Questions factuelles simples, commandes directes, salutations (< 2s)
- Standard: Conversations normales, explications, recherches (3-5s)
- Expert: Planification, analyse complexe, projets (> 10s)

Question: "{user_input}"

Réponds UNIQUEMENT avec ce format JSON:
{{
  "complexity": "Express|Standard|Expert",
  "analyse": "Pourquoi ce niveau",
  "reponse": "Ta réponse à la question"
}}"""

        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": 0.3,
                    "num_predict": 500
                }
            )
            
            # Parser le JSON
            result = json.loads(response['response'])
            return result
            
        except json.JSONDecodeError:
            return {
                "complexity": "Standard",
                "analyse": "Erreur parsing JSON",
                "reponse": response['response']
            }
    
    def generate_response(self, user_input: str, complexity: str) -> str:
        """
        Génère une réponse selon le niveau de complexité
        """
        
        # Adapter selon personnalité
        if self.personality == "Jarvis":
            tone = "professionnel, intelligent, légèrement ironique parfois"
            style = "concis et efficace"
        else:  # Samantha
            tone = "professionnel, intelligent, chaleureux, empathique, doux"
            style = "concis et efficace"
        
        # Récupérer les paramètres selon complexité
        if complexity == "Express":
            max_tokens = self.config['llm']['express']['max_tokens']
            temp = self.config['llm']['express']['temperature']
        elif complexity == "Standard":
            max_tokens = self.config['llm']['standard']['max_tokens']
            temp = self.config['llm']['standard']['temperature']
        else:  # Expert
            max_tokens = self.config['llm']['expert']['max_tokens']
            temp = self.config['llm']['expert']['temperature']
        
        prompt = f"""Tu es {self.personality}, un assistant vocal français.

Ton : {tone}
Style : {style}

Question: {user_input}

Réponds de manière naturelle et {style}."""

        response = ollama.generate(
            model=self.model,
            prompt=prompt,
            options={
                "temperature": temp,
                "num_predict": max_tokens
            }
        )
        
        return response['response']