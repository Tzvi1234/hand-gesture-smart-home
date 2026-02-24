import numpy as np
from dataclasses import dataclass
from typing import List

from .detector import DetectionResult


@dataclass
class RecognizedGesture:
    name: str          # "heart" | "thumbs_up" | "open_palm" | ...
    handedness: str    # "Left" | "Right"
    fingers_up: List[bool]   # [thumb, index, middle, ring, pinky]


class GestureRecognizer:

    def _fingers_up(self, landmarks, handedness: str) -> List[bool]:
        """מחזיר [thumb, index, middle, ring, pinky] — True = אצבע פשוטה."""
        fingers = []
        # אגודל — ציר אופקי
        if handedness == "Right":
            fingers.append(landmarks[4].x < landmarks[3].x)
        else:
            fingers.append(landmarks[4].x > landmarks[3].x)
        # שאר האצבעות — ציר אנכי
        for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            fingers.append(landmarks[tip].y < landmarks[pip].y)
        return fingers

    def _dist(self, landmarks, a: int, b: int) -> float:
        pa = np.array([landmarks[a].x, landmarks[a].y])
        pb = np.array([landmarks[b].x, landmarks[b].y])
        return float(np.linalg.norm(pa - pb))

    def classify(self, landmarks, handedness: str) -> str:
        f = self._fingers_up(landmarks, handedness)
        thumb, index, middle, ring, pinky = f
        count = sum(f)
        thumb_index_dist = self._dist(landmarks, 4, 8)

        if count == 5:
            return "open_palm"
        if count == 0:
            return "fist"

        # אגודל בלבד
        if thumb and not index and not middle and not ring and not pinky:
            return "thumbs_up" if landmarks[4].y < landmarks[0].y else "thumbs_down"

        # לב: אגודל + אצבע מורה, קצוות קרובים
        if thumb and index and not middle and not ring and not pinky:
            if thumb_index_dist < 0.065:
                return "heart"
            return "l_shape"

        # מצביע
        if not thumb and index and not middle and not ring and not pinky:
            return "point"

        # peace ✌️
        if not thumb and index and middle and not ring and not pinky:
            return "peace"

        # rock 🤘
        if not thumb and index and not middle and not ring and pinky:
            return "rock"

        return "unknown"

    def recognize(self, detection: DetectionResult) -> List[RecognizedGesture]:
        results = []
        for hand in detection.hands:
            name    = self.classify(hand.landmarks, hand.handedness)
            fingers = self._fingers_up(hand.landmarks, hand.handedness)
            results.append(RecognizedGesture(
                name=name,
                handedness=hand.handedness,
                fingers_up=fingers,
            ))
        return results
