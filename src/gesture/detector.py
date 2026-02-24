import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
from mediapipe.python.solutions import hands as mp_hands_module
from mediapipe.python.solutions import drawing_utils as mp_drawing_utils
from mediapipe.python.solutions import drawing_styles as mp_drawing_styles


@dataclass
class HandLandmarks:
    landmarks: list       # 21 MediaPipe landmarks
    handedness: str       # 'Left' or 'Right'
    confidence: float


@dataclass
class DetectionResult:
    hands: List[HandLandmarks] = field(default_factory=list)
    raw_results: object = None   # Raw MediaPipe results (for drawing utilities)
    frame_rgb: Optional[np.ndarray] = None


class HandDetector:
    """Detects hands and extracts landmarks using MediaPipe Hands."""

    def __init__(
        self,
        max_hands: int = 2,
        detection_confidence: float = 0.7,
        tracking_confidence: float = 0.5,
    ):
        self.mp_hands = mp_hands_module
        self.mp_draw = mp_drawing_utils
        self.mp_drawing_styles = mp_drawing_styles

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )

    def detect(self, frame: np.ndarray) -> DetectionResult:
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_rgb.flags.writeable = False

        results = self.hands.process(frame_rgb)

        frame_rgb.flags.writeable = True

        detection = DetectionResult(raw_results=results, frame_rgb=frame_rgb)

        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_lm, handedness in zip(
                results.multi_hand_landmarks, results.multi_handedness
            ):
                detection.hands.append(
                    HandLandmarks(
                        landmarks=hand_lm.landmark,
                        handedness=handedness.classification[0].label,
                        confidence=handedness.classification[0].score,
                    )
                )

        return detection

    def close(self):
        self.hands.close()
