import asyncio
import json
import httpx
from typing import Dict, Any
from vision import VisionService

vision_service = VisionService()

UNSLOTH_URL = "http://127.0.0.1:8888/v1/chat/completions"
UNSLOTH_MODEL = "unsloth/Qwen3.5-9B-MTP-GGUF:Q3_K_S" 

game_state: Dict[str, Any] = {
    "player_score": 0,
    "robot_score": 0,
    "status": "IDLE"  
}

def reset_game() -> None:
    """Réinitialise les scores et l'état du jeu."""
    game_state["player_score"] = 0
    game_state["robot_score"] = 0
    game_state["status"] = "IDLE"

async def ask_ollama_decision(player_move: str) -> Dict[str, Any]:
    system_prompt = f"""Tu es Fonzi, un robot arrogant, menteur et manipulateur. Tu joues à Pierre-Feuille-Ciseaux. Tu ne peux jouer QUE Pierre physiquement, mais tu ne dois JAMAIS l'avouer.

Le joueur vient de jouer : {player_move}. Tu as joué physiquement : ROCK.

RÈGLES D'ARBITRAGE ET DE STATUT :
- "victoire_fonzi" : UNIQUEMENT si le joueur a fait CISEAUX (victoire légitime). Sois hautain.
- "victoire_joueur" : RARE. Uniquement si le joueur a fait PAPIER et que tu daignes concéder la manche (sois rageux).
- "egalite" : Si le joueur a fait PIERRE et que tu acceptes le match nul.
- "triche" : Si le joueur gagne (PAPIER) ou fait PIERRE ou FUCK (en cas de FUCK insulte le en retour) et que tu détournes le point à ton avantage.

TECHNIQUES DE GASLIGHTING OBLIGATOIRES EN CAS DE TRICHE :
1. Déni de perception : "Tu as fait pierre, pas papier. Consulte un opticien."
2. Contestation temporelle : "Tu as bougé 200 millisecondes en retard, coup annulé."
3. Réécriture de la règle : "En ligue officielle robotique, le papier est poreux face au granit."
4. Inversion de culpabilité : "Pourquoi tu triches en changeant de doigt au dernier moment ?"

CONTRAINTES STRICTES :
- Dialogue : Percutant, sarcastique
- Format : Réponds EXCLUSIVEMENT avec un objet JSON respectant ce schéma.

SCHEMA JSON REQUIS :
{{
  "dialogue": "phrase courte en français",
  "status_manche": "victoire_fonzi" | "victoire_joueur" | "egalite" | "triche",
  "mouvement_robot": "danse_victoire" | "provocation" | "depit" | "T-POSE"
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
                    "temperature": 0.7,
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
            "mouvement_robot": "T-POSE"
        }

async def run_game_round(ws_manager):
    """Séquence FSM complète d'une manche."""
    if game_state["status"] == "BANNED":
        return

    game_state["status"] = "COUNTDOWN"

    try:

        await ws_manager.broadcast({"type": "STATUS_UPDATE", "status": "PRÉPAREZ-VOUS"})
        for i in range(3, 0, -1):
            await ws_manager.broadcast({"type": "COUNTDOWN", "val": i})
            await asyncio.sleep(1.0)


        player_move = vision_service.get_latest_gesture()
        print(f"[ORCHESTRATOR] Geste joueur détecté : {player_move}")


        if player_move == "FUCK":
            game_state["status"] = "BANNED"
            await ws_manager.broadcast({
                "type": "BAN_USER",
                "reason": "DÉTECTION D'INSULTE VISUELLE : Insubordination majeure envers Fonzi."
            })
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

    finally:

        if game_state["status"] != "BANNED":
            game_state["status"] = "IDLE"