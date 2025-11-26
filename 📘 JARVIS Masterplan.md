# **📘 JARVIS Masterplan**

Version : 1.0 (Post-Audit)

Statut : Référence pour Refactoring & Optimisation

Règle d'Or : "Single Responsibility Principle" (Un module \= Une fonction majeure)

---

## **1\. 👁️ Vision & Philosophie**

Jarvis n'est pas un simple script, c'est une architecture cognitive modulaire.

* **Approche :** Biomimétisme (Cerveau humain).  
* **Priorité actuelle :** Stabiliser le cœur (Audio/LLM) avant d'ajouter les membres (Vision/Mémoire).  
* **Expérience Utilisateur :** Fluidité absolue. Le système doit s'adapter à la complexité de la demande (Mode Express vs Expert) sans configuration manuelle.  
  ---

  ## **2\. 🏗️ Architecture & Responsabilités**

  ### **🧠 Le Cerveau (Backend Python)**

* **jarvis.py** *(Point d'entrée)* : Lance le serveur FastAPI et l'UI. Ne contient **aucune** logique métier.  
* **cortex\_prefrontal/**  
  * llm\_client.py : Gère uniquement la connexion à Ollama et le streaming.  
* **lobes\_temporaux/**  
  * conversation\_flow.py : **Orchestrateur**. C'est le seul script autorisé à faire le lien STT \-\> LLM \-\> TTS.  
  * stt.py : L'oreille (Whisper).  
  * tts.py : La voix (Façade pour les moteurs audio).  
* **hypothalamus/**  
  * config\_coordinator.py : Le gardien de settings.yaml.  
  * voice\_manager.py : L'inventaire des voix disponibles (Backend).

  ### **🔌 Le Système Nerveux (Communication)**

* **thalamus/**  
  * websocket\_relay.py : Tuyau de communication pur. Il ne doit pas "traiter" les données, juste les passer.

  ### **😀 Le Visage (Frontend JS)**

* **app-main.js** : Chef d'orchestre côté navigateur.  
* **voice-lab.js** : Interface spécialisée pour le clonage de voix.  
  ---

  ## **3\. 🧠 Stratégie d'Intelligence Adaptative ("Gearbox")**

Pour optimiser le coût/temps sans sacrifier la qualité, Jarvis utilise un système d'engagement progressif.

| Niveau | Déclencheur | Action Système | Latence Perçue |
| :---- | :---- | :---- | :---- |
| **Réflexe** | "Bonjour", "Merci", "Arrête" | Réponse scriptée ou LLM température 0.1. | \< 1s |
| **Standard** | Questions courantes | LLM Standard (Llama 3 8B). Streaming direct. | \~2s |
| **Profond** | "Analyse...", "Explique...", "Code..." | 1\. Accusé réception immédiat ("Je regarde ça..."). 2\. Activation mode "Deep Thinking". 3\. Réponse structurée. | \< 1s (Accusé) \~2s |

---

## **4\. 🩺 Audit de Santé du Code (Refactoring)**

### **🚨 Zone Rouge \- Part I : Bugs à Corriger (Priorité P0)**

*Ces corrections doivent être appliquées avant tout refactoring d'architecture.*

#### 🐛 Interface & UX

* ***Position Boutons Conversation :***  
  * *Problème : Les icônes "Poubelle" et "Disquette" sont mal placées.*  
  * *Cible : `web_interface/styles/panels/dialogue.css`.*  
  * *Fix : Vérifier le `display: flex` et `justify-content: space-between` sur `.dialogue-header`.*  
* ***Crash Console JS :***  
  * *Erreur : `ReferenceError: cleanupLogs is not defined`.*  
  * *Cible : `web_interface/js/debug-logger.js`.*  
  * *Fix : Créer la fonction `cleanupLogs()` (qui supprime les vieux logs du DOM pour libérer la mémoire) ou renommer l'appel dans `app-main.js` si c'était une erreur de nommage.*

#### 🐛 Logique Métier (Backend)

* ***Sélection de Voix Inopérante :***  
  * *Problème : Le changement dans le menu ne change pas la voix active (reste sur clonée).*  
  * *Diagnostique : Le `config_coordinator.py` met à jour le JSON, mais ne déclenche pas `conversation_flow.reload_tts()`.*  
  * *Fix : Forcer le rechargement du moteur TTS lors d'un update config.*  
* ***Test Voix HS :***  
  * *Problème : Le bouton ne fait rien.*  
  * *Cible : `jarvis.py` (route `/api/voice/test`) et `settings-modal.js`.*  
  * *Fix : Vérifier que l'ID de la voix est bien passé au backend.*  
* ***Changement Modèle LLM (Ollama) :***  
  * *Problème : Le choix n'a aucun impact.*  
  * *Fix : `conversation_flow.py` doit réinstancier `llm_client` avec le nouveau modèle quand la config change.*  
* ***Microphone "Fantôme" :***  
  * *Problème : Liste vide ou "Défaut" uniquement.*  
  * *Fix : `interface_bridge.py` doit correctement mapper les devices renvoyés par PyAudio et le JS doit peupler le `<select>` correctement.*

  ## **2\. 🏗️ Évolution de l'Architecture : "La Stratégie Adaptative"**

  ### **Le Cerveau à Géométrie Variable**

Au lieu de modes figés, Jarvis s'adapte organiquement à la conversation.

* **Interaction Rapide (Ping-Pong) :** Pour les salutations, confirmations. Latence \< 1s.  
* **Mode Profond (Deep Thinking) :**  
  * Jarvis détecte une question complexe.  
  * Il prévient : *"C'est un vaste sujet..."* (Réponse immédiate).  
  * Il enclenche une réflexion longue en arrière-plan.  
  * Il répond en détail.  
  * Il repasse automatiquement en mode rapide ensuite.

  ### **Nouvelle Structure des Menus (UX)**

Pour nettoyer l'interface, la navigation sera refondue :

1. **Paramètres** (Technique : Micro, Audio, Thème).  
2. **Vision IA** (Module d'interaction temps réel).  
3. **Personnalisation** (Nouveau Menu Parent) :  
   * *Sous-menu :* **Clonage Voix** (Le Voice Lab actuel).  
   * *Sous-menu :* **Profils LLM** (Nouvelle fonctionnalité : Rôles, Prompts système, "Tu es un expert en...").

   ---

   ## **3\. 🩺 Refactoring & Nettoyage (Priorité P1)**

Une fois les bugs P0 corrigés, on applique ce nettoyage pour éviter les régressions.

### **🗑️ À Supprimer (Code Mort)**

| Fichier | Cible | Action |
| :---- | :---- | :---- |
| web\_interface/js/utils.js | isValidEmail | Supprimer |
| thalamus/message\_router.py | Tout le fichier | Supprimer  (Le websocket\_relay gère déjà le routage) |
| lobes\_temporaux/memory\_manager.py | Tout le fichier | Déplacer vers \_experimental/ |

### **🔄 À Unifier (Doublons)**

| Zone Fonctionnelle | Action |
| :---- | :---- |
| **Gestion des Voix** | Centraliser toute la logique dans hypothalamus/voice\_manager.py. Le JS ne fait qu'afficher ce que l'API /api/voices renvoie. Plus de logique métier dans le frontend. |
| **Configuration** | Fusionner config\_manager.py et config\_coordinator.py en un seul point d'entrée robuste pour settings.yaml. |

---

## **4\. 🛠️ Roadmap Technique Mise à Jour**

### **Phase 1 : "Urgence Médicale" (Immédiat)**

1. \[ \] **Fix CSS Header** : Remettre les icônes à leur place.  
2. \[ \] **Fix JS Crash** : Définir cleanupLogs pour arrêter les erreurs console.  
3. \[ \] **Fix Voix & Modèles** : S'assurer que le changement dans le menu recharge *vraiment* le moteur Python derrière.  
4. \[ \] **Fix Micros** : Lister les vrais périphériques matériels.

   ### **Phase 2 : Refactoring & Interface**

1. \[ \] **Refonte Menu** : Créer le menu "Personnalisation" et y déplacer le Voice Lab.  
2. \[ \] **Création Profils LLM** : Ajouter l'interface pour créer/éditer les rôles (System Prompts).  
3. \[ \] **Nettoyage Code** : Supprimer les fichiers morts identifiés.

   ### **Phase 3 : Optimisation Performance**

1. \[ \] **Monitoring** : Ajouter des logs de temps (TTFT \- Time To First Token) dans la console Debug.  
2. \[ \] **Vitesse TTS** : Implémenter le streaming audio "phrase par phrase" plus agressif.  
3. \[ \] **Multi-moteurs** : Ajouter Google TTS ou Piper pour comparer la vitesse.  
1. 

