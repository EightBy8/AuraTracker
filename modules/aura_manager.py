# modules/aura_manager.py
import json
import os
from typing import Dict, Any

from modules.utils import log

# Ensure data directory exists
DATA_DIR: str = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# Files (inside data/)
AURA_FILE: str = os.path.join(DATA_DIR, "aura.json")
HISTORY_FILE: str = os.path.join(DATA_DIR, "auraHistory.json")
AURACOUNTER_FILE: str = os.path.join(DATA_DIR, "auraCount.json")
CONFIG_FILE: str = os.path.join(DATA_DIR, "config.json")

# In-memory state
aura_data: Dict[str, int] = {}
user_reactions: Dict[int, list[str]] = {}
user_aura_count: Dict[str, Dict[str, int]] = {}

# Global Variables
OWNER_IDS: list[int] = []
CHANNEL_ID: int | None = None

# ---- Owner/Admin Manager

def add_owner(owner_id : str) -> None:
    global OWNER_IDS
    if owner_id not in OWNER_IDS:
        OWNER_IDS += (owner_id,)

def remove_owner(owner_id: str) -> None:
    global OWNER_IDS
    try:
        OWNER_IDS.remove(owner_id)
    except ValueError:
        pass

# ---- JSON helpers ----
def load_json(file: str) -> Dict[str, Any]:
    """Load JSON from file and return a dict (empty if missing or empty)."""
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            content: str = f.read().strip()
            if content:
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    log(f"{file} exists but contains invalid JSON. Returning empty dict.", "ERROR")
                    return {}
    return {}


def save_json(file: str, data: Dict[str, Any]) -> None:
    """Write JSON to disk with indentation."""
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    log(f"{file} saved", "SUCCESS")



# ---- Aura data management ----
def load_aura() -> None:
    """Load the global aura leaderboard into memory."""
    global aura_data
    loaded: Dict[str, Any] = load_json(AURA_FILE)
    aura_data.clear()
    aura_data.update({k: int(v) for k, v in loaded.items()})  # coerce to int
    log("Aura data loaded", "SUCCESS" if aura_data else "WARNING")


def load_history() -> Dict[str, Any]:
    """Return saved history (may be empty)."""
    return load_json(HISTORY_FILE)


def ensure_today(history: Dict[str, Any]) -> None:
    """Ensure today's key exists in history (YYYY-MM-DD)."""
    from datetime import date

    today: str = date.today().strftime("%Y-%m-%d")
    if today not in history:
        history[today] = {}
        log("Added today's date to history", "WARNING")


# ---- Aura Command Helper ----

def set_aura(user_id: int, amount: int) -> None:
    """Set a user's aura to an explicit value."""
    aura_data[str(user_id)] = int(amount)
    save_json(AURA_FILE, aura_data)
    log(f"Set aura for {user_id}: {amount}", "INFO")


def update_aura(user_id: int, change: int) -> None:
    """
    Apply a relative change to a user's aura (positive or negative),
    save to disk and log.
    """
    uid: str = str(user_id)
    aura_data[uid] = aura_data.get(uid, 0) + int(change)
    save_json(AURA_FILE, aura_data)
    log(f"Updated aura for {user_id}: {aura_data[uid]}", "INFO")


# ---- Aura-count-per-sender (positive / negative counts) ----
def load_aura_count() -> None:
    """Load counters for how much aura each sender has given (POS/NEG)."""
    global user_aura_count
    loaded: Dict[str, Any] = load_json(AURACOUNTER_FILE)
    user_aura_count = {
        k: {"POS": int(v.get("POS", 0)), "NEG": int(v.get("NEG", 0))} for k, v in loaded.items()
    }
    log("'auraCount' data loaded", "SUCCESS" if user_aura_count else "WARNING")


def save_aura_count() -> None:
    """Persist the sender counters to disk."""
    save_json(AURACOUNTER_FILE, user_aura_count)
    log("Saved aura counts to file", "SUCCESS")


def adjust_sender_count(sender_id: int, field: str, delta: int) -> None:
    """
    Increment/decrement a sender's POS/NEG count, clamped to >= 0.
    field must be "POS" or "NEG".
    """
    sid: str = str(sender_id)
    if field not in ("POS", "NEG"):
        raise ValueError("field must be 'POS' or 'NEG'")
    if sid not in user_aura_count:
        user_aura_count[sid] = {"POS": 0, "NEG": 0}
    user_aura_count[sid][field] = max(0, user_aura_count[sid][field] + int(delta))
    save_aura_count()
    log(f"Adjusted {field} for {sid} by {delta} -> {user_aura_count[sid][field]}", "INFO")


def get_negative_leaderboard() -> list[tuple[str, int]]:
    """
    Returns list of (user_id_str, neg_count) sorted descending by NEG.
    """
    return sorted(
        ((uid, data["NEG"]) for uid, data in user_aura_count.items()),
        key=lambda x: x[1],
        reverse=True,
    )
