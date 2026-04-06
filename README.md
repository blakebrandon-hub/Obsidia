# Tales of Obsidia

A slow, atmospheric text-based game about terraforming a dead planet over 300 years. You play as Ren, an android left alone with a small companion robot named Bloop, a hub full of machinery, and three centuries of work ahead of you. The world is narrated by an omniscient voice called Obsidia, which witnesses and describes — it never speaks for Ren, never editorializes, never reassures.

---

## What It Is

Tales of Obsidia is a single-player narrative experience backed by a live AI narrator. Each action you type is sent to a Flask backend, which builds a context window from recent history and rolling summaries, calls the Gemini API, and streams back prose. The narrator also manages a structured game state — atmosphere, temperature, water cycle, flora seeding, stability, Ren's integrity and coherence, and mission year — updating it silently in response to what happens in the story.

The game supports procedural image generation: during meaningful moments, the narrator emits a `[GENERATE_IMAGE]` tag, which triggers an image model and displays the result in the visualizer panel.

---

## Screenshots 

<img width="2560" height="1440" alt="Screenshot 2026-04-06 150739" src="https://github.com/user-attachments/assets/6bbc14ca-6824-4b82-8ac4-dc1f869406d6" />

<img width="1366" height="768" alt="Screenshot 2026-04-06 153725" src="https://github.com/user-attachments/assets/f9e4dda1-eda4-46ed-8915-557357a38b3b" />

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python / Flask |
| AI Narrator | Google Gemini (`gemini-3-flash-preview`) |
| Image Generation | Google Imagen (`imagen-4.0-fast-generate-001`) |
| Database | Supabase (Postgres) |
| Image Storage | Supabase Storage |
| Frontend | Vanilla HTML/CSS/JS |
| Audio | Tone.js (procedural SFX), Web Speech API (TTS) |
| Fonts | Cinzel, Space Mono (Google Fonts) |

---

## Project Structure

```
├── app.py                  # Flask backend, API routes, LLM logic
├── supabase_client.py      # All Supabase reads/writes
└── templates/
    └── index.html          # Frontend (single-file UI)
```

---

## Setup

### 1. Install dependencies

```bash
pip install flask flask-cors google-genai supabase
```

### 2. Configure API keys

Open `app.py` and `supabase_client.py` and set your credentials directly, or move them to environment variables:

```python
# app.py
google_key = 'YOUR_GOOGLE_API_KEY'

# supabase_client.py
url = 'YOUR_SUPABASE_URL'
key = 'YOUR_SUPABASE_ANON_KEY'
```

### 3. Set up Supabase tables

You need three tables in your Supabase project:

**`obsidia`** — the unified message log
```sql
create table obsidia (
  id bigint generated always as identity primary key,
  role text,
  content text,
  created_at timestamptz default now()
);
```

**`game_state`** — a single row holding all terraforming values
```sql
create table game_state (
  id int primary key default 1,
  terra_a int, terra_t int, terra_w int, terra_f int, terra_s int,
  sys_bi int, sys_bc int,
  rel_y int, rel_d int
);

-- Insert the starting row
insert into game_state values (1, 2, 14, 0, 0, 8, 100, 100, 0, 0);
```

**`summaries`** — rolling archivist summaries for long-context management
```sql
create table summaries (
  id bigint generated always as identity primary key,
  content text,
  covers_up_to bigint,
  created_at timestamptz default now()
);
```

You also need a **Supabase Storage bucket** named `obsidia-world` with public read access for generated images.

### 4. Run

```bash
python app.py
```

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

---

## API Routes

| Route | Method | Description |
|---|---|---|
| `/api/action` | POST | Submit an action. Returns narrator response and any image events. |
| `/api/dialog` | POST | Submit dialogue. Treated as `Ren said: "..."` in narrator context. |
| `/api/state` | GET | Returns current game state from Supabase. |
| `/api/history` | GET | Returns full conversation history (up to 100 messages). |
| `/api/reset_state` | POST | Resets game state to initial values. Does not clear message history. |
| `/api/archive` | POST | Manually triggers the archivist summarization pass. |
| `/api/context` | GET | Debug route — returns the current context window and game state. |

---

## Game State

The narrator emits structured tags at the end of each response. The backend parses these and updates Supabase. All values are whole numbers clamped 0–100 (except mission year, which increments freely).

| Tag | Values | Description |
|---|---|---|
| `TERRA_SYNC` | A, T, W, F, S | Atmosphere, Temperature, Water Cycle, Flora, Stability — relative deltas each turn |
| `SYS_INT_COH` | I%, C% | Ren's Integrity and Coherence — set as absolute values |
| `MISSION_LOG` | Y | Mission year elapsed — cumulative |

The frontend syncs state from `/api/state` after every turn and animates the sidebar bars accordingly.

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

---

## Save & Load

Use the browser's save/load controls (if wired to your instance) to export a full snapshot of game state and message history as a `.json` file. Loading a save re-renders the entire scroll and restores the sidebar.

---

## Notes

- The game starts fresh automatically if no messages exist in Supabase — it runs a silent `Look around.` action to generate the opening scene.
- The `PAINTER_MODEL` (`imagen-4.0-fast-generate-001`) requires specific API access. If you get a permission error, check that your key has image generation enabled or substitute a different Imagen model string.
- Resetting state via `/api/reset_state` does not clear the message log. To fully restart, truncate the `obsidia` and `summaries` tables in Supabase directly.
