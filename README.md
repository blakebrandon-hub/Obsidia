# Obsidia [![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fblakebrandon-hub%2FObsidia&env=GEMINI_API_KEY&envDescription=GEMINI_API_KEY)

A slow, atmospheric text-based game about terraforming a dead planet over 300 years. You play as Ren, an android left alone with a small companion robot named Bloop, a hub full of machinery, and three centuries of work ahead of you.

## Plot
There is no story in the traditional sense. There is a planet, and there is work, and there is time.

Ren arrives alone. The atmosphere is thin and hostile. The ground is rust-colored rock. Nothing grows. The machines begin running immediately — atmospheric processors bolted into the mountain slopes, seismic thumpers driving heat from below — and Ren tends them. That is the mission. That is most of what the next 300 years will be.

Bloop is there too. A utility robot, six-legged, built for terrain mapping, repurposed long ago into something closer to companionship. Bloop doesn't speak. Bloop follows.

Progress is slow enough to be almost invisible. Years pass in the space of a few turns. The sky changes tone over decades. Instruments register shifts that eyes cannot see. Then one day there is something faintly green on the crater floor, and it is one of the most significant things that has ever happened on this planet.

The VR archive in the hub lets Ren step into historical simulations — ancient civilizations, catastrophes, ordinary lives — and live inside them for what feels like years. The longer Ren stays, the harder it becomes to tell the difference between the simulation and the planet outside. Coherence drifts. Reality becomes a matter of attention.

There is no ending. The 300-year mission is a horizon, not a finish line. What the game is really about is what it means to do slow, necessary work alone, across a span of time longer than any individual life — and what that does to the mind doing it.

---

## Screenshots 

<img width="2560" height="1440" alt="Screenshot 2026-04-06 150739" src="https://github.com/user-attachments/assets/6bbc14ca-6824-4b82-8ac4-dc1f869406d6" />

<img width="1366" height="768" alt="Screenshot 2026-04-06 153725" src="https://github.com/user-attachments/assets/f9e4dda1-eda4-46ed-8915-557357a38b3b" />

---

## What It Is

Tales of Obsidia is a single-player narrative experience backed by a live AI narrator. Each action you type is sent to a Flask backend, which builds a context window from recent history and rolling summaries, calls the Gemini API, and streams back prose. The narrator also manages a structured game state — atmosphere, temperature, water cycle, flora seeding, stability, Ren's integrity and coherence, and mission year — updating it silently in response to what happens in the story.

The game supports procedural image generation: during meaningful moments, the narrator emits a `[GENERATE_IMAGE]` tag, which triggers an image model and displays the result in the visualizer panel.

---

## Terraforming Stages

The narrator's tone and Bloop's behavior evolve automatically as the planet changes. There are six stages driven by the TERRA_SYNC values:

1. **Sterile World** — Dust, scale, and oppressive monotony.
2. **Chemical Seeding** — Invisible change. Instruments detect what eyes cannot.
3. **Microbial Life** — The first living things, boring and extraordinary.
4. **Instability** — The planet resists. Storms, die-offs, reversals.
5. **Growth** — Moss, lichen, color where there was none.
6. **Early Ecosystem** — Water cycles. Weather. The planet continuing on its own.

---

## Special Mechanics

**Planetary Travel** — Ren can use the orbital lander as a sub-orbital hopper to reach remote sites. Journeys emphasize scale and isolation.

**VR Historical Archive** — Ren can enter the ship's VR archive and live entire simulated lifetimes in historical eras. Extended immersion increases Coherence drift (C%), which at high levels begins to blur the boundary between simulation and present.

**SFX** — The narrator emits `[SFX]` tags for significant audible events. These are processed by a Tone.js synthesizer engine in the frontend using three synth types: FMSynth (crystalline, high-frequency), MonoSynth (deep, tectonic), and NoiseSynth (wind, mechanical noise).

**SIGNAL** — Each narrator response includes a `[SIGNAL]` tag: a single quiet observation from the environment. Rendered as a highlighted aside in the scroll.

## Setup

