import cv2
import math
import threading
import time
from collections import deque
from typing import Any, List, Optional, Tuple

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np

# Config réseau
ROBOT_IP: str = "192.168.0.150"
STREAM_URL: str = f"http://{ROBOT_IP}:8080/?action=stream"
MODEL_PATH: str = "hand_landmarker.task"

# Topologie des os de la main
HAND_CONNECTIONS: List[Tuple[int, int]] = [
    (0, 1), (1, 2), (2, 3), (3, 4),        # Pouce
    (0, 5), (5, 6), (6, 7), (7, 8),        # Index
    (5, 9), (9, 10), (10, 11), (11, 12),   # Majeur
    (9, 13), (13, 14), (14, 15), (15, 16), # Annulaire
    (13, 17), (17, 18), (18, 19), (19, 20),# Auriculaire
    (0, 17)                                # Base de paume
]


class FreshFrameReader:
    def __init__(self, src: str) -> None:
        self.cap: cv2.VideoCapture = cv2.VideoCapture(src)
        self.ret: bool = False
        self.frame: Optional[np.ndarray] = None
        self.running: bool = True
        self.lock: threading.Lock = threading.Lock()
        self.thread: threading.Thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _update(self) -> None:
        while self.running:
            ret, frame = self.cap.read()
            with self.lock:
                self.ret = ret
                self.frame = frame
            if not ret:
                time.sleep(0.01)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        with self.lock:
            return self.ret, self.frame.copy() if self.frame is not None else None

    def release(self) -> None:
        self.running = False
        self.thread.join(timeout=1.0)
        self.cap.release()


class GestureStabilizer:
    def __init__(self, window_size: int = 7) -> None:
        self.history: deque[str] = deque(maxlen=window_size)

    def update(self, raw_gesture: str) -> str:
        if raw_gesture not in ("UNKNOWN", "AUCUNE MAIN"):
            self.history.append(raw_gesture)
        if not self.history:
            return raw_gesture
        return max(set(self.history), key=self.history.count)


def get_euclidean_distance_3d(p1: Any, p2: Any) -> float:
    """Normalisation 3d."""
    return math.sqrt(
        (p1.x - p2.x) ** 2 + 
        (p1.y - p2.y) ** 2 + 
        (p1.z - p2.z) ** 2
    )


def is_finger_extended(wrist: Any, mcp: Any, pip: Any, tip: Any) -> bool:
    """
    Vérifie si un doigt est déplié indépendamment de la rotation de la main.
    Condition : distance tip->wrist > distance pip->wrist avec coefficient de marge.
    """
    dist_tip_wrist: float = get_euclidean_distance_3d(tip, wrist)
    dist_pip_wrist: float = get_euclidean_distance_3d(pip, wrist)
    dist_mcp_wrist: float = get_euclidean_distance_3d(mcp, wrist)

    return dist_tip_wrist > (dist_pip_wrist * 1.15) and dist_tip_wrist > dist_mcp_wrist


def classify_gesture_advanced(landmarks: List[Any]) -> str:
    """
    Classification invariante par rotation (Rock / Paper / Scissors).
    Le pouce est exclu des calculs pour éliminer les faux positifs d'anatomie.
    """
    wrist: Any = landmarks[0]

    # Détection de l'état des 4 doigts majeurs
    index_open: bool = is_finger_extended(wrist, landmarks[5], landmarks[6], landmarks[8])
    middle_open: bool = is_finger_extended(wrist, landmarks[9], landmarks[10], landmarks[12])
    ring_open: bool = is_finger_extended(wrist, landmarks[13], landmarks[14], landmarks[16])
    pinky_open: bool = is_finger_extended(wrist, landmarks[17], landmarks[18], landmarks[20])

    opened_fingers_count: int = sum([index_open, middle_open, ring_open, pinky_open])

    # 1. PIERRE : Poing fermé
    if opened_fingers_count == 0:
        return "ROCK"

    # 2. CISEAUX : Index et Majeur ouverts uniquement
    if index_open and middle_open and not ring_open and not pinky_open:
        return "SCISSORS"

    # 3. FEUILLE : Au moins 3 doigts ouverts simultanément
    if opened_fingers_count >= 3:
        return "PAPER"

    # 4. MIDDLE FINGER : le middle finger ouvert et c'est tout bro
    if middle_open and not index_open and not ring_open and not pinky_open:
        return "FUCK"

    return "UNKNOWN"


def draw_landmarks_on_image(image: np.ndarray, landmarks: List[Any]) -> np.ndarray:
    """Rendu manuel des points et liaisons du squelette."""
    height, width, _ = image.shape
    coords: List[Tuple[int, int]] = [
        (int(point.x * width), int(point.y * height)) for point in landmarks
    ]

    for start_idx, end_idx in HAND_CONNECTIONS:
        cv2.line(image, coords[start_idx], coords[end_idx], (0, 255, 0), 2)
    for x, y in coords:
        cv2.circle(image, (x, y), 4, (0, 0, 255), -1)

    return image

class VisionService:
    def __init__(self, stream_url: str = STREAM_URL, model_path: str = MODEL_PATH):
        self.stream_url = stream_url
        self.model_path = model_path
        self.running = False
        self.current_gesture = "AUCUNE MAIN"
        self.stabilizer = GestureStabilizer(window_size=7)
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._run_detection, daemon=True)
        self._thread.start()

    def _run_detection(self):
        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=1,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.5,
            running_mode=vision.RunningMode.IMAGE
        )
        detector = vision.HandLandmarker.create_from_options(options)
        stream = FreshFrameReader(self.stream_url)

        try:
            while self.running:
                ret, frame = stream.read()
                if not ret or frame is None:
                    time.sleep(0.01)
                    continue

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                detection_result = detector.detect(mp_image)

                raw_gesture = "AUCUNE MAIN"
                if detection_result.hand_landmarks:
                    landmarks = detection_result.hand_landmarks[0]
                    raw_gesture = classify_gesture_advanced(landmarks)

                self.current_gesture = self.stabilizer.update(raw_gesture)
                time.sleep(0.01)
        finally:
            detector.close()
            stream.release()

    def get_latest_gesture(self) -> str:
        return self.current_gesture

    def stop(self):
        self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

if __name__ == "__main__":
    print("Démarrage du test autonome du VisionService...")
    service = VisionService()
    service.start()
    
    try:
        while True:
            geste = service.get_latest_gesture()
            print(f"[TEST VISION] Geste détecté en continu : {geste}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nArrêt du service...")
        service.stop()