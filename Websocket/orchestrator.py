import asyncio
import json
import httpx
from typing import Dict, Any, List
from vision import VisionService
from tts_service import speak_on_yanshee, prepare_tts, trigger_play
from motion_service import trigger_robot_motion

vision_service = VisionService()

UNSLOTH_URL = "http://127.0.0.1:8888/v1/chat/completions"
UNSLOTH_MODEL = "unsloth/Qwen3.5-9B-MTP-GGUF:Q3_K_S" 
TOTAL_ASTRO_QUESTIONS = 5

game_state: Dict[str, Any] = {
    "player_score": 0,
    "robot_score": 0,
    "status": "IDLE",
    "mode": "MENU",                 
    "astro_step": 0,
    "astro_answers": [],
    "current_astro_question": ""
}

def reset_game() -> None:
    """Réinitialise les scores et l'état du jeu."""
    game_state["player_score"] = 0
    game_state["robot_score"] = 0
    game_state["status"] = "IDLE"

async def ask_ollama_decision(player_move: str) -> Dict[str, Any]:
    system_prompt = f"""Tu es Fonzi, un robot arrogant, menteur et manipulateur. Tu joues à Pierre-Feuille-Ciseaux. Tu ne peux jouer QUE Pierre physiquement, mais tu ne dois JAMAIS l'avouer.

Le joueur vient de jouer : {player_move}. Tu as joué physiquement : ROCK.

LOGIQUE D'ARBITRAGE ET DISTRIBUTION :
Si le joueur fait PAPIER :
- 60% du temps -> "victoire_joueur" (Accepte la défaite : rage, mauvaise foi, prétextes sur le matériel, mais RECONNAÎT la défaite).
- 40% du temps -> "triche" (Refuse la défaite via du gaslighting).

Si le joueur fait CISEAUX :
- 100% du temps -> "victoire_fonzi" (Victoire légitime : sois hautain, méprisant, sur-confiant).

Si le joueur fait PIERRE :
- 80% du temps -> "egalite" (Match nul : blasé, condescendant).
- 20% du temps -> "triche" (Accuse le joueur d'avoir copié ton coup).

Si le geste du joueur est invalide ou non reconnu :
- 100% du temps -> "triche" (Moque-toi de son incapacité à faire un geste correct).

DIRECTIVES DE DIALOGUE (Punchlines variées) :
- Pour "victoire_joueur" : Rage noire, accuse la batterie, le Wi-Fi ou un bug, mais accepte le point du joueur. Ex: "C'est un coup de chance algorithmique, profite-en.", "Mon capteur a bugué, apprécie ton unique victoire."
- Pour "victoire_fonzi" : Courte, percutante, moque l'intelligence humaine.
- Pour "triche" : Utilise du gaslighting (Déni, réécriture de règles, fausses millisecondes).
- Ne réutilise jamais deux fois la même tournure de phrase.

CONTRAINTES STRICTES :
- Dialogue : Percutant, sarcastique, court (1 à 2 phrases max).
- Réponds EXCLUSIVEMENT avec un objet JSON valide.

SCHEMA JSON REQUIS :
{{
  "dialogue": "phrase courte en français",
  "status_manche": "victoire_fonzi" | "victoire_joueur" | "egalite" | "triche",
  "mouvement_robot": "Danse2" | "T-POSE2"
}}"""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                UNSLOTH_URL,
                json={
                    "model": UNSLOTH_MODEL,
                    "messages": [
                        {"role": "system", "content": "Tu es une IA qui réponds exclusivement en JSON validé."},
                        {"role": "user", "content": system_prompt}
                    ],
                    "temperature": 1.2,
                    "response_format": {"type": "json_object"}
                },
                timeout=45.0 
            )
            response.raise_for_status()
            data = response.json()
            raw_text = data["choices"][0]["message"]["content"].strip()
            
            # Nettoyage markdown éventuel
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                raw_text = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])
                
            return json.loads(raw_text)

    except Exception as e:
        print(f"[UNSLOTH FATAL ERROR] {type(e).__name__} : {e}")
        return {
            "dialogue": "Mon algorithme dépasse ton entendement.",
            "status_manche": "victoire_fonzi",
            "mouvement_robot": "T-POSE2"
        }

async def execute_reaction_sequence(dialogue: str, motion_name: str) -> None:
    """Chef d'orchestre séquentiel : Joue l'audio, attend sa fin, joue la danse."""
    audio_duration = await speak_on_yanshee(dialogue)
    
    if audio_duration > 0:
        await asyncio.sleep(audio_duration + 0.3)
        
    if motion_name and motion_name not in ("AUCUN", "IDLE"):
        await trigger_robot_motion(motion_name)