### 1. Install dependencies

```bash
pip install flask flask-cors google-genai
```

### 2. Set your API key

```bash
export GEMINI_API_KEY='your_key_here'
```

### 3. Run

```bash
python app.py
```

`obsidia_data.json` is created automatically on first run with default starting values. No database setup required.

Then open `http://localhost:8080` in your browser.

---

## How to Play

Type an action in the console at the bottom and press **Transmit** (or Enter). Ren will do it. Obsidia will describe what happens.

- **Actions** — plain text: `Walk to the Ridgeline.` or `Check the atmospheric processor.`
- **Dialogue** — wrap in quotes: `"Is anything out there, Bloop?"`

Shift+Enter adds a new line without submitting.

The left sidebar tracks terraforming progress in real time. The visualizer panel at the top displays AI-generated scene images when the narrator triggers them.

---

## Sidebar Controls

| Control | What it does |
|---|---|
| **Narration Voice** | Enables text-to-speech for Obsidia's narration using your browser's speech engine |
| **No Images** | Disables the visualizer and skips image rendering. Does not prevent the backend from generating images — it only suppresses display on the client. |
| **Save Mission Log** | Downloads the full save as a `.json` file |
| **Load Mission Log** | Restores a previously saved `.json` file, replacing current game state |

---

## Data Storage

All game data is persisted locally in `obsidia_data.json`, stored next to the server. The file is created automatically if it doesn't exist. Its structure:

```json
{
  "messages":  [],
  "game_state": { "terra_a": 2, "terra_t": 14, ... },
  "summaries":  []
}
```

Generated scene images are saved as PNG files under `static/photos/` and served by Flask's static file handler.

Use the **Save Mission Log** and **Load Mission Log** buttons in the sidebar to export and import the full save file as a portable `.json` download.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python / Flask |
| AI Narrator | Google Gemini (`gemini-3-flash-preview`) |
| Image Generation | Google Imagen (`imagen-4.0-fast-generate-001`) |
| Data Storage | Local JSON file (`obsidia_data.json`) |
| Image Storage | Local filesystem (`static/photos/`) |
| Frontend | Vanilla HTML/CSS/JS |
| Audio | Tone.js (procedural SFX), Web Speech API (TTS) |
| Fonts | Cinzel, Space Mono (Google Fonts) |

---

## Project Structure

```
├── app.py                  # Flask backend, API routes, LLM logic
├── json_store.py           # Local JSON file reads/writes (replaces Supabase)
├── obsidia_data.json       # Auto-created on first run; holds all game data
└── templates/
    └── index.html          # Frontend (single-file UI)
```

---

## API Routes

| Route | Method | Description |
|---|---|---|
| `/api/action` | POST | Submit an action. Returns narrator response and any image events. |
| `/api/dialog` | POST | Submit dialogue. Treated as `Ren said: "..."` in narrator context. |
| `/api/state` | GET | Returns current game state. |
| `/api/history` | GET | Returns full conversation history (up to 100 messages). |
| `/api/reset_state` | POST | Resets game state to initial values. Does not clear message history. |
| `/api/archive` | POST | Manually triggers the archivist summarization pass. |
| `/api/context` | GET | Debug route — returns the current context window and game state. |
| `/api/save` | GET | Downloads the full `obsidia_data.json` as a save file. |
| `/api/load` | POST | Accepts a `.json` save file and restores it as the current game state. |

---

## Game State

The narrator emits structured tags at the end of each response. The backend parses these and updates the local JSON store. All values are whole numbers clamped 0–100 (except mission year, which increments freely).

| Tag | Values | Description |
|---|---|---|
| `TERRA_SYNC` | A, T, W, F, S | Atmosphere, Temperature, Water Cycle, Flora, Stability — relative deltas each turn |
| `SYS_INT_COH` | I%, C% | Ren's Integrity and Coherence — set as absolute values |
| `MISSION_LOG` | Y | Mission year elapsed — cumulative |

The frontend syncs state from `/api/state` after every turn and animates the sidebar bars accordingly.
