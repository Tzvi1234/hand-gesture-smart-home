import os
import requests
import logging

logger = logging.getLogger(__name__)

_IFTTT_URL = "https://maker.ifttt.com/trigger/{event}/with/key/{key}"

# Maps internal action names → IFTTT event names.
# Create matching Applets on https://ifttt.com/maker_webhooks
ACTION_EVENTS = {
    "ac_toggle":        "ac_toggle",
    "ac_on":            "ac_on",
    "ac_off":           "ac_off",
    "ac_increase_temp": "ac_temp_up",
    "ac_decrease_temp": "ac_temp_down",
    "lights_on":        "lights_on",
    "lights_off":       "lights_off",
    "lights_toggle":    "lights_toggle",
    "volume_up":        "volume_up",
    "volume_down":      "volume_down",
    "custom_scene":     "custom_scene",
}


class IFTTTBackend:
    """Triggers IFTTT Webhooks (Maker) events."""

    def __init__(self):
        self.api_key = os.getenv("IFTTT_WEBHOOK_KEY", "")
        if not self.api_key:
            logger.warning(
                "IFTTT_WEBHOOK_KEY is not set — IFTTT triggers will not work"
            )

    def trigger(self, action: str, gesture=None) -> bool:
        if not self.api_key:
            logger.error("Cannot trigger IFTTT: API key missing")
            return False

        event = ACTION_EVENTS.get(action, action)
        url = _IFTTT_URL.format(event=event, key=self.api_key)

        payload = {}
        if gesture:
            payload = {
                "value1": gesture.display_name,
                "value2": action,
                "value3": f"confidence:{gesture.confidence:.2f}",
            }

        try:
            resp = requests.post(url, json=payload, timeout=5)
            if resp.status_code == 200:
                logger.info(f"IFTTT event '{event}' triggered successfully")
                return True
            logger.warning(f"IFTTT returned {resp.status_code}: {resp.text}")
            return False
        except requests.RequestException as exc:
            logger.error(f"IFTTT request failed: {exc}")
            return False
