import sqlite3
import datetime
import secrets
import string
from config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Settings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # Keys stock table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS keys_stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_value TEXT UNIQUE NOT NULL,
        password TEXT DEFAULT '',
        tier TEXT DEFAULT 'FREE',
        is_used INTEGER DEFAULT 0,
        used_by_user_id INTEGER NULL,
        used_by_username TEXT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        claimed_at TEXT NULL
    )
    """)

    # User claims table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT NOT NULL,
        key_id INTEGER,
        key_value TEXT NOT NULL,
        password TEXT DEFAULT '',
        tier TEXT DEFAULT 'FREE',
        claimed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        expires_at TEXT NULL
    )
    """)

    # Audit logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        action TEXT,
        details TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Default settings matching the server setup
    defaults = {
        "bot_name": "GLOBAL BYPASS",
        "status": "Enabled",
        "total_limit": "INFINITE",
        "free_limit_per_person": "1",
        "max_days": "1",
        "free_channel": "1560660990897422376",
        "free_logs": "1560661297899774042",
        "paid_channel": "1560623415835234395",
        "paid_logs": "1560623451507531888",
        "admin_panel_channel": "1560623103699062846",
        "admin_panel_logs": "1560623103699062846",
        "voice_channel": "1560614980158750797",
        "allowed_free_roles": "",
        "allowed_paid_roles": "1560655816477114509",
        "paid_owners": "768020734231969793, 1392630988622008352, 375765136658661377",
        "admin_panel_owners": "768020734231969793, 1392630988622008352, 1190844956395446397",
        "paid_color": "Not configured",
        "free_color": "00FFA2",
        "admin_panel_color": "FC2403",
        "language": "English",
        "support_url": "https://discord.gg/",
        "free_panel_message_id": "0",
        "admin_panel_message_id": "0"
    }

    for k, v in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    # Ensure Primary Owner is in admin_panel_owners and paid_owners even on existing databases
    cursor.execute("SELECT value FROM settings WHERE key = 'admin_panel_owners'")
    row = cursor.fetchone()
    if row and "768020734231969793" not in row["value"]:
        updated_val = "768020734231969793, " + row["value"] if row["value"] else "768020734231969793"
        cursor.execute("UPDATE settings SET value = ? WHERE key = 'admin_panel_owners'", (updated_val,))

    cursor.execute("SELECT value FROM settings WHERE key = 'paid_owners'")
    row = cursor.fetchone()
    if row and "768020734231969793" not in row["value"]:
        updated_val = "768020734231969793, " + row["value"] if row["value"] else "768020734231969793"
        cursor.execute("UPDATE settings SET value = ? WHERE key = 'paid_owners'", (updated_val,))

    conn.commit()
    conn.close()

def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_all_settings() -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}

def add_keys(keys_data: list, tier: str = "FREE") -> tuple[int, int]:
    """
    keys_data: list of dicts [{'key': 'xyz', 'password': 'abc'}]
    returns (added_count, duplicate_count)
    """
    conn = get_connection()
    cursor = conn.cursor()
    added = 0
    duplicates = 0

    for item in keys_data:
        key_val = item.get("key", "").strip()
        pwd = item.get("password", "").strip()
        if not key_val:
            continue
        try:
            cursor.execute("""
            INSERT INTO keys_stock (key_value, password, tier)
            VALUES (?, ?, ?)
            """, (key_val, pwd, tier.upper()))
            added += 1
        except sqlite3.IntegrityError:
            duplicates += 1

    conn.commit()
    conn.close()
    return added, duplicates

def generate_random_keys(count: int, prefix: str = "GB-", tier: str = "FREE", with_password: bool = True) -> int:
    """Generate cryptographically secure random keys and passwords into stock."""
    keys_data = []
    chars = string.ascii_uppercase + string.digits
    pwd_chars = string.ascii_letters + string.digits

    for _ in range(count):
        token_part = ''.join(secrets.choice(chars) for _ in range(12))
        formatted_key = f"{prefix}{token_part[:4]}-{token_part[4:8]}-{token_part[8:]}"
        password = ''.join(secrets.choice(pwd_chars) for _ in range(10)) if with_password else ""
        keys_data.append({"key": formatted_key, "password": password})

    added, _ = add_keys(keys_data, tier)
    return added

