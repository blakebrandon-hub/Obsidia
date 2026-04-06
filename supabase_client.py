import os
import uuid
from supabase import create_client, Client

url = ''
key = ''
supabase: Client = create_client(url, key)

# ─────────────────────────────────────────────────────────────────────────────
# UNIFIED CONVERSATION LOG
# ─────────────────────────────────────────────────────────────────────────────

def add_message(message_type: str, character: str, content: str) -> dict:
    try:
        data = {'role': f"{message_type}:{character}", 'content': content}
        result = supabase.table('obsidia').insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"CRITICAL: Failed to add message to Supabase. Error: {e}")
        return None

def get_conversation_history(limit: int = 24) -> list:
    """FIX: Added robust error handling for Supabase connection issues."""
    try:
        result = (supabase.table('obsidia')
                  .select('role, content, created_at')
                  .order('created_at', desc=True)
                  .limit(limit)
                  .execute())
        
        messages = result.data or []
        messages.reverse()
        
        history = []
        for msg in messages:
            role_parts = msg.get('role', '').split(':', 1)
            msg_type = role_parts[0] if len(role_parts) > 0 else 'unknown'
            character = role_parts[1] if len(role_parts) > 1 else msg.get('role', 'Unknown')
            content = msg.get('content', '')
            
            # Handle photo URLs saved in the content
            if msg_type == 'photo' and ' ||| ' in content:
                text_prompt, image_url = content.split(' ||| ', 1)
                history.append({'type': msg_type, 'character': character, 'text': text_prompt, 'image_url': image_url})
            else:
                history.append({'type': msg_type, 'character': character, 'text': content})
        return history
    except Exception as e:
        print(f"CRITICAL: Could not fetch conversation history from Supabase. Check credentials and connection. Error: {e}")
        return []

def get_game_state() -> dict:
    """FIX: Added robust error handling for Supabase connection issues."""
    try:
        res = supabase.table('game_state').select('*').eq('id', 1).single().execute()
        if not res.data: return {}
        row = res.data
        return {
            'TERRA': {'A': row['terra_a'], 'T': row['terra_t'], 'W': row['terra_w'], 'F': row['terra_f'], 'S': row['terra_s']},
            'SYS': {'BI': row['sys_bi'], 'BC': row['sys_bc']},
            'REL': {'Y': row['rel_y'], 'D': row['rel_d']}
        }
    except Exception as e:
        print(f"CRITICAL: Could not fetch game state from Supabase. Check table exists and credentials are correct. Error: {e}")
        return {}

def save_game_state(state: dict):
    try:
        t, s, r = state.get('TERRA', {}), state.get('SYS', {}), state.get('REL', {})
        payload = {
            'terra_a': t.get('A'), 'terra_t': t.get('T'), 'terra_w': t.get('W'), 'terra_f': t.get('F'), 'terra_s': t.get('S'),
            'sys_bi':  s.get('BI'), 'sys_bc':  s.get('BC'),
            'rel_y':   r.get('Y'), 'rel_d':   r.get('D'),
        }
        supabase.table('game_state').update(payload).eq('id', 1).execute()
    except Exception as e:
        print(f"CRITICAL: Failed to save game state to Supabase. Error: {e}")



# ─────────────────────────────────────────────────────────────────────────────
# SUMMARIES
# ─────────────────────────────────────────────────────────────────────────────

def get_message_count() -> int:
    """Return total number of messages in the log."""
    try:
        res = supabase.table('obsidia').select('id', count='exact').execute()
        return res.count or 0
    except Exception as e:
        print(f"CRITICAL: Could not count messages. Error: {e}")
        return 0

def get_oldest_unsummarized(limit: int = 12) -> list:
    """Return the oldest N messages that have not yet been summarized."""
    try:
        # Find the highest message id already covered by a summary
        res = supabase.table('summaries').select('covers_up_to').order('covers_up_to', desc=True).limit(1).execute()
        last_covered_id = res.data[0]['covers_up_to'] if res.data else 0

        res = (supabase.table('obsidia')
               .select('id, role, content, created_at')
               .gt('id', last_covered_id)
               .order('created_at', desc=False)
               .limit(limit)
               .execute())
        return res.data or []
    except Exception as e:
        print(f"CRITICAL: Could not fetch unsummarized messages. Error: {e}")
        return []

def count_unsummarized() -> int:
    """Return how many messages exist beyond the last summary boundary."""
    try:
        res = supabase.table('summaries').select('covers_up_to').order('covers_up_to', desc=True).limit(1).execute()
        last_covered_id = res.data[0]['covers_up_to'] if res.data else 0
        res = supabase.table('obsidia').select('id', count='exact').gt('id', last_covered_id).execute()
        return res.count or 0
    except Exception as e:
        print(f"CRITICAL: Could not count unsummarized messages. Error: {e}")
        return 0

def save_summary(content: str, covers_up_to: int):
    """Persist a summary and the highest message id it covers."""
    try:
        supabase.table('summaries').insert({
            'content': content,
            'covers_up_to': covers_up_to
        }).execute()
    except Exception as e:
        print(f"CRITICAL: Could not save summary. Error: {e}")

def get_recent_summaries(limit: int = 3) -> list:
    """Return the most recent N summaries."""
    try:
        res = (supabase.table('summaries')
               .select('content, covers_up_to, created_at')
               .order('covers_up_to', desc=True)
               .limit(limit)
               .execute())
        return list(reversed(res.data or []))
    except Exception as e:
        print(f"CRITICAL: Could not fetch summaries. Error: {e}")
        return []

def get_oldest_live_message_id() -> int:
    """Return the id of the oldest message currently in the live context window."""
    try:
        res = (supabase.table('obsidia')
               .select('id')
               .order('created_at', desc=True)
               .limit(12)
               .execute())
        data = res.data or []
        if not data:
            return 0
        return min(row['id'] for row in data)
    except Exception as e:
        print(f"CRITICAL: Could not fetch oldest live message id. Error: {e}")
        return 0

# ─────────────────────────────────────────────────────────────────────────────
# PHOTO STORAGE
# ─────────────────────────────────────────────────────────────────────────────

def upload_photo_to_storage(image_bytes: bytes) -> str:
    bucket_name = 'obsidia-world'
    file_name = f"{uuid.uuid4()}.png"
    supabase.storage.from_(bucket_name).upload(
        path=file_name, file=image_bytes, file_options={"content-type": "image/png"}
    )
    return f"{url}/storage/v1/object/public/{bucket_name}/{file_name}"