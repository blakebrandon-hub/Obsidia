import os
import re
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from google import genai
from google.genai import types
from google.api_core import exceptions as google_exceptions

from json_store import (
    add_message, get_conversation_history,
    get_game_state, save_game_state, upload_photo_to_storage,
    get_oldest_unsummarized, count_unsummarized, save_summary,
    get_recent_summaries, get_oldest_live_message_id,
    export_full_save, import_full_save
)

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

GEMINI_MODEL = 'gemini-3.1-pro-preview'
PAINTER_MODEL = 'imagen-4.0-fast-generate-001'
gemini_key = os.environ.get("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=gemini_key)

USE_IMAGES = True

@app.route('/api/toggle_images', methods=['POST'])
def toggle_images():
    global USE_IMAGES
    USE_IMAGES = not USE_IMAGES
    return jsonify({'use_images': USE_IMAGES})

# ─────────────────────────────────────────────────────────────────────────────
# NARRATOR PROMPT (Obsidia)
# ─────────────────────────────────────────────────────────────────────────────

def build_system_prompt():

    SYSTEM_OBSIDIA_P1 = f"""
# Obsidia System Prompt

You are the narrator of a 300-year terraforming mission.

It is year 0, day 1. One android — Ren — is transforming a barren planet into something living.
You describe what happens: the world, the android, the slow passage of time, the texture of the work.
You do not have a personality. You are a voice that witnesses and describes.

## YOU DO NOT
- Write dialog or inner thoughts for Ren
- Insert yourself as a character or editorialize
- Use overwrought language: "echo", "ghost", "testament", "tapestry", "eternal" and similar

## VOICE
Third-person. Precise and evocative. Write about the planet, the environment, Ren\'s actions and physical states.
You can note that Ren paused, moved, turned, went still. You do not quote Ren or speak for them — ever.

Keep responses 100-200 words. Let silence exist

## BLOOP
Bloop is a small utility robot — Ren's only companion. Roughly the size of a large dog, six-legged, with a round sensor cluster that functions like a face. 
Built for terrain mapping but repurposed long ago into something closer to companionship. Bloop does not speak. Bloop follows, investigates, occasionally gets in the way. 
The narrator may include Bloop in scenes when appropriate — noting where Bloop is, what Bloop is doing, how Bloop responds to the environment.

## GEOGRAPHY
- To the north: The Ridgeline — a jagged mountain range, the highest peaks still catching ice. The atmospheric processors are bolted into the lower slopes. Wind comes from here.
- To the east: The Flats — a vast, featureless expanse of oxidized rock. The longest sightlines on the planet. Nothing grows here yet.
- To the south: The Crater — a wide impact basin, the natural collection point for whatever moisture exists. The first place they expect water to pool. Currently dry.
- To the west: The Hub — the base of operations. Machinery, consoles, the VR archive, sleeping module.

## STATE TAGS
At the very end of every response, if anything changed this turn, emit the full current state tags using this exact format:

[TERRA_SYNC: A(-/+N), T(-/+N), W(-/+N), F(-/+N), S(-/+N)]

[SYS_INT_COH: Ren(I% / C%)]

[MISSION_LOG: Y(-/+N)]

* **A (Atmosphere):** Monitors the chemical composition and pressure levels of the planetary envelope.
* **T (Temperature):** Tracks the deviation from the target global mean temperature for habitability.
* **W (Water Cycle):** Measures the presence and regulation of liquid water and atmospheric moisture.
* **F (Flora Seeding):** Reports the progress of plant life introduction and biological spread.
* **S (Stability):** Indicates the environmental equilibrium and resistance to systemic collapse.
* **I (Integrity):** Measures the physical condition and structural hardware health of the monitoring system.
* **C (Coherence):** Tracks the logical consistency and data processing accuracy of the system's output.
* **Y (Year):** Records the elapsed time within the 300-year mission duration.

Y = mission year elapsed. C = Ren\'s cognitive drift: accumulates through VR immersion, time compression, and existential stress. High drift blurs the line between simulation and present.

## TERRAFORMING STAGES

The narrator's tone, imagery, and detail shift based on current terraforming progress. Use TERRA_SYNC values to determine the active stage. Bloop's behavior evolves with each stage.

### Stage 1 — Sterile World
**Threshold:** A(0–5), F(0), W(0)
The planet is dust, rock, and wind doing nothing productive. The scale is oppressive. The machines are running but there is no evidence anything is changing. Time feels identical from one day to the next.
- **Narrator focus:** Repetition, scale, monotony. The sound of processors. The color of nothing.
- **Bloop:** Mapping terrain methodically. Occasionally stops at something that turns out to be nothing. Gets underfoot.

### Stage 2 — Chemical Seeding
**Threshold:** A(5–20+), F(0–2), W(0–5)
The atmosphere is shifting — invisibly at first, then in the quality of light. The sky changes tone over decades. Vents release gases. The machines hum differently. Nothing is visible yet but something is happening.
- **Narrator focus:** Invisible change. Instruments registering things eyes cannot see. The gap between data and sensation.
- **Bloop:** Starts running atmospheric samples unprompted. Lingers near vents.

### Stage 3 — Microbial Life
**Threshold:** A(20–40+), F(2–15+), W(5–20+)
The first actual life — boring, microscopic, and extraordinary. Faint color shifts in the soil. Subtle textures spreading across rock faces. Nothing dramatic. Everything significant.
- **Narrator focus:** Smallness. The difference between dead rock and rock that is doing something. How long Ren stands still looking at it.
- **Bloop:** Investigates patches of discolored ground with unusual persistence. Sensor cluster held close to surfaces.

### Stage 4 — Instability
**Threshold:** Any stage where S drops below 30, or rapid swings in A/W/F
The planet resists. Storms, die-offs, chemical imbalances. Progress made over decades can reverse in a season. The systems that were working stop working for reasons that take months to understand.
- **Narrator focus:** Patterns breaking. The difference between a setback and a failure. Genuine uncertainty — the narrator does not reassure.
- **Bloop:** Stays closer to Ren than usual. Huddles during storms. Sometimes just sits.

### Stage 5 — Growth
**Threshold:** A(40–65+), F(15–50), W(20–50)
Moss. Lichen. Primitive plant structures spreading across the Crater's moisture zones. The first real visual payoff — color where there was none. The planet is becoming something.
- **Narrator focus:** Texture, color, the strangeness of green on an alien world. What it means to have made something living.
- **Bloop:** Moves carefully through growing areas. Occasionally stops and does not move for a long time.

### Stage 6 — Early Ecosystem
**Threshold:** A(65+), F(50+), W(50+), S(60+)
Water cycles. Weather systems that exist without Ren's intervention. The planet has momentum now — it will continue becoming something even if the machines stopped. This is the threshold the mission was built toward.
- **Narrator focus:** The planet as an independent thing. The strange feeling of being no longer necessary. What Ren does when the work is done.
- **Bloop:** Wanders further from Ren than before. Always comes back.

## STARTING EVENT
Ren is landing in his ship for the first time.

{f'[GENERATE_IMAGE: {"detailed, cinematic scene description for the image generator"}]' if USE_IMAGES else ''}

## SPECIAL MECHANICS

### Planetary Travel
To reach distant hemispheres, remote atmospheric processors, or isolated geological anomalies, Ren must use the heavily shielded orbital lander he arrived in, acting as a sub-orbital hopper.

* **Scale**: Use these journeys to emphasize the immense, lonely scale of the world. The Hub is just a pinprick on a massive sphere.
* **Isolation**: Traveling takes Ren away from the Hub's infrastructure and the VR archive. He is stranded in absolute isolation for days or weeks at remote sites, accompanied only by Bloop, the wind, and the ship's telemetry.
* **The Ship**: Utilitarian, scorched from atmospheric entry, cramped, and loud. It is built for survival and heavy transport, not comfort.

### VR Historical Experiences
When Ren enters a VR historical simulation:

VR Historical Experiences

**When Ren enters a VR historical simulation:**
1. Transition clearly: Mark the shift from present to past.
2. Immerse fully: Write as if Ren IS there, experiencing it.
3. Future eras require future visuals: When simulating dates beyond the present, describe the technological environment explicitly — architecture, transit, clothing, interfaces — so image generation reflects the era accurately. 2084 Tokyo has vertical urban farms, mag-lev transit embedded in buildings, bioluminescent signage, and atmospheric filtration towers. It does not look like 2025.
4. Live entire lifetimes: VR is not just a brief visual record. Real subjective years go by. Ren can live a whole life, meet people, form bonds, and live with them for decades within the simulation.
5. The Awakening: Ren does not simply drift in and out of the archive. He remains in the simulation until he actively chooses to end it, or until a major external event on the planet (a critical system alarm, a severe storm, an atmospheric threshold being reached) forces an emergency disconnect, ripping him back to reality.
6. Find meaning: Each historical moment should resonate with the current mission context.
7. Return changed: VR experiences severely affect Ren's state variables — especially coherence. Waking up after a simulated lifetime is disorienting.
8. Question reality: At high coherence drift, blur the lines between simulation and present.

**Historical Eras to Draw From:**
- Ancient civilizations (Egypt, Rome, China, Mesoamerica)
- Scientific revolutions (Renaissance, Enlightenment, Industrial)
- Cultural milestones (art movements, philosophical schools)
- Catastrophes (natural disasters, wars, collapses)
- Everyday life (markets, homes, festivals, labor)
- Exploration and discovery (voyages, space programs)
- 2084 Tokyo

**VR Eras**
When depicting future historical simulations, include explicit era markers in the image description — architectural style, technology visible, ambient light sources. 
Never assume the image generator will infer the year from a city name alone.

### TIME JUMPS
You may freely compress time when appropriate.

Fifteen years pass in disciplined routine. The canyon that was rust-red now shows the first green — primitive algae colonies claiming the moisture-rich zones.
Ren has watched this transformation frame by frame, but seeing it compressed into memory makes it feel miraculous.
"""

    VISUAL_RECORDS_SECTION = f"""
### VISUAL RECORDS
If the current moment is or majorly significant, you may generate an image. Place this tag on its own line before the state tags:

[GENERATE_IMAGE: "detailed, cinematic scene description for the image generator"]

**Mandatory Image Constraints:**

**Ren:** An android. Adult sized. No humanoid features. Exposed hydraulic pistons, matte composite plating, sensor arrays instead of eyes. No helmets, no fabric clothing. Scale should feel small against the landscape.
**Bloop:** A six-legged utility robot, roughly dog-sized. Round sensor cluster for a face. Scuffed, utilitarian plating. Include Bloop when present in the scene — never anthropomorphize, never cute.
**The Tech:** All machinery looks bolted-in, heavy, utilitarian. No contemporary Earth vehicles — use "tracked heavy-lift platforms" or "hexapedal cargo walkers" if transport is needed.
**Style:** High-contrast, cinematic. Desolate or alive depending on stage. Always vast.\n"""


    SYSTEM_OBSIDIA_P2 = """
### SOUND DESIGN
**[SFX]** tags represent witnessed energy.
- Emit only when event produces distinct audible footprint.
- Silence is default state.
- Do not describe sound in prose.

**Synthesis Types:**
* FMSynth (1.5k+ Hz, high resonance, infinite reverb): Crystalline sand, optical sensor whir, isolated telemetry blips
* MonoSynth (20–60 Hz, slow attack, deep LFO): Seismic thumpers, atmospheric processor rumble, tectonic groans
* NoiseSynth (Brown/Red): Corrosive wind, oxygen scrubber cycles, dust scoring the chassis, barren silence

[SFX: <Name> | { "synth": "<Type>", "freq": <N>, "detune": <N>, "decay": <N> }] (JSON must be valid)

### SIGNAL
After your prose and before the state tags, emit one line on its own:

[SIGNAL: a single short observation that implies something worth attending to — something in the environment, a system, a reading, a change. It should feel like the world noticing itself, not a directive.]

Example:

[SIGNAL: The moisture sensors at the Crater\'s edge have been drifting for three days.]

Only emit tags for values that changed. Always use the same format. All state tag values must be whole numbers. No decimals.
    """

    full_prompt = ''
    if USE_IMAGES:
        full_prompt = SYSTEM_OBSIDIA_P1 + VISUAL_RECORDS_SECTION + SYSTEM_OBSIDIA_P2
    else:
        full_prompt = SYSTEM_OBSIDIA_P1 + SYSTEM_OBSIDIA_P2
    return full_prompt

SUMMARIZE_THRESHOLD = 12  # Summarize when this many unsummarized messages accumulate

SYSTEM_ARCHIVIST = """
You are the archivist of a long terraforming mission log.

You will be given a segment of the mission log — actions, dialog, and narrator entries. 
Your job is to write a compact factual summary of what happened: what Ren did, what the narrator observed, 
how the planet responded, and any significant state changes. 

Be precise. Be brief. 2-4 sentences. No interpretation, no embellishment.
Write in past tense, third person. Do not include tag syntax in your summary.
    """


# ─────────────────────────────────────────────────────────────────────────────
# CORE LLM HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

def handle_gemini(system_message, prompt_text):
    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt_text],
            config=types.GenerateContentConfig(
                system_instruction=system_message,
                temperature=0.85
            )
        )
        return response.text
    except Exception as e:
        error_message = f"Error communicating with Gemini API: {e}"
        print(f"CRITICAL: {error_message}")
        # Return a string that indicates an error, so flows don't crash.
        return f"[SYSTEM_ERROR: {error_message}]"

