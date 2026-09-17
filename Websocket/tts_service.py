import os
from typing import Dict
import asyncio
import pyttsx3
import requests

ROBOT_IP: str = "192.168.0.150"
API_URL: str = f"http://{ROBOT_IP}:9090/v1/media/music"
FILENAME: str = "fonzi_dialogue.wav"


def _generate_local_tts(text: str, filepath: str) -> None:
    engine = pyttsx3.init()
    engine.setProperty('rate', 160)
    engine.setProperty('volume', 1.0)

    voices = engine.getProperty('voices')
    for voice in voices:
        if 'Guillaume' in voice.name:
            engine.setProperty('voice', voice.id)
            break

    engine.save_to_file(text, filepath)
    engine.runAndWait()


def _upload_and_play_sync(text: str) -> None:
    filepath = FILENAME
    try:
        _generate_local_tts(text, filepath)
        if not os.path.exists(filepath):
            print("[-] Erreur : Le fichier WAV n'a pas été généré.")
            return

        with open(filepath, 'rb') as f:
            files = {'file': (os.path.basename(filepath), f, 'audio/wav')}
            response = requests.post(API_URL, files=files, timeout=10.0)

        if not response.ok:
            print(f"[-] Échec Upload : HTTP {response.status_code}")
            return

        payload: Dict[str, str] = {"name": os.path.basename(filepath), "operation": "start"}
        requests.put(API_URL, json=payload, timeout=5.0)
        print("[+] TTS lu avec succès sur Yanshee.")

    except Exception as e:
        print(f"[-] Erreur TTS Yanshee : {e}")


async def speak_on_yanshee(text: str) -> None:
    """Exécute la génération et la lecture audio dans un thread non-bloquant."""
    await asyncio.to_thread(_upload_and_play_sync, text)