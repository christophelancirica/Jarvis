# **🛠️ REF\_TECHNIQUE\_OPTIMISATION**

Objectif : Guide de référence pour le nettoyage, le refactoring et l'implémentation de la stratégie adaptative.

Basé sur : jarvis\_functions\_analysis\_v3.md et les nouvelles directives LLM.

---

## **1\. 📂 Arborescence & Rôles des Fichiers**

Cette carte permet de localiser instantanément quel fichier modifier pour une fonctionnalité donnée.

Plaintext  
JARVIS/  
│  
├── jarvis.py                        \# \[TRONC CÉRÉBRAL\] Point d'entrée, lance FastAPI et l'UI  
├── requirements.txt                 \# Dépendances Python  
│  
├── config/                          \# \[MÉMOIRE CONFIG\] Fichiers JSON statiques  
│   ├── settings.yaml                \# Config globale (à privilégier comme source unique)  
│   ├── voices.json                  \# Inventaire des voix  
│   ├── models.json                  \# Inventaire des LLM  
│   └── whisper\_config.json          \# Paramètres STT  
│  
├── cortex\_prefrontal/               \# \[INTELLIGENCE\]  
│   ├── llm\_client.py                \# Gestionnaire Ollama (Streaming)  
│   └── model\_manager.py             \# Installation/Switch des modèles  
│  
├── lobes\_temporaux/                 \# \[AUDIO I/O\]  
│   ├── conversation\_flow.py         \# Orchestrateur central (STT \-\> LLM \-\> TTS)  
│   ├── stt.py                       \# Faster-Whisper \+ VAD  
│   ├── tts.py                       \# Façade pour la synthèse vocale  
│   ├── audio\_generator.py           \# Moteurs de génération (Edge, XTTS, Coqui)  
│   ├── audio\_pipeline.py            \# Gestion file d'attente (Streaming audio)  
│   └── voice\_cloner.py              \# Logique de clonage (XTTS)  
│  
├── hypothalamus/                    \# \[RÉGULATION SYSTÈME\]  
│   ├── config\_coordinator.py        \# Coordination des configs en temps réel  
│   ├── device\_manager.py            \# Gestion des micros/speakers  
│   ├── system\_monitor.py            \# Surveillance CPU/RAM  
│   └── voice\_manager.py             \# Gestionnaire inventaire voix (Backend)  
│  
├── thalamus/                        \# \[COMMUNICATION\]  
│   ├── websocket\_relay.py           \# Gestionnaire WebSocket (Serveur \<-\> Client)  
│   ├── message\_router.py            \# Dispatch des messages (⚠️ Peu utilisé actuellement)  
│   ├── interface\_bridge.py          \# Pont API REST  
│   ├── app\_config\_endpoints.py      \# Routes API Config  
│   └── whisper\_config\_api.py        \# Routes API Whisper  
│  
└── web\_interface/                   \# \[VISAGE / UI\]  
    ├── index.html                   \# Structure HTML  
    ├── styles/                      \# CSS modulaire (base, layout, panels...)  
    └── js/                          \# Logique Frontend  
        ├── app-main.js              \# Orchestrateur JS  
        ├── websocket-manager.js     \# Client WS (Réception/Envoi)  
        ├── message-handler.js       \# Affichage chat & bulles  
        ├── voice-manager.js         \# Gestion voix (Frontend)  
        ├── voice-lab.js             \# Interface clonage  
        ├── settings-modal.js        \# UI Paramètres  
        ├── config-loader.js         \# Chargement JSON (⚠️ À refactoriser)  
        ├── debug-logger.js          \# Console virtuelle  
        └── ...

---

## **2\. 🧠 Nouvelle Stratégie LLM : "Gearbox Adaptative"**

Au lieu de modes rigides (Express/Expert), le système adopte un comportement conversationnel fluide basé sur le contexte.

### **Le Flux "Handshake" (Exploratoire)**