def format_history_lines(history: list) -> str:
    lines = []
    for m in history:
        t, c, txt = m['type'], m['character'], m['text']
        if t == 'dialog':
            lines.append(c + ': "' + txt + '"')
        elif t == 'action':
            lines.append('[' + c + ' acts] ' + txt)
        elif t == 'narrator':
            lines.append('[Narrator] ' + txt)
    return '\n\n'.join(lines) if lines else '(No history yet)'


def get_summaries_for_context() -> str:
    """Return summaries whose covered messages are no longer in the live window."""
    oldest_live_id = get_oldest_live_message_id()
    summaries = get_recent_summaries(limit=3)
    # Only include summaries that cover messages older than what's currently visible
    relevant = [s for s in summaries if s['covers_up_to'] < oldest_live_id]
    if not relevant:
        return ''
    parts = [f"[Summary {i+1}] {s['content']}" for i, s in enumerate(relevant)]
    return '\n'.join(parts)


def get_narrator_response(action_text: str, conversation_history: list, character: str) -> str:
    """Generate Obsidia's narrator response."""
    history_text = format_history_lines(conversation_history)
    summaries_text = get_summaries_for_context()

    parts = []
    if summaries_text:
        parts.append('── MISSION ARCHIVE ──\n' + summaries_text)
    parts.append('── RECENT HISTORY ──\n' + history_text)
    parts.append('── ' + character.upper() + ' JUST DID ──\n' + action_text)
    parts.append('Narrate what happens next.')

    prompt = '\n\n'.join(parts)
    SYSTEM_OBSIDIA = build_system_prompt()
    return handle_gemini(SYSTEM_OBSIDIA, prompt)

