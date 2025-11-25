# 🤖 Jarvis - Assistant Vocal Intelligent

Assistant vocal local utilisant Llama 3.1, Whisper et Coqui TTS.

## 🚀 Fonctionnalités

- ✅ Reconnaissance vocale (Whisper)
- ✅ LLM local (Llama 3.1:8b via Ollama)
- ✅ Synthèse vocale avec voice cloning (XTTS)
- ✅ Streaming audio optimisé
- ✅ Multi-personnalités (Jarvis/Samantha)

## 📋 Prérequis

- Python 3.10+
- Ollama installé avec llama3.1:8b
- 16GB+ RAM recommandés

## 🔧 Installation
```bash
git clone https://github.com/christophelancirica/Jarvis.git
cd Jarvis
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## 🎯 Utilisation
```bash
python jarvis.py
```

## 🧠 Architecture

- `cortex_prefrontal/` : Gestion LLM
- `lobes_temporaux/` : STT/TTS
- `hypothalamus/` : Logger système