1. **Entrée Utilisateur :** "Parle-moi de la physique quantique."  
2. **Analyse Rapide (Gear 1\) :** Le LLM détecte un sujet vaste.  
3. **Réponse Immédiate (TTS) :** "C'est un sujet passionnant. Tu veux aborder l'histoire ou les principes ?"  
   * *Gain :* Latence perçue quasi-nulle.  
   * *Action :* Le système active un flag DEEP\_THINKING\_NEXT \= True.  
4. **Réponse Utilisateur :** "Les principes."  
5. **Traitement Approfondi (Gear 5\) :**  
   * Le système voit le flag DEEP\_THINKING\_NEXT.  
   * Il alloue plus de temps/tokens ou change de prompt système pour une réponse structurée.  
   * Il désactive le flag (DEEP\_THINKING\_NEXT \= False) après la réponse, revenant à une conversation fluide normale.

**Implémentation technique :**

* Modifier cortex\_prefrontal/llm\_client.py pour accepter un paramètre de contexte dynamique.  
* Modifier conversation\_flow.py pour maintenir cet état de "profondeur de réflexion" entre deux tours de parole.

---

## **3\. 🧹 Plan de Refactoring & Nettoyage**

Basé sur votre analyse jarvis\_functions\_analysis\_v3.md, voici les zones prioritaires pour supprimer les doublons et le code mort.

### **🔴 Code à Supprimer (Doublons/Inutile)**

| Fichier | Fonction / Code | Action | Pourquoi ? |
| :---- | :---- | :---- | :---- |
| web\_interface/js/utils.js | isValidEmail() | **Supprimer** | Inutile pour un assistant vocal. |
| web\_interface/js/utils.js | formatFileSize() | **Supprimer** | Inutile si pas d'upload de fichiers lourds. |
| thalamus/message\_router.py | Tout le fichier | **Questionner** | L'analyse indique "Peu utilisé". Si websocket\_relay fait le dispatch, ce fichier est du code mort. |
| lobes\_temporaux/memory\_manager.py | Tout le fichier | **Archiver** | Fonctionnalité "Fantôme" (RAG) non connectée. À déplacer dans un dossier \_future. |

### **🟠 Code à Consolider (Refactoring)**

| Zone | Problème | Solution |
| :---- | :---- | :---- |
| **Gestion des Voix** | Logique éclatée entre voice\_manager.py (backend), voice-manager.js (frontend) et config\_loader.js. | Centraliser la logique métier dans le **Backend** (hypothalamus/voice\_manager.py). Le Frontend ne doit faire que de l'affichage via API. |
| **Chargement Config** | config\_loader.js (Frontend) charge aussi des voix et thèmes. | Déplacer populateVoiceSelect vers voice-manager.js et populateThemeSelect vers theme-manager.js. |
| **Logs** | handleErrorMessage (JS) redondant avec addLogEntry. | Supprimer les wrappers inutiles, appeler addLogEntry directement. |

---

## **4\. 🎯 Guide de Modification Rapide**

Si vous voulez...

* **Optimiser la latence TTS (Génération trop longue) :**  
  * Regardez : lobes\_temporaux/audio\_pipeline.py  
  * Action : Vérifiez la fonction \_generation\_worker. Assurez-vous que audio\_generator utilise bien le cache d'embeddings pour XTTS (\_preload\_xtts\_embeddings).  
  * Action : Vérifiez que \_play\_audio\_chunk (lecture) se déclenche dès le premier chunk reçu, sans attendre la fin de la génération totale.  
* **Ajouter un nouveau moteur TTS (ex: Google) :**  
  * Fichier : lobes\_temporaux/audio\_generator.py  
  * Action : Ajouter une méthode \_generate\_google\_tts et l'enregistrer dans generate\_audio.  
* **Modifier le comportement du LLM (Nouvelle stratégie) :**  
  * Fichier : lobes\_temporaux/conversation\_flow.py  
  * Action : C'est ici que se décide l'envoi au LLM. Implémentez la logique de "Flag" (DEEP\_THINKING) ici avant d'appeler self.llm.generate\_response\_stream.  
* **Nettoyer l'interface Web :**  
  * Fichier : web\_interface/js/app-main.js  
  * Action : C'est le chef d'orchestre. Nettoyez les appels aux fonctions supprimées.