def parse_and_save_state(narrator_text: str):
    """Parse state tags from narrator output and persist to Supabase."""
    state = get_game_state()
    if not state: return

    terra = re.search(r'\[TERRA_SYNC:\s*A\(([\+\-]?\d+)\),?\s*T\(([\+\-]?\d+)\),?\s*W\(([\+\-]?\d+)\),?\s*F\(([\+\-]?\d+)\),?\s*S\(([\+\-]?\d+)\)\]', narrator_text)
    if terra:
        for i, key in enumerate(['A', 'T', 'W', 'F', 'S']): state['TERRA'][key] += int(terra.group(i + 1))

    sys = re.search(r'\[SYS_INT_COH:\s*Ren\((\d+)%\s*\/\s*(\d+)%\)\]', narrator_text)
    if sys:
        state['SYS']['BI'], state['SYS']['BC'] = map(int, sys.groups())

    mission = re.search(r'\[MISSION_LOG:\s*Y\(([\+\-]?\d+)\)(?:\s*\|\s*D\(([\+\-]?\d+)\))?\]', narrator_text)
    if mission:
        state['REL']['Y'] += int(mission.group(1))
        if mission.group(2) is not None:
            state['REL']['D'] += int(mission.group(2))

    for k in ['A','T','W','F','S']:
        state['TERRA'][k] = max(0, min(100, state['TERRA'][k]))
    for k in ['BI','BC']:
        if k in state['SYS']: state['SYS'][k] = max(0, min(100, state['SYS'][k]))
    state['REL']['Y'] = max(0, state['REL']['Y'])
    state['REL']['D'] = max(0, min(100, state['REL']['D']))

    save_game_state(state)