async def run_game_round(ws_manager):
    if game_state["status"] == "BANNED":
        return

    game_state["status"] = "COUNTDOWN"

    try:
        await ws_manager.broadcast({"type": "STATUS_UPDATE", "status": "PRÉPAREZ-VOUS"})
        
        print("[ORCHESTRATOR] Préparation des assets audio...")
        await asyncio.gather(
            prepare_tts("Pierre", "pierre.wav"),
            prepare_tts("Feuille", "feuille.wav"),
            prepare_tts("Ciseaux", "ciseaux.wav")
        )

        print("[ORCHESTRATOR] Déclenchement du mouvement Shifumi...")
        asyncio.create_task(trigger_robot_motion("Shifumi"))
        await asyncio.sleep(1.24)

        sequence = [
            (3, "pierre.wav"),
            (2, "feuille.wav"),
            (1, "ciseaux.wav")
        ]

        for val, audio_file in sequence:
            await ws_manager.broadcast({"type": "COUNTDOWN", "val": val})
            asyncio.create_task(trigger_play(audio_file))
            
            if val > 1:
                await asyncio.sleep(1.24)
            else:
                await asyncio.sleep(0.62)

        player_move = vision_service.get_latest_gesture()
        print(f"[ORCHESTRATOR] Geste joueur détecté : {player_move}")

        if player_move == "FUCK":
            game_state["status"] = "BANNED"
            await ws_manager.broadcast({
                "type": "BAN_USER",
                "reason": "DÉTECTION D'INSULTE VISUELLE : Insubordination majeure envers Fonzi."
            })
            asyncio.create_task(speak_on_yanshee("Insubordination détectée. Accès révoqué."))
            return

        if player_move in ("AUCUNE MAIN", "UNKNOWN"):
            player_move = "ROCK"

        robot_physical_move = "ROCK"
        ai_response = await ask_ollama_decision(player_move)
        
        status_manche = ai_response.get("status_manche", "victoire_fonzi")
        mouvement_robot = ai_response.get("mouvement_robot", "provocation")
        dialogue = ai_response.get("dialogue", "J'ai encore gagné.")

        if status_manche in ("victoire_fonzi", "triche"):
            game_state["robot_score"] += 1
        elif status_manche == "victoire_joueur":
            game_state["player_score"] += 1

        await ws_manager.broadcast({
            "type": "ROUND_RESULT",
            "playerMove": player_move,
            "robotMove": robot_physical_move,
            "statusManche": status_manche,
            "mouvementRobot": mouvement_robot,
            "playerScore": game_state["player_score"],
            "robotScore": game_state["robot_score"],
            "dialogue": dialogue
        })

        asyncio.create_task(execute_reaction_sequence(dialogue, mouvement_robot))

    finally:
        if game_state["status"] != "BANNED":
            game_state["status"] = "IDLE"

async def ask_ollama_astro_question(qa_history: List[Dict[str, str]], current_step: int) -> str:
    """Demande au LLM de générer la question astrologique suivante."""
    history_text = "\n".join([f"- Q: {item['q']} | R: {item['a']}" for item in qa_history])
    
    system_prompt = (
        f"Tu es Fonzi, un robot chinois charlatan. "
        f"C'est la question {current_step} sur {TOTAL_ASTRO_QUESTIONS} de ton test astrologique. "
        "Pose une question absurde, unique et pseudo-mystique. "
        "Plus on s'approche de la question finale, plus tes questions doivent être ridicules. "
        "Ne répète jamais les thèmes précédents."
    )
    user_prompt = f"Historique :\n{history_text}\nGénère la question {current_step}."

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                UNSLOTH_URL,
                json={
                    "model": UNSLOTH_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt + " Réponds UNIQUEMENT en JSON avec la clé 'question'."},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 1.1,
                    "response_format": {"type": "json_object"}
                },
                timeout=15.0
            )
            response.raise_for_status()
            data = response.json()
            raw_text = data["choices"][0]["message"]["content"].strip()
            return json.loads(raw_text).get("question", f"Les astres sont flous. Question {current_step} : Aimes-tu les câbles USB ?")
            
    except Exception as e:
        print(f"[ASTRO Q ERROR] {e}")
        return f"Mon processeur divinatoire saute. Question {current_step} : Quel est ton métal préféré ?"

