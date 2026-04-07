"""
json_store.py — local JSON file backend replacing supabase_client.py

Data is persisted in ./obsidia_data.json next to the server.
Structure:
{
  "messages":  [ { "id": int, "role": "type:character", "content": str, "created_at": iso } ],
  "game_state": { ... },
  "summaries":  [ { "id": int, "content": str, "covers_up_to": int, "created_at": iso } ]
}
"""

import json
import os
import uuid
import base64
from datetime import datetime, timezone

DATA_FILE = os.path.join(os.path.dirname(__file__), 'obsidia_data.json')

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _load() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return _default_db()

def _save(db: dict):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

def _default_db() -> dict:
    return {
        "messages": [],
        "game_state": {
            "terra_a": 2,  "terra_t": 14, "terra_w": 0, "terra_f": 0, "terra_s": 8,
            "sys_bi":  100, "sys_bc":  100,
            "rel_y":   0,   "rel_d":   0
        },
        "summaries": []
    }

def _next_msg_id(db: dict) -> int:
    if not db["messages"]:
        return 1
    return db["messages"][-1]["id"] + 1

def _next_sum_id(db: dict) -> int:
    if not db["summaries"]:
        return 1
    return db["summaries"][-1]["id"] + 1


# ─────────────────────────────────────────────────────────────────────────────
# UNIFIED CONVERSATION LOG
# ─────────────────────────────────────────────────────────────────────────────

def add_message(message_type: str, character: str, content: str) -> dict:
    try:
        db = _load()
        row = {
            "id": _next_msg_id(db),
            "role": f"{message_type}:{character}",
            "content": content,
            "created_at": _now()
        }
        db["messages"].append(row)
        _save(db)
        return row
    except Exception as e:
        print(f"CRITICAL: Failed to add message. Error: {e}")
        return None


def get_conversation_history(limit: int = 24) -> list:
    try:
        db = _load()
        messages = db["messages"][-limit:]
        history = []
        for msg in messages:
            role_parts = msg.get('role', '').split(':', 1)
            msg_type  = role_parts[0] if len(role_parts) > 0 else 'unknown'
            character = role_parts[1] if len(role_parts) > 1 else msg.get('role', 'Unknown')
            content   = msg.get('content', '')

            if msg_type == 'photo' and ' ||| ' in content:
                text_prompt, image_url = content.split(' ||| ', 1)
                history.append({'type': msg_type, 'character': character,
                                 'text': text_prompt, 'image_url': image_url})
            else:
                history.append({'type': msg_type, 'character': character, 'text': content})
        return history
    except Exception as e:
        print(f"CRITICAL: Could not fetch conversation history. Error: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# GAME STATE
# ─────────────────────────────────────────────────────────────────────────────

def get_game_state() -> dict:
    try:
        db  = _load()
        row = db.get("game_state", {})
        if not row:
            return {}
        return {
            'TERRA': {'A': row['terra_a'], 'T': row['terra_t'], 'W': row['terra_w'],
                      'F': row['terra_f'], 'S': row['terra_s']},
            'SYS':   {'BI': row['sys_bi'], 'BC': row['sys_bc']},
            'REL':   {'Y': row['rel_y'],   'D': row['rel_d']}
        }
    except Exception as e:
        print(f"CRITICAL: Could not fetch game state. Error: {e}")
        return {}


def save_game_state(state: dict):
    try:
        db = _load()
        t, s, r = state.get('TERRA', {}), state.get('SYS', {}), state.get('REL', {})
        db["game_state"].update({
            'terra_a': t.get('A'), 'terra_t': t.get('T'), 'terra_w': t.get('W'),
            'terra_f': t.get('F'), 'terra_s': t.get('S'),
            'sys_bi':  s.get('BI'), 'sys_bc':  s.get('BC'),
            'rel_y':   r.get('Y'), 'rel_d':   r.get('D'),
        })
        _save(db)
    except Exception as e:
        print(f"CRITICAL: Failed to save game state. Error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARIES
# ─────────────────────────────────────────────────────────────────────────────

def get_message_count() -> int:
    try:
        return len(_load()["messages"])
    except Exception as e:
        print(f"CRITICAL: Could not count messages. Error: {e}")
        return 0


def get_oldest_unsummarized(limit: int = 12) -> list:
    try:
        db = _load()
        last_covered_id = 0
        if db["summaries"]:
            last_covered_id = max(s['covers_up_to'] for s in db["summaries"])
        unsummarized = [m for m in db["messages"] if m['id'] > last_covered_id]
        return unsummarized[:limit]
    except Exception as e:
        print(f"CRITICAL: Could not fetch unsummarized messages. Error: {e}")
        return []


def count_unsummarized() -> int:
    try:
        db = _load()
        last_covered_id = 0
        if db["summaries"]:
            last_covered_id = max(s['covers_up_to'] for s in db["summaries"])
        return sum(1 for m in db["messages"] if m['id'] > last_covered_id)
    except Exception as e:
        print(f"CRITICAL: Could not count unsummarized messages. Error: {e}")
        return 0


def save_summary(content: str, covers_up_to: int):
    try:
        db = _load()
        db["summaries"].append({
            "id": _next_sum_id(db),
            "content": content,
            "covers_up_to": covers_up_to,
            "created_at": _now()
        })
        _save(db)
    except Exception as e:
        print(f"CRITICAL: Could not save summary. Error: {e}")


def get_recent_summaries(limit: int = 3) -> list:
    try:
        db = _load()
        summaries = sorted(db["summaries"], key=lambda s: s['covers_up_to'])
        return summaries[-limit:]
    except Exception as e:
        print(f"CRITICAL: Could not fetch summaries. Error: {e}")
        return []


def get_oldest_live_message_id() -> int:
    try:
        db = _load()
        msgs = db["messages"][-12:]
        if not msgs:
            return 0
        return min(m['id'] for m in msgs)
    except Exception as e:
        print(f"CRITICAL: Could not fetch oldest live message id. Error: {e}")
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# PHOTO STORAGE — saves image files locally as PNG, returns a relative URL
# ─────────────────────────────────────────────────────────────────────────────

PHOTO_DIR = os.path.join(os.path.dirname(__file__), 'static', 'photos')

def upload_photo_to_storage(image_bytes: bytes) -> str:
    """Save image bytes to ./static/photos/<uuid>.png and return a URL path."""
    os.makedirs(PHOTO_DIR, exist_ok=True)
    file_name = f"{uuid.uuid4()}.png"
    file_path = os.path.join(PHOTO_DIR, file_name)
    with open(file_path, 'wb') as f:
        f.write(image_bytes)
    # Return a URL that Flask will serve via its static route
    return f"/static/photos/{file_name}"


# ─────────────────────────────────────────────────────────────────────────────
# FULL SAVE / LOAD  (used by /api/save and /api/load endpoints)
# ─────────────────────────────────────────────────────────────────────────────

def export_full_save() -> dict:
    """Return the entire database as a JSON-serialisable dict."""
    return _load()

def import_full_save(data: dict):
    """Overwrite the database with the provided save data."""
    # Validate it has expected keys
    for key in ("messages", "game_state", "summaries"):
        if key not in data:
            raise ValueError(f"Save data missing required key: '{key}'")
    _save(data)