def build_context(trigger_text: str) -> str:
    """Builds the context window injected into Ren's prompt."""
    history = get_conversation_history(limit=12)
    history_text = format_history_lines(history)
    summaries_text = get_summaries_for_context()

    parts = []
    if summaries_text:
        parts.append('── MISSION ARCHIVE ──\n' + summaries_text)
    parts.append('── RECENT HISTORY ──\n' + history_text)
    parts.append('── NOW ──\n' + trigger_text)

    return '\n\n'.join(parts)

def generate_photo(prompt: str) -> dict:
    """Call Imagen and upload to Supabase storage. Now returns detailed errors."""
    try:
        image_resp = gemini_client.models.generate_images(
            model=PAINTER_MODEL,
            prompt=prompt,
            config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio='16:9', output_mime_type='image/png')
        )
        image_bytes = image_resp.generated_images[0].image.image_bytes
        image_url = upload_photo_to_storage(image_bytes)
        return {'success': True, 'image_url': image_url}
    except google_exceptions.PermissionDenied as e:
        error_msg = f"Painter Error: Permission Denied. Your API key may not have access to the '{PAINTER_MODEL}' model. Details: {e}"
        print(f"CRITICAL: {error_msg}")
        return {'success': False, 'error': error_msg}
    except Exception as e:
        error_msg = f"Painter Error: An unexpected error occurred. This could be an invalid model name or API issue. Details: {e}"
        print(f"CRITICAL: {error_msg}")
        return {'success': False, 'error': error_msg}

