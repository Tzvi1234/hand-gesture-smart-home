import time
from typing import Optional, List

import cv2
import numpy as np
from mediapipe.python.solutions import hands as mp_hands_module
from mediapipe.python.solutions import drawing_utils as mp_drawing_utils
from mediapipe.python.solutions import drawing_styles as mp_drawing_styles
from PIL import Image, ImageDraw, ImageFont

from ..gesture.detector import DetectionResult
from ..gesture.recognizer import RecognizedGesture

EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
EMOJI_FONT_SIZE = 109          # גודל גופן — אימוגי יוצא כ-~136px
EMOJI_DISPLAY_SECS = 2.0      # כמה שניות האימוגי מוצג

GESTURE_LABELS = {
    "heart":      "❤️  לב",
    "thumbs_up":  "👍  אגודל למעלה",
    "thumbs_down":"👎  אגודל למטה",
    "open_palm":  "🖐  כף פתוחה",
    "fist":       "✊  אגרוף",
    "peace":      "✌️  peace",
    "point":      "👆  מצביע",
    "rock":       "🤘  rock",
    "l_shape":    "🤙  L",
    "unknown":    "",
}


class Visualizer:

    def __init__(self):
        self._mp_draw   = mp_drawing_utils
        self._mp_styles = mp_drawing_styles
        self._mp_hands  = mp_hands_module

        try:
            self._emoji_font = ImageFont.truetype(EMOJI_FONT, size=EMOJI_FONT_SIZE)
        except Exception:
            self._emoji_font = None   # fallback: ללא PIL

        self._active_emoji: Optional[str] = None
        self._emoji_start:  float = 0.0

    # ------------------------------------------------------------------ #

    def show_emoji(self, emoji: str):
        self._active_emoji = emoji
        self._emoji_start  = time.time()

    def draw(
        self,
        frame: np.ndarray,
        detection: DetectionResult,
        gestures: List[RecognizedGesture],
    ) -> np.ndarray:
        display = frame.copy()

        # ציור נקודות יד
        if detection.raw_results and detection.raw_results.multi_hand_landmarks:
            for hand_lm in detection.raw_results.multi_hand_landmarks:
                self._mp_draw.draw_landmarks(
                    display,
                    hand_lm,
                    self._mp_hands.HAND_CONNECTIONS,
                    self._mp_styles.get_default_hand_landmarks_style(),
                    self._mp_styles.get_default_hand_connections_style(),
                )

        # שם התנועה הנוכחית (פינה שמאלית עליונה)
        self._draw_gesture_label(display, gestures)

        # אימוגי גדול במרכז
        self._draw_emoji(display)

        # הוראות
        h = display.shape[0]
        cv2.putText(display, "Q / ESC: יציאה", (10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (120, 120, 120), 1)

        return display

    # ------------------------------------------------------------------ #

    def _draw_gesture_label(self, frame: np.ndarray, gestures: List[RecognizedGesture]):
        if not gestures:
            return
        # קח את התנועה הראשונה שיש לה שם
        for g in gestures:
            label = GESTURE_LABELS.get(g.name, "")
            if label:
                cv2.putText(frame, label, (10, 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 220, 220), 2)
                break

    def _draw_emoji(self, frame: np.ndarray):
        if not self._active_emoji:
            return

        elapsed = time.time() - self._emoji_start
        if elapsed > EMOJI_DISPLAY_SECS:
            self._active_emoji = None
            return

        alpha = max(0.0, 1.0 - elapsed / EMOJI_DISPLAY_SECS)
        h, w = frame.shape[:2]
        emoji_size = 200

        if self._emoji_font:
            self._draw_emoji_pil(frame, self._active_emoji, alpha, emoji_size, w, h)
        else:
            # Fallback: טקסט ASCII גדול
            text = self._active_emoji
            sz, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 3.5, 6)
            x = (w - sz[0]) // 2
            y = (h + sz[1]) // 2
            c = int(255 * alpha)
            cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                        3.5, (c, c, c), 6)

    def _draw_emoji_pil(
        self,
        frame: np.ndarray,
        emoji: str,
        alpha: float,
        size: int,
        w: int,
        h: int,
    ):
        # צור שכבת אימוגי שקופה
        layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw  = ImageDraw.Draw(layer)
        draw.text((0, 0), emoji, font=self._emoji_font, embedded_color=True)

        # הפעל שקיפות
        r, g, b, a = layer.split()
        a = a.point(lambda v: int(v * alpha))
        layer = Image.merge("RGBA", (r, g, b, a))

        # הדבק על הפריים במרכז
        pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
        ex = (w - size) // 2
        ey = (h - size) // 2
        pil_frame.paste(layer, (ex, ey), layer)

        result = cv2.cvtColor(np.array(pil_frame.convert("RGB")), cv2.COLOR_RGB2BGR)
        frame[:] = result
