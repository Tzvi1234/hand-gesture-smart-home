import os
import time
import logging
from typing import Optional

from ..gesture.recognizer import RecognizedGesture

logger = logging.getLogger(__name__)

# Default per-gesture cooldown (seconds)
DEFAULT_COOLDOWN = 2.0


class HomeController:
    """Dispatches smart-home actions triggered by recognised gestures."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._last_action_time: dict = {}
        self._backend = self._init_backend()

        if dry_run:
            logger.info("DRY RUN mode — no actual home control commands will be sent")

    def _init_backend(self):
        backend_type = os.getenv("HOME_BACKEND", "ifttt").lower()

        if backend_type == "ifttt":
            from .backends.ifttt import IFTTTBackend
            return IFTTTBackend()
        elif backend_type == "home_assistant":
            from .backends.home_assistant import HomeAssistantBackend
            return HomeAssistantBackend()
        elif backend_type == "google_sdm":
            from .backends.google_sdm import GoogleSDMBackend
            return GoogleSDMBackend()
        else:
            logger.warning(f"Unknown backend '{backend_type}', falling back to IFTTT")
            from .backends.ifttt import IFTTTBackend
            return IFTTTBackend()

    def execute(self, gesture: RecognizedGesture, cooldown: float = DEFAULT_COOLDOWN) -> bool:
        """
        Send a home-control command for the given gesture.
        Returns True if the action was dispatched.
        """
        if not gesture.action:
            return False

        # Per-gesture cooldown guard
        now = time.time()
        if (now - self._last_action_time.get(gesture.name, 0.0)) < cooldown:
            return False
        self._last_action_time[gesture.name] = now

        if self.dry_run:
            logger.info(
                f"[DRY RUN] gesture={gesture.display_name!r}  "
                f"action={gesture.action!r}  desc={gesture.description!r}"
            )
            return True

        try:
            success = self._backend.trigger(gesture.action, gesture)
            level = logging.INFO if success else logging.WARNING
            logger.log(level, f"Action '{gesture.action}' → {'OK' if success else 'FAILED'}")
            return success
        except Exception as exc:
            logger.error(f"Error executing action '{gesture.action}': {exc}")
            return False