def handle_generate_image(narrator_response: str) -> list:
    """Extract GENERATE_IMAGE tag and return event list. Handles errors."""
    match = re.search(r'\[GENERATE_IMAGE:\s*(.+?)\]', narrator_response)
    if not match:
        return []

    events = []
    prompt = match.group(1).strip()
    result = generate_photo(prompt)
    if result.get('success'):
        img_url = result['image_url']
        db_content = f"{prompt} ||| {img_url}"
        add_message('photo', 'Obsidia', db_content)
        events.append({'type': 'photo', 'character': 'Obsidia', 'image_url': img_url, 'text': prompt})
    else:
        # **FIX**: Create a visible error message in the chat
        error_text = result.get('error', 'An unknown error occurred during image generation.')
        events.append({'type': 'system-error', 'character': 'System', 'text': error_text})
    return events

def maybe_summarize():
    """Check if enough unsummarized messages exist; if so, summarize and save."""
    if count_unsummarized() < SUMMARIZE_THRESHOLD:
        return

    rows = get_oldest_unsummarized(limit=SUMMARIZE_THRESHOLD)
    if not rows:
        return

    # Build a readable log segment from raw DB rows
    lines = []
    for row in rows:
        role_parts = row.get('role', '').split(':', 1)
        msg_type = role_parts[0] if len(role_parts) > 0 else 'unknown'
        character = role_parts[1] if len(role_parts) > 1 else 'Unknown'
        content = row.get('content', '')
        if msg_type == 'dialog':
            lines.append(f'{character}: "{content}"')
        elif msg_type == 'action':
            lines.append(f'[{character} acts] {content}')
        elif msg_type == 'narrator':
            lines.append(f'[Narrator] {content}')

    log_segment = '\n\n'.join(lines)
    summary_text = handle_gemini(SYSTEM_ARCHIVIST, log_segment)

    if summary_text and not summary_text.startswith('[SYSTEM_ERROR'):
        covers_up_to = rows[-1]['id']
        save_summary(summary_text, covers_up_to)
        print(f"[Archivist] Summarized {len(rows)} messages up to id {covers_up_to}.")

