import time
import cv2
import numpy as np
import mediapipe as mp
from typing import List

from ..gesture.detector import DetectionResult
from ..gesture.recognizer import RecognizedGesture

# BGR colour per gesture
GESTURE_COLORS = {
    "open_palm":     (0,   220,   0),
    "fist":          (0,     0, 220),
    "thumbs_up":     (0,   220, 220),
    "thumbs_down":   (0,   100, 255),
    "peace":         (220,   0, 220),
    "point":         (220, 220,   0),
    "heart":         (60,   60, 255),   # red-ish (BGR)
    "ok":            (0,   200, 120),
    "rock":          (200,   0, 140),
    "l_shape":       (180, 140,  60),
    "three_fingers": (80,  200, 255),
    "four_fingers":  (40,  255, 200),
    "unknown":       (128, 128, 128),
}

FINGER_SYMBOLS = ["T", "I", "M", "R", "P"]   # Thumb Index Middle Ring Pinky


class Visualizer:
    """Renders hand landmarks, gesture info panel, FPS and debug overlay."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.mp_draw   = mp.solutions.drawing_utils
        self.mp_styles = mp.solutions.drawing_styles
        self.mp_hands  = mp.solutions.hands

        self._fps_times: List[float] = []
        self._flash_text   = ""
        self._flash_time   = 0.0

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def toggle_debug(self):
        self.debug = not self.debug

    def flash_action(self, text: str):
        self._flash_text = text
        self._flash_time = time.time()

    def draw(
        self,
        frame: np.ndarray,
        detection: DetectionResult,
        gestures: List[RecognizedGesture],
    ) -> np.ndarray:
        display = frame.copy()

        # --- hand landmarks ---
        if detection.raw_results and detection.raw_results.multi_hand_landmarks:
            for hand_lm, handedness in zip(
                detection.raw_results.multi_hand_landmarks,
                detection.raw_results.multi_handedness,
            ):
                label   = handedness.classification[0].label
                gesture = next((g for g in gestures if g.handedness == label), None)
                color   = GESTURE_COLORS.get(gesture.name if gesture else "unknown", (200, 200, 200))

                self.mp_draw.draw_landmarks(
                    display,
                    hand_lm,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_styles.get_default_hand_landmarks_style(),
                    self.mp_styles.get_default_hand_connections_style(),
                )

                # Gesture label near wrist
                if gesture:
                    h, w = display.shape[:2]
                    wx = int(hand_lm.landmark[0].x * w)
                    wy = int(hand_lm.landmark[0].y * h)
                    label_text = f"{gesture.display_name} ({gesture.confidence:.0%})"
                    cv2.putText(
                        display, label_text,
                        (max(wx - 60, 0), min(wy + 35, h - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2,
                    )

        # --- panels ---
        self._draw_fps(display)
        self._draw_gesture_panel(display, gestures)
        if self.debug:
            self._draw_debug_panel(display, gestures)
        self._draw_action_flash(display)
        self._draw_shortcuts(display)

        return display

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _draw_fps(self, frame: np.ndarray):
        now = time.time()
        self._fps_times.append(now)
        self._fps_times = [t for t in self._fps_times if now - t < 1.0]
        fps = len(self._fps_times)
        cv2.putText(frame, f"FPS: {fps}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 0), 2)

    def _draw_gesture_panel(self, frame: np.ndarray, gestures: List[RecognizedGesture]):
        h, w = frame.shape[:2]
        panel_w = 290
        px = w - panel_w

        # Semi-transparent background
        overlay = frame.copy()
        panel_h = max(60 + len(gestures) * 120, 120)
        cv2.rectangle(overlay, (px, 0), (w, panel_h), (15, 15, 15), -1)
        cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, frame)

        y = 24
        cv2.putText(frame, "DETECTED GESTURES", (px + 8, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (180, 180, 180), 1)
        y += 28

        if not gestures:
            cv2.putText(frame, "  — no hands —", (px + 8, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, (90, 90, 90), 1)
            return

        for g in gestures:
            color = GESTURE_COLORS.get(g.name, (200, 200, 200))

            # Hand label
            cv2.putText(frame, f"{g.handedness} Hand:", (px + 8, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (130, 130, 130), 1)
            y += 20

            # Gesture name
            cv2.putText(frame, g.display_name, (px + 8, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.68, color, 2)
            y += 22

            # Confidence bar
            bar_max = panel_w - 20
            bar_fill = int(bar_max * g.confidence)
            cv2.rectangle(frame, (px + 8, y), (px + 8 + bar_max, y + 7), (55, 55, 55), -1)
            cv2.rectangle(frame, (px + 8, y), (px + 8 + bar_fill, y + 7), color, -1)
            cv2.putText(frame, f"{g.confidence:.0%}", (px + panel_w - 42, y + 7),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 200), 1)
            y += 16

            # Finger indicator — filled circle = extended
            finger_str = "  ".join(
                f"{sym}●" if up else f"{sym}○"
                for sym, up in zip(FINGER_SYMBOLS, g.fingers_up)
            )
            cv2.putText(frame, finger_str, (px + 8, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1)
            y += 18

            # Action label
            if g.action:
                desc = g.description or g.action
                cv2.putText(frame, f"=> {desc}", (px + 8, y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (80, 220, 80), 1)
                y += 18

            y += 8   # gap between hands

    def _draw_debug_panel(self, frame: np.ndarray, gestures: List[RecognizedGesture]):
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h - 210), (420, h), (15, 15, 15), -1)
        cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)

        y = h - 198
        cv2.putText(frame, "DEBUG  [D = toggle]", (8, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 220, 220), 1)
        y += 18

        for g in gestures:
            cv2.putText(frame, f"{g.handedness}: fingers={g.fingers_up}", (8, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.40, (200, 200, 200), 1)
            y += 15

            lm = g.landmarks
            for idx, label in [(0, "Wrist"), (4, "Thumb tip"), (8, "Index tip"),
                                (12, "Mid tip"), (16, "Ring tip"), (20, "Pinky tip")]:
                info = f"  [{idx:2d}] {label}: ({lm[idx].x:.3f}, {lm[idx].y:.3f}, {lm[idx].z:.3f})"
                cv2.putText(frame, info, (8, y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.36, (160, 160, 160), 1)
                y += 13
            y += 4

    def _draw_action_flash(self, frame: np.ndarray):
        if not self._flash_text:
            return
        elapsed = time.time() - self._flash_time
        if elapsed > 2.0:
            self._flash_text = ""
            return

        alpha = max(0.0, 1.0 - elapsed / 2.0)
        h, w = frame.shape[:2]
        text = self._flash_text
        sz, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.1, 3)
        x = (w - sz[0]) // 2
        y = h // 2
        color = (int(60 * alpha), int(240 * alpha), int(60 * alpha))
        cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1.1, color, 3)

    def _draw_shortcuts(self, frame: np.ndarray):
        h = frame.shape[0]
        cv2.putText(frame, "Q / ESC: Quit    D: Toggle debug",
                    (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (120, 120, 120), 1)
