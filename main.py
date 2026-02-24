#!/usr/bin/env python3
"""
Hand Gesture Emoji Display
--------------------------
מזהה תנועות יד דרך המצלמה ומציג אימוגי על המסך.

- ❤️  כשמזהה לב (thumb + index נוגעים)
- 👍  כשמזהה אגודל למעלה

Usage:
    python main.py
    python main.py --camera 1   # מצלמה אחרת
"""

import sys
import time
import cv2

from src.camera import Camera
from src.gesture.detector import HandDetector
from src.gesture.recognizer import GestureRecognizer
from src.ui.visualizer import Visualizer

GESTURE_EMOJI = {
    "heart":     "❤️",
    "thumbs_up": "👍",
}

COOLDOWN = 2.0   # שניות בין טריגרים לאותה תנועה


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--camera", type=int, default=0)
    args = p.parse_args()

    camera     = Camera(index=args.camera)
    detector   = HandDetector(max_hands=2, detection_confidence=0.7)
    recognizer = GestureRecognizer()
    visualizer = Visualizer()

    last_trigger: dict[str, float] = {}

    if not camera.open():
        print("שגיאה: לא הצלחתי לפתוח את המצלמה")
        sys.exit(1)

    try:
        while True:
            frame = camera.read()
            if frame is None:
                continue

            detection = detector.detect(frame)
            gestures  = recognizer.recognize(detection)

            for gesture in gestures:
                emoji = GESTURE_EMOJI.get(gesture.name)
                if not emoji:
                    continue
                now = time.time()
                if now - last_trigger.get(gesture.name, 0.0) >= COOLDOWN:
                    visualizer.show_emoji(emoji)
                    last_trigger[gesture.name] = now

            display = visualizer.draw(frame, detection, gestures)
            cv2.imshow("Hand Gesture  [Q / ESC = יציאה]", display)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break

    except KeyboardInterrupt:
        pass
    finally:
        camera.release()
        detector.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
