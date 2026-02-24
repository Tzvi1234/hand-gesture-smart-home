import os
import requests
import logging

logger = logging.getLogger(__name__)

# action → (domain, service, env_var_for_entity_id)
ACTION_MAP = {
    "ac_toggle":        ("climate", "toggle",   "HA_CLIMATE_ENTITY"),
    "ac_on":            ("climate", "turn_on",  "HA_CLIMATE_ENTITY"),
    "ac_off":           ("climate", "turn_off", "HA_CLIMATE_ENTITY"),
    "ac_increase_temp": ("climate", "turn_on",  "HA_CLIMATE_ENTITY"),  # extend as needed
    "ac_decrease_temp": ("climate", "turn_on",  "HA_CLIMATE_ENTITY"),
    "lights_on":        ("light",   "turn_on",  "HA_LIGHT_ENTITY"),
    "lights_off":       ("light",   "turn_off", "HA_LIGHT_ENTITY"),
    "lights_toggle":    ("light",   "toggle",   "HA_LIGHT_ENTITY"),
    "volume_up":        ("media_player", "volume_up",   "HA_MEDIA_PLAYER_ENTITY"),
    "volume_down":      ("media_player", "volume_down", "HA_MEDIA_PLAYER_ENTITY"),
    "custom_scene":     ("scene",   "turn_on",  "HA_SCENE_ENTITY"),
}


class HomeAssistantBackend:
    """Controls Home Assistant entities via its REST API."""

    def __init__(self):
        self.base_url = os.getenv("HA_BASE_URL", "http://homeassistant.local:8123").rstrip("/")
        self.token = os.getenv("HA_LONG_LIVED_TOKEN", "")
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        if not self.token:
            logger.warning("HA_LONG_LIVED_TOKEN is not set — Home Assistant backend will not work")

    def trigger(self, action: str, gesture=None) -> bool:
        if not self.token:
            logger.error("Cannot call Home Assistant: token missing")
            return False

        mapping = ACTION_MAP.get(action)
        if not mapping:
            logger.warning(f"No HA mapping for action '{action}'")
            return False

        domain, service, entity_env = mapping
        entity_id = os.getenv(entity_env, "")
        if not entity_id:
            logger.warning(f"Entity ID not configured ({entity_env})")
            return False

        url = f"{self.base_url}/api/services/{domain}/{service}"
        payload = {"entity_id": entity_id}

        try:
            resp = requests.post(url, json=payload, headers=self._headers, timeout=5)
            if resp.status_code in (200, 201):
                logger.info(f"HA service {domain}.{service} called on {entity_id}")
                return True
            logger.warning(f"HA returned {resp.status_code}: {resp.text}")
            return False
        except requests.RequestException as exc:
            logger.error(f"HA request error: {exc}")
            return False
