import time
import os
from typing import Optional, List

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..gesture.detector import DetectionResult, HAND_CONNECTIONS
from ..gesture.recognizer import RecognizedGesture

# גופן אימוגי — Windows ו-Linux
_EMOJI_FONT_CANDIDATES = [
    "C:/Windows/Fonts/seguiemj.ttf",                                   # Windows (Segoe UI Emoji)
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",               # Linux
    "/System/Library/Fonts/Apple Color Emoji.ttc",                     # macOS
]

EMOJI_DISPLAY_SECS = 2.0

GESTURE_LABELS = {
    "heart":      "לב",
    "thumbs_up":  "אגודל למעלה",
    "thumbs_down": "אגודל למטה",
    "open_palm":  "כף פתוחה",
    "fist":       "אגרוף",
    "peace":      "peace",
    "point":      "מצביע",
    "rock":       "rock",
    "unknown":    "",
}


def _load_emoji_font(size: int):
    for path in _EMOJI_FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    return None


class Visualizer:

    def __init__(self):
        self._emoji_font = _load_emoji_font(size=109)

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

        # ציור נקודות ועצמות יד
        self._draw_landmarks(display, detection)

        # שם התנועה — פינה שמאלית עליונה
        self._draw_gesture_label(display, gestures)

        # אימוגי גדול במרכז
        self._draw_emoji(display)

        h = display.shape[0]
        cv2.putText(display, "Q / ESC: quit", (10, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (120, 120, 120), 1)

        return display

    # ------------------------------------------------------------------ #

    def _draw_landmarks(self, frame: np.ndarray, detection: DetectionResult):
        h, w = frame.shape[:2]
        for hand in detection.hands:
            lm = hand.landmarks

            # חיבורים
            for a, b in HAND_CONNECTIONS:
                x1, y1 = int(lm[a].x * w), int(lm[a].y * h)
                x2, y2 = int(lm[b].x * w), int(lm[b].y * h)
                cv2.line(frame, (x1, y1), (x2, y2), (0, 200, 255), 2)

            # נקודות
            for pt in lm:
                cx, cy = int(pt.x * w), int(pt.y * h)
                cv2.circle(frame, (cx, cy), 5, (255, 255, 255), -1)
                cv2.circle(frame, (cx, cy), 5, (0, 150, 255), 1)

    def _draw_gesture_label(self, frame: np.ndarray, gestures: List[RecognizedGesture]):
        for g in gestures:
            label = GESTURE_LABELS.get(g.name, "")
            if label:
                cv2.putText(frame, label, (10, 38),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 220, 220), 2)
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
        size = 200

        if self._emoji_font:
            # PIL — אימוגי צבעוני אמיתי
            layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw  = ImageDraw.Draw(layer)
            draw.text((0, 0), self._active_emoji, font=self._emoji_font,
                      embedded_color=True)
            r, g, b, a = layer.split()
            a = a.point(lambda v: int(v * alpha))
            layer = Image.merge("RGBA", (r, g, b, a))

            pil_frame = Image.fromarray(
                cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            ).convert("RGBA")
            pil_frame.paste(layer, ((w - size) // 2, (h - size) // 2), layer)
            frame[:] = cv2.cvtColor(np.array(pil_frame.convert("RGB")),
                                    cv2.COLOR_RGB2BGR)
        else:
            # Fallback — טקסט רגיל
            c = int(255 * alpha)
            sz, _ = cv2.getTextSize(self._active_emoji,
                                    cv2.FONT_HERSHEY_SIMPLEX, 3.5, 6)
            cv2.putText(frame, self._active_emoji,
                        ((w - sz[0]) // 2, (h + sz[1]) // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 3.5, (c, c, c), 6)
