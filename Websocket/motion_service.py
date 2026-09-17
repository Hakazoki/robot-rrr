import httpx
from typing import Dict, Any

ROBOT_IP: str = "192.168.0.150"
MOTION_API_URL: str = f"http://{ROBOT_IP}:9090/v1/motions"

async def trigger_robot_motion(motion_name: str) -> None:
    """Déclenche un mouvement physique sur le robot en asynchrone."""
    if not motion_name:
        return
        
    payload: Dict[str, Any] = {
        "operation": "start",
        "motion": {
            "name": motion_name,
            "repeat": 1,
            "direction": "left",
            "speed": "normal"
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(MOTION_API_URL, json=payload, timeout=5.0)
            if not response.is_success:
                print(f"[MOTION ERREUR API] Code: {response.status_code} | Body: {response.text}")
    except httpx.RequestError as e:
        print(f"[MOTION ERREUR RESEAU] {e}")