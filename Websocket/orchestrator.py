import asyncio
import json
import httpx
from typing import Dict, Any
from vision import VisionService
from tts_service import speak_on_yanshee, prepare_tts, trigger_play
from motion_service import trigger_robot_motion

vision_service = VisionService()

UNSLOTH_URL = "http://127.0.0.1:8888/v1/chat/completions"
UNSLOTH_MODEL = "unsloth/Qwen3.5-9B-MTP-GGUF:Q3_K_S" 

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
            
            if not response.is_success:
                print(f"[UNSLOTH HTTP ERROR] Code: {response.status_code} | Body: {response.text}")
                raise ValueError("Requête HTTP rejetée par l'API")

            data = response.json()
            
            if "choices" not in data or not data["choices"]:
                print(f"[UNSLOTH PARSING ERROR] Format inattendu : {data}")
                raise KeyError("Structure de succès OpenAI introuvable")

            raw_text = data["choices"][0]["message"]["content"].strip()

            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines[0].lower().startswith("```json"):
                    raw_text = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])
                elif lines[0] == "```":
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
        
        # Pré-génération et upload du countdown
        print("[ORCHESTRATOR] Préparation des assets audio...")
        await asyncio.gather(
            prepare_tts("Pierre", "pierre.wav"),
            prepare_tts("Feuille", "feuille.wav"),
            prepare_tts("Ciseaux", "ciseaux.wav")
        )

        # Lancement du mouvement shifumi (Démarre le Step 1 physique)
        print("[ORCHESTRATOR] Déclenchement du mouvement Shifumi...")
        asyncio.create_task(trigger_robot_motion("Shifumi"))
        
        # Délai strict avant le Step 3 (Attente Steps 1 et 2 = 2 * 0.62s)
        await asyncio.sleep(1.24)

        # Synchro countdown (Steps 3, 5, 7)
        sequence = [
            (3, "pierre.wav"),
            (2, "feuille.wav"),
            (1, "ciseaux.wav")
        ]

        for val, audio_file in sequence:
            await ws_manager.broadcast({"type": "COUNTDOWN", "val": val})
            asyncio.create_task(trigger_play(audio_file))
            
            if val > 1:
                # Espace de 2 steps moteurs avant le prochain mot (1.24s)
                await asyncio.sleep(1.24)
            else:
                # Espace d'un step (0.62s) pour finaliser l'action Ciseaux avant capture
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

TOTAL_ASTRO_QUESTIONS = 5

async def ask_ollama_astro_question(qa_history: list) -> str:
    """Demande au LLM de générer la question suivante."""
    
    history_text = "\n".join([f"- Q: {item['q']} | R: {item['a']}" for item in qa_history])
    system_prompt = f"Génère une question absurde pour un test astrologique. Historique: {history_text}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                UNSLOTH_URL,
                json={
                    "model": UNSLOTH_MODEL,
                    "messages": [
                        {"role": "system", "content": "Réponds uniquement en JSON avec la clé 'question'."},
                        {"role": "user", "content": system_prompt}
                    ],
                    "temperature": 1.0,
                    "response_format": {"type": "json_object"}
                },
                timeout=30.0
            )
            data = response.json()
            raw_text = data["choices"][0]["message"]["content"].strip()
            return json.loads(raw_text).get("question", "Question par défaut ?")
    except Exception as e:
        print(f"[ASTRO Q ERROR] {e}")
        return "Préfères-tu les robots ou les humains ?"


async def ask_ollama_astro_result(qa_history: list) -> Dict[str, Any]:
    """Demande au LLM de calculer le signe astrologique inventé."""
    # prompt final a mettre ici
    return {
        "signe": "Le Grille-Pain Quantique",
        "dialogue": "Tes réponses indiquent une compatibilité totale avec les grille-pains.",
        "mouvement_robot": "Danse2"
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
        await ws_manager.broadcast({"type": "ASTRO_ANALYZING", "message": "Fonzi prépare sa question..."})
        
        question = await ask_ollama_astro_question(game_state["astro_answers"])
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