import os
import logging
import requests

logger = logging.getLogger(__name__)

SDM_BASE = "https://smartdevicemanagement.googleapis.com/v1"
TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleSDMBackend:
    """
    Controls Nest devices via the Smart Device Management (SDM) API.
    Requires a Google Cloud project enrolled in the Device Access programme.
    See README for full OAuth2 setup instructions.
    """

    def __init__(self):
        self.project_id    = os.getenv("GOOGLE_SDM_PROJECT_ID", "")
        self.device_id     = os.getenv("GOOGLE_SDM_DEVICE_ID", "")
        self.client_id     = os.getenv("GOOGLE_CLIENT_ID", "")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN", "")
        self._access_token: str = ""

        missing = [
            k for k, v in {
                "GOOGLE_SDM_PROJECT_ID": self.project_id,
                "GOOGLE_SDM_DEVICE_ID":  self.device_id,
                "GOOGLE_CLIENT_ID":      self.client_id,
                "GOOGLE_CLIENT_SECRET":  self.client_secret,
                "GOOGLE_REFRESH_TOKEN":  self.refresh_token,
            }.items() if not v
        ]
        if missing:
            logger.warning(f"Google SDM: missing env vars: {missing}")

    def _refresh_access_token(self) -> bool:
        try:
            resp = requests.post(
                TOKEN_URL,
                data={
                    "client_id":     self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type":    "refresh_token",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                self._access_token = resp.json()["access_token"]
                return True
            logger.error(f"Token refresh failed: {resp.status_code} {resp.text}")
            return False
        except requests.RequestException as exc:
            logger.error(f"Token refresh error: {exc}")
            return False

    def trigger(self, action: str, gesture=None) -> bool:
        if not self._access_token and not self._refresh_access_token():
            return False

        command = self._action_to_command(action)
        if not command:
            logger.warning(f"No SDM command mapped for action '{action}'")
            return False

        url = (
            f"{SDM_BASE}/enterprises/{self.project_id}"
            f"/devices/{self.device_id}:executeCommand"
        )
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type":  "application/json",
        }

        try:
            resp = requests.post(url, json=command, headers=headers, timeout=5)
            if resp.status_code == 200:
                return True
            # Token may have expired — retry once
            if resp.status_code == 401 and self._refresh_access_token():
                headers["Authorization"] = f"Bearer {self._access_token}"
                resp = requests.post(url, json=command, headers=headers, timeout=5)
                return resp.status_code == 200
            logger.warning(f"SDM returned {resp.status_code}: {resp.text}")
            return False
        except requests.RequestException as exc:
            logger.error(f"SDM request error: {exc}")
            return False

    @staticmethod
    def _action_to_command(action: str) -> dict:
        commands = {
            "ac_on": {
                "command": "sdm.devices.commands.ThermostatMode.SetMode",
                "params":  {"mode": "COOL"},
            },
            "ac_off": {
                "command": "sdm.devices.commands.ThermostatMode.SetMode",
                "params":  {"mode": "OFF"},
            },
            "ac_toggle": {
                # SDM has no toggle; use COOL as default "on" state
                "command": "sdm.devices.commands.ThermostatMode.SetMode",
                "params":  {"mode": "COOL"},
            },
            "ac_increase_temp": {
                "command": "sdm.devices.commands.ThermostatTemperatureSetpoint.SetCool",
                "params":  {"coolCelsius": 24.0},
            },
            "ac_decrease_temp": {
                "command": "sdm.devices.commands.ThermostatTemperatureSetpoint.SetCool",
                "params":  {"coolCelsius": 22.0},
            },
        }
        return commands.get(action, {})
