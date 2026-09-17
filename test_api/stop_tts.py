import pyttsx3
import requests
import os
from typing import Dict, Any

ROBOT_IP: str = "192.168.0.150"
API_URL: str = f"http://{ROBOT_IP}:9090/v1/media/music"
FILENAME: str = "fonzi_test.wav"


def stop_file(filename: str) -> None:
    """Lis le fichier spécifié."""
    print(f"[*] Ordre d'arrêt pour' {filename}...")
    payload: Dict[str, str] = {
        "name": filename,
        "operation": "stop"
    }
    
    try:
        response = requests.put(API_URL, json=payload, timeout=5.0)
        if response.ok:
            print("[+] Arrèt de lecture.")
        else:
            print(f"[-] Echec d'arrèt: HTTP {response.status_code} | {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"[-] Erreur réseau: {e}")

stop_file(FILENAME)