def get_available_count(tier: str = "FREE") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM keys_stock WHERE tier = ? AND is_used = 0", (tier.upper(),))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_used_count(tier: str = "FREE") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM keys_stock WHERE tier = ? AND is_used = 1", (tier.upper(),))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_total_count(tier: str = "FREE") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM keys_stock WHERE tier = ?", (tier.upper(),))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_user_claims_count(user_id: int, tier: str = "FREE") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM user_claims WHERE user_id = ? AND tier = ?", (user_id, tier.upper()))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_user_active_key(user_id: int, tier: str = "FREE"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT key_value, password, claimed_at, expires_at 
    FROM user_claims 
    WHERE user_id = ? AND tier = ? 
    ORDER BY id DESC LIMIT 1
    """, (user_id, tier.upper()))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def claim_free_key(user_id: int, username: str) -> tuple[bool, str, str, str]:
    """
    Claims a free key for a user.
    Returns: (success, key_or_error, password, expires_at_str)
    """
    settings = get_all_settings()
    if settings.get("status", "Enabled").lower() != "enabled":
        return False, "BOT_DISABLED", "", ""

    limit_per_person = int(settings.get("free_limit_per_person", "1"))
    current_claims = get_user_claims_count(user_id, "FREE")

    if current_claims >= limit_per_person:
        return False, "LIMIT_REACHED", "", ""

    conn = get_connection()
    cursor = conn.cursor()

    # Find next available key
    cursor.execute("""
    SELECT id, key_value, password FROM keys_stock 
    WHERE tier = 'FREE' AND is_used = 0 
    ORDER BY id ASC LIMIT 1
    """)
    key_row = cursor.fetchone()

    if not key_row:
        conn.close()
        return False, "OUT_OF_STOCK", "", ""

    key_id = key_row["id"]
    key_val = key_row["key_value"]
    key_pwd = key_row["password"]

    now = datetime.datetime.now(datetime.timezone.utc)
    max_days = int(settings.get("max_days", "1"))
    expires_at = now + datetime.timedelta(days=max_days)
    now_str = now.isoformat()
    exp_str = expires_at.isoformat()

    # Mark key as used
    cursor.execute("""
    UPDATE keys_stock 
    SET is_used = 1, used_by_user_id = ?, used_by_username = ?, claimed_at = ?
    WHERE id = ?
    """, (user_id, username, now_str, key_id))

    # Insert into user claims
    cursor.execute("""
    INSERT INTO user_claims (user_id, username, key_id, key_value, password, tier, claimed_at, expires_at)
    VALUES (?, ?, ?, ?, ?, 'FREE', ?, ?)
    """, (user_id, username, key_id, key_val, key_pwd, now_str, exp_str))

    # Audit log
    cursor.execute("""
    INSERT INTO audit_logs (user_id, username, action, details)
    VALUES (?, ?, 'CLAIM_FREE_KEY', ?)
    """, (user_id, username, f"Claimed key: {key_val}"))

    conn.commit()
    conn.close()
    return True, key_val, key_pwd, exp_str

def reset_all_free_limits():
    """Clears all FREE user claims and restores the keys or allows users to claim again."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_claims WHERE tier = 'FREE'")
    conn.commit()
    conn.close()

def reset_single_user_limit(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_claims WHERE user_id = ? AND tier = 'FREE'", (user_id,))
    conn.commit()
    conn.close()

def delete_user_records(user_id: int) -> bool:
    """Deletes all claims for a specific user ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_claims WHERE user_id = ?", (user_id,))
    deleted = cursor.rowcount > 0
    # Also update any keys_stock used by this user to mark as deleted/released if desired
    cursor.execute("UPDATE keys_stock SET is_used = 0, used_by_user_id = NULL, used_by_username = NULL, claimed_at = NULL WHERE used_by_user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return deleted

def get_claims_list(tier: str = "FREE", limit: int = 50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT user_id, username, key_value, password, claimed_at 
    FROM user_claims 
    WHERE tier = ? 
    ORDER BY id DESC LIMIT ?
    """, (tier.upper(), limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_stock_keys(tier: str = "FREE", is_used: int = 0, limit: int = 100):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT key_value, password, is_used, used_by_username, claimed_at 
    FROM keys_stock 
    WHERE tier = ? AND is_used = ?
    ORDER BY id DESC LIMIT ?
    """, (tier.upper(), is_used, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def log_audit(user_id: int, username: str, action: str, details: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO audit_logs (user_id, username, action, details)
    VALUES (?, ?, ?, ?)
    """, (user_id, username, action, details))
    conn.commit()
    conn.close()
