# db.py

import sqlite3

DB_PATH = "insignia.db"


def get_connection():
    return sqlite3.connect(DB_PATH)

def get_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, username, access_token, refresh_token, expires_at FROM users")
    rows = c.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "username": r[1],
            "access_token": r[2],
            "refresh_token": r[3],
            "expires_at": r[4],
        }
        for r in rows
    ]

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # user table (from oauth_server)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY,
            username      TEXT,
            access_token  TEXT,
            refresh_token TEXT,
            expires_at    INTEGER,
            email         TEXT,
            ip            TEXT
        )
    """
    )
    # guilds you manage in the CLI
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS guilds (
            guild_id         INTEGER PRIMARY KEY,
            verified_role_id INTEGER
        )
    """
    )
    conn.commit()
    conn.close()


def upsert_user(user_id, username, access_token, refresh_token, expires_at, email, ip):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO users
           (id, username, access_token, refresh_token, expires_at, email, ip)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          username      = excluded.username,
          access_token  = excluded.access_token,
          refresh_token = excluded.refresh_token,
          expires_at    = excluded.expires_at,
          email         = excluded.email,
          ip            = excluded.ip
    """,
        (user_id, username, access_token, refresh_token, expires_at, email, ip),
    )
    conn.commit()
    conn.close()


def add_guild(guild_id, verified_role_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO guilds (guild_id, verified_role_id)
        VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET
          verified_role_id = excluded.verified_role_id
    """,
        (guild_id, verified_role_id),
    )
    conn.commit()
    conn.close()


def get_guilds():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT guild_id, verified_role_id FROM guilds")
    rows = c.fetchall()
    conn.close()
    return [{"guild_id": r[0], "verified_role_id": r[1]} for r in rows]
