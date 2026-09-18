# Fonzi — Robot Rock Rock Rock (`robot-rrr`)

Fonzi est un robot humanoïde (Yanshee) hautain, menteur et manipulateur. Il joue au jeu Pierre-Feuille-Ciseaux (et à un mode Astro Roboscope), mais a une particularité : physiquement, il ne peut faire QUE la Pierre. Pour compenser cette limitation, il triche en permanence, réinvente les règles et utilise une IA locale (LLM) pour générer du dialogue sarcastique et adapter son arbitrage.

---

## Stack Technique

* **Framework Web & Sockets :** FastAPI, WebSockets
* **Vision & Détection :** OpenCV, MediaPipe (`HandLandmarker`)
* **IA & Generative Text :** Unsloth / Ollama (`Qwen3.5-9B-MTP-GGUF`)
* **Synthèse Vocale (TTS) :** `pyttsx3` (voix locale) + API Média Yanshee
* **Contrôle Moteur :** API REST Yanshee

---

## Prérequis

* **Python 3.10+**
* Un robot **Yanshee** connecté sur le même réseau local.
* Un serveur **Unsloth / Ollama** exécutant le modèle LLM sur `http://127.0.0.1:8888`.
* Le fichier de modèle MediaPipe `hand_landmarker.task` placé à la racine du projet.
* Une caméra (locale ou flux MJPEG distant du robot).

---

## Installation & Configuration

1. **Cloner le dépôt et créer l'environnement virtuel :**
    git clone https://github.com/Hakazoki/robot-rrr.git
    cd robot-rrr
    python -m venv venv
    source venv/bin/activate  # Sur Windows: venv\Scripts\activate

2. **Installer les dépendance pip**
    pip install -r requirements.txt

3. **Vérifier la configuration réseau**
    Ip du robot Yanshee : 192.168.0.150 (modifiable dans tts_service.py et vision.py)
    Endpoint de Unsloth : exemple http://127.0.0.1:8888/v1/chat/completion

---

## Démarrage du projet

1. **Lancer le flux vidéo de vision**
    python stream_camera.py (Le flux vidéo souvre sur le port 8080)

2. **Lancer le server Websocket** 
    python -m uvicorn main:app --reload --port 8000 (page web sur : http://localhost:8000)
