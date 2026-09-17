import pyttsx3
import requests
import os
from typing import Dict, Any

ROBOT_IP: str = "192.168.0.150"
API_URL: str = f"http://{ROBOT_IP}:9090/v1/media/music"
FILENAME: str = "fonzi_test.wav"

def generate_local_tts(text: str, filepath: str) -> None:
    """Génère le ficheir wav en local."""
    print(f"[*] Génération TTS : {filepath}")
    engine = pyttsx3.init()
    engine.setProperty('rate', 160)
    engine.setProperty('volume', 1.0)
    
    """Cherche une voix spécifique"""
    voices = engine.getProperty('voices')
    for voice in voices:
        if 'Paul' in voice.name:
            engine.setProperty('voice', voice.id)
            break
            
    engine.save_to_file(text, filepath)
    engine.runAndWait()

def upload_to_yanshee(filepath: str) -> bool:
    """Upload le fichier WAV sur le robot."""
    print(f"[*] Upload de {filepath} en cours...")
    try:
        with open(filepath, 'rb') as f:
            files = {'file': (os.path.basename(filepath), f, 'audio/wav')}
            response = requests.post(API_URL, files=files, timeout=10.0)
            
        if response.ok:
            print("[+] Upload réussi.")
            return True
        else:
            print(f"[-] Echec Upload: HTTP {response.status_code} | {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[-] Erreur réseau (Upload): {e}")
        return False

def play_on_yanshee(filename: str) -> None:
    """Lis le fichier spécifié."""
    print(f"[*] Ordre de lecture pour {filename}...")
    payload: Dict[str, str] = {
        "name": filename,
        "operation": "start"
    }
    
    try:
        response = requests.put(API_URL, json=payload, timeout=5.0)
        if response.ok:
            print("[+] Lecture en cours sur le robot.")
        else:
            print(f"[-] Echec Lecture: HTTP {response.status_code} | {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"[-] Erreur réseau (Lecture): {e}")

if __name__ == "__main__":
    phrase = "Système vocal français activé. Prêt à détruire les humains."
    
    generate_local_tts(phrase, FILENAME)
    
    if os.path.exists(FILENAME):
        if upload_to_yanshee(FILENAME):
            play_on_yanshee(FILENAME)
    else:
        print("[-] Erreur : Le fichier WAV n'a pas été généré.")