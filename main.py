#!/usr/bin/env python3
"""
Hand Gesture Smart Home Controller
-----------------------------------
Uses your webcam to detect hand gestures in real-time and trigger
smart-home actions (Google Home via IFTTT, Home Assistant, or Google SDM).

Usage:
    python main.py                  # basic mode
    python main.py --debug          # live landmark coordinates overlay
    python main.py --dry-run        # print actions, send nothing
    python main.py --camera 1       # use a specific camera index
    python main.py --config path/to/gestures.yaml
"""

import sys
import logging
import argparse

import cv2
from dotenv import load_dotenv

from src.camera import Camera
from src.config import load_config
from src.gesture.detector import HandDetector
from src.gesture.recognizer import GestureRecognizer
from src.home.controller import HomeController
from src.ui.visualizer import Visualizer

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Hand Gesture Smart Home Controller")
    p.add_argument("--camera", type=int, default=0,
                   help="Camera device index (default: 0)")
    p.add_argument("--debug", action="store_true",
                   help="Show landmark-coordinate debug panel")
    p.add_argument("--dry-run", action="store_true",
                   help="Log actions without sending any home-control commands")
    p.add_argument("--config", default="config/gestures.yaml",
                   help="Path to gesture-action mapping YAML (default: config/gestures.yaml)")
    return p.parse_args()


def main():
    args = parse_args()

    config     = load_config(args.config)
    camera     = Camera(index=args.camera)
    detector   = HandDetector(max_hands=2, detection_confidence=0.7)
    recognizer = GestureRecognizer(config=config)
    controller = HomeController(dry_run=args.dry_run)
    visualizer = Visualizer(debug=args.debug)

    logger.info("Hand Gesture Smart Home — starting")
    logger.info(f"Camera={args.camera}  debug={args.debug}  dry_run={args.dry_run}")

    if not camera.open():
        logger.error("Failed to open camera — exiting")
        sys.exit(1)

    try:
        while True:
            frame = camera.read()
            if frame is None:
                logger.warning("Dropped frame")
                continue

            detection = detector.detect(frame)
            gestures  = recognizer.recognize(detection)

            for gesture in gestures:
                if gesture.name == "unknown":
                    continue
                cfg = config.get(gesture.name)
                cooldown = cfg.cooldown if cfg else 2.0
                if controller.execute(gesture, cooldown=cooldown):
                    logger.info(
                        f"Triggered  gesture={gesture.display_name!r}"
                        f"  action={gesture.action!r}"
                    )
                    visualizer.flash_action(
                        f"{gesture.display_name} => {gesture.description or gesture.action}"
                    )

            display = visualizer.draw(frame, detection, gestures)
            cv2.imshow("Hand Gesture Smart Home  [Q/ESC = quit]", display)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):   # q or ESC
                break
            elif key == ord("d"):
                visualizer.toggle_debug()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        camera.release()
        detector.close()
        cv2.destroyAllWindows()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    main()
