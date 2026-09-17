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
    engine.setProperty('rate', 320)
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
    phrase = "La Bible (du grec βιβλία / biblía, littéralement « les livres[1] ») est un terme générique désignant l'ensemble des textes saints du christianisme, qui incluent le Tanakh, ensemble des textes saints du judaïsme. La Bible chrétienne, qui connaît plusieurs canons selon les époques et les confessions, se compose généralement des écrits de l'Ancien Testament (constitué par le Tanakh repris tel quel par les églises protestantes mais augmenté des livres deutérocanoniques pour les catholiques) et des écrits du Nouveau Testament. Celui-ci est généralement constitué des quatre Évangiles canoniques, des Actes des Apôtres, des Épîtres et de l'Apocalypse). La Bible hébraïque se compose quant à elle de trois parties : la Torah (la Loi), les Nevi'im (les Prophètes) et les Ketouvim (les Écrits), dont le titre forme en hébreu l'acronyme TaNaKh (תנ״ך). Les textes constitutifs des différents canons, parfois fragmentaires, sont de nature très variée : récits des origines, textes législatifs, récits historiques, textes sapientiaux, prophétiques, poétiques, hagiographies, épîtres.  Les chercheurs estiment que leur rédaction s’est échelonnée entre les VIIIe et IIe siècles av. J.-C. pour l'Ancien Testament et jusqu'à la fin du Ier siècle, voire le début du IIe siècle, pour le Nouveau Testament. Rédigée en hébreu, la Bible hébraïque a été traduite en grec ancien à Alexandrie entre les IIIe et IIe siècles av. J.-C. Cette traduction, connue sous le nom de Septante, a été utilisée au tournant du Ve siècle par Jérôme de Stridon pour compléter sa propre traduction en latin (la Vulgate), puis, au IXe siècle, par les « apôtres des Slaves » Cyrille et Méthode pour établir une traduction en vieux-slave à l'origine de la Bible orthodoxe. Depuis lors, ces textes ont été traduits à de très nombreuses reprises dans un très grand nombre de langues, faisant de la Bible non seulement l'œuvre la plus célèbre issue de l'Antiquité, mais aussi le plus grand best-seller de l'histoire de l'humanité. Le mot « bible » vient du grec ancien βίϐλος / bíblos, « livre » ou βιϐλίον / biblíon, « papier à écrire »[2] correspondant à l'hébreu sépher[3], « livre », qui a donné βιϐλία / biblía, un substantif au pluriel qui signifie « les livres », soulignant son caractère multiple, qui est traité par les auteurs médiévaux en latin comme un féminin singulier, biblia, avec pour pluriel bibliae[3], par lequel il passe dans la langue française[4]. Le mot « Testament », traduit du latin testamentum, correspond lui au mot grec διαθήκη / diathḗkē, qui signifie « convention » ou « disposition écrite »[5] avant de recouvrir une acception littéraire spécifique au sens de « testament philosophique », un sens que retient la Septante pour traduire le terme hébreu berith, « alliance », qui correspond pourtant davantage au grec sunthêkê[6]. Le déplacement sémantique du terme en tant que « testament » littéraire s'opère chez les auteurs chrétiens dès le IIIe siècle[7], traduit alors par le terme juridique latin testamentum qui est repris ensuite dans toutes les langues[8]."
    
    generate_local_tts(phrase, FILENAME)
    
    if os.path.exists(FILENAME):
        if upload_to_yanshee(FILENAME):
            play_on_yanshee(FILENAME)
    else:
        print("[-] Erreur : Le fichier WAV n'a pas été généré.")
        