import time
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple

from .detector import DetectionResult, HandLandmarks
from ..config import GestureConfig


@dataclass
class RecognizedGesture:
    name: str
    display_name: str
    action: Optional[str]
    description: Optional[str]
    confidence: float
    handedness: str
    fingers_up: List[bool]   # [thumb, index, middle, ring, pinky]
    landmarks: list


class GestureRecognizer:
    """
    Classifies hand gestures from MediaPipe 21-point hand landmarks.

    Landmark indices (MediaPipe convention):
        0: WRIST
        1-4: THUMB  (CMC, MCP, IP, TIP)
        5-8: INDEX  (MCP, PIP, DIP, TIP)
        9-12: MIDDLE (MCP, PIP, DIP, TIP)
        13-16: RING  (MCP, PIP, DIP, TIP)
        17-20: PINKY (MCP, PIP, DIP, TIP)
    """

    FINGER_NAMES = ["Thumb", "Index", "Middle", "Ring", "Pinky"]

    def __init__(self, config: Dict[str, GestureConfig]):
        self.config = config
        self._last_action_time: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------

    def get_fingers_up(self, landmarks, handedness: str) -> List[bool]:
        """
        Returns [thumb, index, middle, ring, pinky] — True = extended.

        Because the frame is flipped (mirror), the handedness label is
        already swapped by MediaPipe, so we can compare x-coords directly:
          Right hand (appears on user's right): thumb tip x < thumb IP x
          Left  hand (appears on user's left):  thumb tip x > thumb IP x
        """
        fingers: List[bool] = []

        # Thumb — horizontal axis
        if handedness == "Right":
            fingers.append(landmarks[4].x < landmarks[3].x)
        else:
            fingers.append(landmarks[4].x > landmarks[3].x)

        # Index → Pinky — vertical axis (lower y = higher on screen)
        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            fingers.append(landmarks[tip].y < landmarks[pip].y)

        return fingers

    def _tip_distance(self, landmarks, a: int, b: int) -> float:
        """Normalised Euclidean distance between two landmarks."""
        pa = np.array([landmarks[a].x, landmarks[a].y])
        pb = np.array([landmarks[b].x, landmarks[b].y])
        return float(np.linalg.norm(pa - pb))

    # ------------------------------------------------------------------
    # Gesture classification
    # ------------------------------------------------------------------

    def classify(self, landmarks, handedness: str) -> Tuple[str, float]:
        """Return (gesture_name, confidence) for one hand."""
        f = self.get_fingers_up(landmarks, handedness)
        thumb, index, middle, ring, pinky = f
        count = sum(f)

        thumb_index_dist = self._tip_distance(landmarks, 4, 8)

        # ---- 5 fingers -----------------------------------------------
        if count == 5:
            return "open_palm", 0.95

        # ---- 0 fingers -----------------------------------------------
        if count == 0:
            return "fist", 0.95

        # ---- Thumb only ----------------------------------------------
        if thumb and not index and not middle and not ring and not pinky:
            # Thumb tip above wrist → thumbs up, else thumbs down
            if landmarks[4].y < landmarks[0].y:
                return "thumbs_up", 0.90
            return "thumbs_down", 0.85

        # ---- Index only (pointing) -----------------------------------
        if not thumb and index and not middle and not ring and not pinky:
            return "point", 0.90

        # ---- Index + Middle (peace) ----------------------------------
        if not thumb and index and middle and not ring and not pinky:
            return "peace", 0.90

        # ---- Index + Pinky (rock on) ---------------------------------
        if not thumb and index and not middle and not ring and pinky:
            return "rock", 0.90

        # ---- Index + Middle + Ring (three fingers) -------------------
        if not thumb and index and middle and ring and not pinky:
            return "three_fingers", 0.88

        # ---- Index + Middle + Ring + Pinky (four fingers) ------------
        if not thumb and index and middle and ring and pinky:
            return "four_fingers", 0.88

        # ---- OK sign: thumb + index tips touching, others up ---------
        if middle and ring and pinky and thumb_index_dist < 0.055:
            return "ok", 0.85

        # ---- Finger heart: thumb + index up, tips touching -----------
        if thumb and index and not middle and not ring and not pinky:
            if thumb_index_dist < 0.065:
                return "heart", 0.90
            return "l_shape", 0.80

        return "unknown", 0.50

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def can_trigger(self, gesture_name: str, cooldown: float) -> bool:
        last = self._last_action_time.get(gesture_name, 0.0)
        return (time.time() - last) >= cooldown

    def mark_triggered(self, gesture_name: str):
        self._last_action_time[gesture_name] = time.time()

    def recognize(self, detection: DetectionResult) -> List[RecognizedGesture]:
        """Recognise gestures for every detected hand."""
        results: List[RecognizedGesture] = []

        for hand in detection.hands:
            name, confidence = self.classify(hand.landmarks, hand.handedness)
            cfg = self.config.get(name)

            results.append(
                RecognizedGesture(
                    name=name,
                    display_name=cfg.name if cfg else name.replace("_", " ").title(),
                    action=cfg.action if cfg else None,
                    description=cfg.description if cfg else None,
                    confidence=confidence,
                    handedness=hand.handedness,
                    fingers_up=self.get_fingers_up(hand.landmarks, hand.handedness),
                    landmarks=hand.landmarks,
                )
            )

        return results
