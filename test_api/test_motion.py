import requests
import time
from typing import Dict, Any

ROBOT_IP: str = "192.168.0.150"
ROBOT_PORT: int = 9090  
URL: str = f"http://{ROBOT_IP}:{ROBOT_PORT}/v1/motions"

def jouer_danse(nom_danse: str) -> None:
    # Payload API
    payload: Dict[str, Any] = {
        "operation": "start",
        "motion": {
            "name": nom_danse,
            "repeat": 1,
            "direction": "left", 
            "speed": "normal"
        }
    }
    
    try:
        print(f"[*] Envoi de la commande de mouvement : {nom_danse}")
        response = requests.put(URL, json=payload, timeout=5.0)

        if response.ok:
            print(f"[+] Succès (HTTP {response.status_code}) : Le robot exécute '{nom_danse}'.")
        else:
            print(f"[-] Rejet API (HTTP {response.status_code}) : {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"[-] Erreur de communication réseau : {e}")

if __name__ == "__main__":
    motion = input()
    jouer_danse(motion)