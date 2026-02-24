import os
import time
import urllib.request
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

MODEL_PATH = "hand_landmarker.task"
MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)

# חיבורים בין נקודות היד (אינדקסים של MediaPipe)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),          # אגודל
    (0, 5), (5, 6), (6, 7), (7, 8),           # אצבע מורה
    (5, 9), (9, 10), (10, 11), (11, 12),      # אמה
    (9, 13), (13, 14), (14, 15), (15, 16),    # קמיצה
    (13, 17), (17, 18), (18, 19), (19, 20),   # זרת
    (0, 17),                                   # כף יד
]


@dataclass
class HandLandmarks:
    landmarks: list    # 21 NormalizedLandmark
    handedness: str    # 'Left' | 'Right'
    confidence: float


@dataclass
class DetectionResult:
    hands: List[HandLandmarks] = field(default_factory=list)


class HandDetector:

    def __init__(self, max_hands: int = 2, detection_confidence: float = 0.7,
                 tracking_confidence: float = 0.5):
        if not os.path.exists(MODEL_PATH):
            print("מוריד מודל זיהוי יד (חד-פעמי, ~29MB)...")
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
            print("הורדה הושלמה.")

        base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
        options = mp_vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=max_hands,
            min_hand_detection_confidence=detection_confidence,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=tracking_confidence,
            running_mode=mp_vision.RunningMode.VIDEO,
        )
        self._landmarker  = mp_vision.HandLandmarker.create_from_options(options)
        self._start_time  = time.perf_counter()

    def detect(self, frame: np.ndarray) -> DetectionResult:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        timestamp_ms = int((time.perf_counter() - self._start_time) * 1000)
        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)

        detection = DetectionResult()
        if result.hand_landmarks and result.handedness:
            for landmarks, handedness in zip(result.hand_landmarks, result.handedness):
                detection.hands.append(HandLandmarks(
                    landmarks=landmarks,
                    handedness=handedness[0].category_name,   # 'Left' | 'Right'
                    confidence=handedness[0].score,
                ))

        return detection

    def close(self):
        self._landmarker.close()