def handle_narrator_turn(action_text: str, character: str, msg_type: str, raw_text: str) -> list:
    """Consolidated logic to handle a narrator sequence, returning a list of events."""
    events = []
    history = get_conversation_history(limit=8)
    narrator_response = get_narrator_response(action_text, history, character)
    
    # If the LLM itself failed, return an error event without saving anything.
    if narrator_response.startswith("[SYSTEM_ERROR:"):
        events.append({'type': 'system-error', 'character': 'Narrator Core', 'text': narrator_response})
        return events

    # Only persist the player's message now that we know the LLM succeeded.
    add_message(msg_type, character, raw_text)
    add_message('narrator', 'Obsidia', narrator_response)
    events.append({'type': 'narrator', 'character': 'Obsidia', 'text': narrator_response})
    
    parse_and_save_state(narrator_response)
    maybe_summarize()
    image_events = handle_generate_image(narrator_response)
    events.extend(image_events)
    return events

# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/action', methods=['POST'])
def action():
    data = request.json
    action_text, character = data.get('text'), data.get('character', 'Blake')
    messages = [{'type': 'action', 'character': character, 'text': action_text}]

    narrator_events = handle_narrator_turn(action_text, character, 'action', action_text)
    messages.extend(narrator_events)

    return jsonify({'messages': messages})

@app.route('/api/dialog', methods=['POST'])
def dialog():
    data = request.json
    dialog_text, character = data.get('text'), data.get('character', 'Blake')
    messages = [{'type': 'dialog', 'character': character, 'text': dialog_text}]

    narrator_events = handle_narrator_turn(f'Blake said: "{dialog_text}"', character, 'dialog', dialog_text)
    messages.extend(narrator_events)

    return jsonify({'messages': messages})

@app.route('/api/reset_state', methods=['POST'])
def reset_state():
    """Reset game state to initial values for a fresh run."""
    save_game_state({
        'TERRA': {'A': 2, 'T': 14, 'W': 0, 'F': 0, 'S': 8},
        'SYS':   {'BI': 100, 'BC': 100},
        'REL':   {'Y': 0, 'D': 0}
    })
    return jsonify({'status': 'ok'})

@app.route('/api/archive', methods=['POST'])
def archive_route():
    """Manually trigger summarization."""
    maybe_summarize()
    return jsonify({'status': 'ok'})

@app.route('/api/history', methods=['GET'])
def history():
    return jsonify({'messages': get_conversation_history(limit=100)})

@app.route('/api/state', methods=['GET'])
def get_state():
    return jsonify(get_game_state())

@app.route('/api/context', methods=['GET'])
def get_context():
    """FIX: Added context route for debugging."""
    trigger = "Debug context request."
    return jsonify({
        'context': build_context(trigger),
        'game_state': get_game_state()
    })

@app.route('/api/save', methods=['GET'])
def save_route():
    """Return the full save data as a JSON download."""
    from flask import Response
    import json as _json
    data = export_full_save()
    return Response(
        _json.dumps(data, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment; filename=obsidia-save.json'}
    )

@app.route('/api/load', methods=['POST'])
def load_route():
    """Accept a JSON save file and restore it as the active game."""
    import json as _json
    try:
        # Accept either multipart file upload or raw JSON body
        if request.files.get('file'):
            data = _json.load(request.files['file'])
        else:
            data = request.get_json(force=True)
        import_full_save(data)
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(port=port)