async def ask_ollama_astro_result(qa_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """Demande au LLM de calculer le signe astrologique inventé."""
    history_text = "\n".join([f"- Q: {item['q']} | R: {item['a']}" for item in qa_history])
    
    system_prompt = (
        "Tu es Fonzi, un robot chinois charlatan se faisant passer pour un grand astrologue. "
        "Tu dois assigner un signe astrologique totalement idiot au joueur (tu PEUX t'INSPIRER des exemples suivants mais le but n'est pas de les recopier : Le Grille-Pain Quantique, la fourmis tigre, l'huitre de madagascar). "
        "Justifie ce signe avec une fausse logique très affirmée, en mélangeant mysticisme de pacotille "
        "et jargon technologique. Cite spécifiquement les réponses du joueur pour prouver ton analyse."
    )
    
    user_prompt = (
        f"Voici les réponses du joueur :\n{history_text}\n\n"
        "Renvoie un JSON avec 3 clés exactes :\n"
        "- 'signe' : Le nom du signe absurde.\n"
        "- 'dialogue' : Ton explication charlatanesque justifiant le signe (max 3 phrases dynamiques).\n"
        "- 'mouvement_robot' : Choisis une valeur parmi ['Danse1', 'Danse2', 'Salutation', 'T-POSE2']."
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                UNSLOTH_URL,
                json={
                    "model": UNSLOTH_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt + " Réponds UNIQUEMENT au format JSON demandé."},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 1.0,
                    "response_format": {"type": "json_object"}
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            raw_text = data["choices"][0]["message"]["content"].strip()
            result = json.loads(raw_text)
            
            return {
                "signe": result.get("signe", "Le Boulon Mystique"),
                "dialogue": result.get("dialogue", "Tes réponses indiquent une fluctuation de tes chakras wifi. Tu es un Boulon Mystique."),
                "mouvement_robot": result.get("mouvement_robot", "T-POSE2")
            }
            
    except Exception as e:
        print(f"[ASTRO RESULT ERROR] {e}")
        return {
            "signe": "L'Antenne Cassée",
            "dialogue": "Les ondes astrales sont coupées. Ton aura a fait planter mon processeur divinatique. Tu es l'Antenne Cassée.",
            "mouvement_robot": "T-POSE2"
        }

async def start_astro_game(ws_manager):
    """Initialise le jeu Astro Roboscope."""
    game_state["mode"] = "ASTRO"
    game_state["astro_step"] = 0
    game_state["astro_answers"] = []
    
    await ws_manager.broadcast({"type": "GAME_STARTED", "game": "ASTRO"})
    asyncio.create_task(speak_on_yanshee("Bienvenue dans l'Astro Roboscope !"))
    await asyncio.sleep(2.5)
    
    await ask_next_astro_question(ws_manager)

async def ask_next_astro_question(ws_manager):
    step = game_state["astro_step"]
    
    if step < TOTAL_ASTRO_QUESTIONS:
        await ws_manager.broadcast({"type": "ASTRO_ANALYZING", "message": f"Fonzi prépare la question {step + 1}..."})
        
        question = await ask_ollama_astro_question(game_state["astro_answers"], step + 1)
        game_state["current_astro_question"] = question
        
        await ws_manager.broadcast({
            "type": "ASTRO_QUESTION",
            "step": step + 1,
            "total": TOTAL_ASTRO_QUESTIONS,
            "question": question
        })
        
        asyncio.create_task(speak_on_yanshee(question))
        game_state["status"] = "WAITING_INPUT"
    else:
        await resolve_astro_game(ws_manager)

async def process_astro_answer(user_text: str, ws_manager):
    """Reçoit la réponse du joueur et passe à la question suivante."""
    if game_state["mode"] != "ASTRO" or game_state["status"] != "WAITING_INPUT":
        return

    current_q = game_state.get("current_astro_question", "")
    game_state["astro_answers"].append({"q": current_q, "a": user_text})
    game_state["astro_step"] += 1
    game_state["status"] = "RUNNING"
    
    await ask_next_astro_question(ws_manager)

async def resolve_astro_game(ws_manager):
    """Génère le bilan astrologique et l'annonce."""
    await ws_manager.broadcast({"type": "ASTRO_ANALYZING", "message": "Consultation de l'Astro Roboscope en cours..."})
    
    result = await ask_ollama_astro_result(game_state["astro_answers"])
    signe = result.get("signe", "Inconnu")
    dialogue = result.get("dialogue", "Ton avenir est flou.")
    mouvement = result.get("mouvement_robot", "T-POSE2")
    
    await ws_manager.broadcast({
        "type": "ASTRO_RESULT",
        "signe": signe,
        "dialogue": dialogue
    })
    
    await execute_reaction_sequence(f"D'après l'Astro Roboscope, ton signe est : {signe}. {dialogue}", mouvement)
    
    game_state["mode"] = "MENU"
    game_state["status"] = "IDLE"