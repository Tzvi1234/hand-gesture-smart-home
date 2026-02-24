# Hand Gesture Smart Home Controller

Control your Google Home devices with hand gestures detected live from your webcam.

Built with **MediaPipe** for hand tracking and **OpenCV** for the live debug view.
Supports three smart-home backends: **IFTTT**, **Home Assistant**, and **Google SDM** (Nest).

---

## Demo — Gesture Map (default)

| Gesture | What it does |
|---------|-------------|
| ❤️  Finger Heart (thumb + index tips touching) | Toggle AC |
| 🖐️  Open Palm (5 fingers) | Increase AC temperature |
| ✊  Fist (0 fingers) | Decrease AC temperature |
| 👍  Thumbs Up | Turn on lights |
| 👎  Thumbs Down | Turn off lights |
| ✌️  Peace / Victory | Volume up |
| 🤘  Rock On (index + pinky) | Volume down |
| 👌  OK Sign | Activate custom scene |
| ☝️  Point (index only) | Toggle lights |

You can remap any gesture → action in `config/gestures.yaml`.

---

## Requirements

- Python 3.9 or later
- A webcam
- One of the following:
  - An [IFTTT](https://ifttt.com) account (easiest)
  - A [Home Assistant](https://www.home-assistant.io) instance
  - A Google Nest device + Google Cloud project (advanced)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/hand-gesture-smart-home.git
cd hand-gesture-smart-home
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` in your editor and fill in the credentials for your chosen backend (see backend setup below).

---

## Running the application

```bash
# Normal mode
python main.py

# Show landmark-coordinate debug panel (press D at any time to toggle)
python main.py --debug

# Dry-run: prints triggered actions, sends nothing to your home
python main.py --dry-run

# Use a specific camera (useful if you have multiple webcams)
python main.py --camera 1

# Use a custom gesture config
python main.py --config path/to/my_gestures.yaml
```

### Keyboard shortcuts (inside the window)

| Key | Action |
|-----|--------|
| `Q` or `ESC` | Quit |
| `D` | Toggle debug overlay |

---

## Backend Setup

### Option 1 — IFTTT Webhooks (Recommended)

IFTTT is the simplest integration. Each gesture triggers a named webhook event that you connect to a Google Home routine.

**Step-by-step:**

1. Sign up or log in at [ifttt.com](https://ifttt.com).
2. Go to **Explore → Webhooks → Documentation** and copy your **Webhook key**.
3. Paste it in `.env`:
   ```
   HOME_BACKEND=ifttt
   IFTTT_WEBHOOK_KEY=your_key_here
   ```
4. For each gesture you want to control, create an IFTTT **Applet**:
   - **IF** → Webhooks → *Receive a web request* → enter the event name (e.g. `ac_toggle`)
   - **THEN** → Google Home → *Adjust thermostat* (or any other action)
5. Event names used by this app (see `src/home/backends/ifttt.py`):

   | Event name | Triggered by |
   |------------|-------------|
   | `ac_toggle` | Finger Heart |
   | `ac_temp_up` | Open Palm |
   | `ac_temp_down` | Fist |
   | `lights_on` | Thumbs Up |
   | `lights_off` | Thumbs Down |
   | `volume_up` | Peace Sign |
   | `volume_down` | Rock On |
   | `custom_scene` | OK Sign |
   | `lights_toggle` | Pointing |

---

### Option 2 — Home Assistant

If you run Home Assistant, this backend calls its REST API directly.

1. In Home Assistant go to **Profile → Long-Lived Access Tokens → Create Token**.
2. Find your entity IDs (e.g. `climate.bedroom_ac`, `light.living_room`).
3. Set in `.env`:
   ```
   HOME_BACKEND=home_assistant
   HA_BASE_URL=http://homeassistant.local:8123
   HA_LONG_LIVED_TOKEN=your_token
   HA_CLIMATE_ENTITY=climate.living_room_ac
   HA_LIGHT_ENTITY=light.living_room
   HA_MEDIA_PLAYER_ENTITY=media_player.living_room_speaker
   HA_SCENE_ENTITY=scene.movie_night
   ```

---

### Option 3 — Google Smart Device Management (Nest devices)

This uses the official Google SDM API and works only with **Nest** thermostats.

1. **Enable Device Access**
   - Go to [console.nest.google.com/device-access](https://console.nest.google.com/device-access) and create a project (one-time $5 registration fee).
   - Note your **Project ID**.

2. **Create OAuth 2.0 credentials**
   - Open [console.cloud.google.com](https://console.cloud.google.com).
   - Create (or select) a project → **APIs & Services → Credentials**.
   - Create an **OAuth 2.0 Client ID** (Desktop application).
   - Download the JSON and note `client_id` and `client_secret`.

3. **Authorise and obtain a refresh token**
   - Use the OAuth Playground or run the helper script:
     ```bash
     python scripts/get_google_token.py
     ```
   - This will open a browser, ask you to approve access, and print your `refresh_token`.

4. **Find your Device ID**
   ```bash
   curl -X GET \
     "https://smartdevicemanagement.googleapis.com/v1/enterprises/YOUR_PROJECT_ID/devices" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
   ```

5. Set in `.env`:
   ```
   HOME_BACKEND=google_sdm
   GOOGLE_SDM_PROJECT_ID=your_project_id
   GOOGLE_SDM_DEVICE_ID=your_device_id
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   GOOGLE_REFRESH_TOKEN=your_refresh_token
   ```

---

## Customising Gestures

Edit `config/gestures.yaml` to change which gesture triggers which action, or to adjust the cooldown (minimum seconds between two triggers of the same gesture).

```yaml
gestures:
  heart:
    name: "Finger Heart"
    action: "ac_toggle"
    description: "Toggle AC"
    cooldown: 2.5
```

Available `action` values depend on your backend.
For IFTTT: any string — it becomes the webhook event name.
For Home Assistant: see `src/home/backends/home_assistant.py → ACTION_MAP`.
For Google SDM: see `src/home/backends/google_sdm.py → _action_to_command`.

---

## Project Structure

```
hand-gesture-smart-home/
├── main.py                          # Entry point
├── requirements.txt
├── .env.example                     # Template for credentials
├── config/
│   └── gestures.yaml               # Gesture → action mappings
└── src/
    ├── config.py                    # Config loader
    ├── camera.py                    # Webcam capture
    ├── gesture/
    │   ├── detector.py             # MediaPipe hand detection (21 landmarks)
    │   └── recognizer.py           # Gesture classification logic
    ├── home/
    │   ├── controller.py           # Action dispatcher + cooldown logic
    │   └── backends/
    │       ├── ifttt.py            # IFTTT Webhooks
    │       ├── home_assistant.py   # Home Assistant REST API
    │       └── google_sdm.py       # Google Smart Device Management API
    └── ui/
        └── visualizer.py           # OpenCV live debug view
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Failed to open camera` | Try `--camera 1` or check that no other app is using the webcam |
| Gestures not detected | Ensure good lighting; keep hand 30–80 cm from camera |
| IFTTT not triggering | Verify key in `.env`; check Applet is enabled; test event name with curl |
| HA returns 401 | Regenerate the long-lived token |
| Google SDM returns 403 | Re-run the token helper; ensure Device Access project is active |
| Heart gesture confused with OK | Adjust the `thumb_index_dist` threshold in `src/gesture/recognizer.py` |

---

## License

MIT
