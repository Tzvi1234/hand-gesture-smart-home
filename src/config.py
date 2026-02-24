import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Dict


@dataclass
class GestureConfig:
    name: str
    action: str
    description: str
    cooldown: float = 2.0


def load_config(config_path: str) -> Dict[str, GestureConfig]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    configs = {}
    for gesture_id, gesture_data in data.get("gestures", {}).items():
        configs[gesture_id] = GestureConfig(
            name=gesture_data["name"],
            action=gesture_data["action"],
            description=gesture_data["description"],
            cooldown=gesture_data.get("cooldown", 2.0),
        )

    return configs
