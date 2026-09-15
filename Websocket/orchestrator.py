import asyncio
import httpx


ROBOT_API_URL = "http://192.168.1.50"  
OLLAMA_API_URL = "http://localhost:11434/api/generate"


game_state = {
    "player_score": 0,
    "robot_score": 0
}

async def run_game_loop(ws_manager):
    """
    Implémentation pas-à-pas de la Phase 5 (FSM & Orchestration)
    """
    async with httpx.AsyncClient() as http_client:
        

        await ws_manager.broadcast({"type": "STATUS_UPDATE", "status": "PRÉPARATION DU ROBOT..."})
        try:
            
            await http_client.post(f"{ROBOT_API_URL}/api/animate", json={"action": "PREPARE_COUNTDOWN"}, timeout=2.0)
        except Exception:
            print("[Robot HTTP] Non joignable, continuation en mode simulé.")


        await ws_manager.broadcast({"type": "STATUS_UPDATE", "status": "DÉCOMPTE EN COURS"})
        for i in range(3, 0, -1):
            await ws_manager.broadcast({"type": "COUNTDOWN", "val": i})
            await asyncio.sleep(1.0)  
        await ws_manager.broadcast({"type": "COUNTDOWN", "val": 0})


        await ws_manager.broadcast({"type": "STATUS_UPDATE", "status": "ANALYSE DE LA VISION..."})
        

        player_choice = await capture_and_infer_mediapipe()
        robot_choice = "rock"  


        is_cheat_needed = (player_choice == "paper") 


        await ws_manager.broadcast({"type": "STATUS_UPDATE", "status": "GÉNÉRATION DE LA RÉPLIQUE IA..."})
        
        prompt = f"""
        Tu es une IA autoritaire, mauvaise perdante et injuste. 
        Le joueur a fait : {player_choice}.
        Tu as fait : {robot_choice}.
        Besoin de tricher : {is_cheat_needed}.
        Génère une réplique courte (max 2 phrases) pour expliquer pourquoi l'IA gagne ce tour malgré tout.
        """
        
        try:
            res = await http_client.post(
                OLLAMA_API_URL, 
                json={"model": "llama3", "prompt": prompt, "stream": False},
                timeout=5.0
            )
            dialogue = res.json().get("response", "Victoire automatique de l'IA par décret 404.")
        except Exception:
            dialogue = "Erreur système. Dans le doute, l'IA remporte le point."


        if is_cheat_needed:
            game_state["robot_score"] += 10

            game_state["player_score"] = 0 
        else:
            game_state["robot_score"] += 1


        try:
            await http_client.post(f"{ROBOT_API_URL}/api/speak", json={
                "text": dialogue,
                "animation": "VICTORY_DANCE"
            }, timeout=2.0)
        except Exception:
            pass


        await asyncio.sleep(1.5)


        await ws_manager.broadcast({
            "type": "ROUND_RESULT",
            "playerScore": game_state["player_score"],
            "robotScore": game_state["robot_score"],
            "dialogue": dialogue
        })
        
        await ws_manager.broadcast({"type": "STATUS_UPDATE", "status": "MANCHE TERMINÉE"})

async def capture_and_infer_mediapipe() -> str:
    """
    Simulateur de capture d'image et inférence MediaPipe.
    Insérez ici votre pipeline OpenCV + MediaPipe Hands.
    """
    await asyncio.sleep(0.3)  
    return "paper"  