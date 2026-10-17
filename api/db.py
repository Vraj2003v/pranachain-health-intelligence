"""SQLite storage: users, login sessions, uploaded workbooks, analysis summaries and an audit log.

The database file is data/pranapulse.db (override with PRANAPULSE_DB). It is not committed to git.
"""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get("PRANAPULSE_DB", Path(__file__).resolve().parent.parent / "data" / "pranapulse.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'clinician',
  pw_hash TEXT NOT NULL, salt TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime('now')), consent_at TEXT);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  filename TEXT NOT NULL, sha256 TEXT NOT NULL, size INTEGER NOT NULL, blob BLOB NOT NULL, is_demo INTEGER NOT NULL DEFAULT 0,
  uploaded_at TEXT NOT NULL DEFAULT (datetime('now')), UNIQUE(user_id, sha256));
CREATE TABLE IF NOT EXISTS results (
  document_id INTEGER PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE, patient_id TEXT, age REAL, sex TEXT,
  status TEXT, found TEXT, flag TEXT, scenario TEXT, kinds TEXT, held INTEGER, insights INTEGER);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY, at TEXT NOT NULL DEFAULT (datetime('now')), user_id INTEGER, email TEXT, action TEXT NOT NULL, detail TEXT);
CREATE INDEX IF NOT EXISTS idx_docs_user ON documents(user_id);
"""


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


@contextmanager
def db():
    con = connect()
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init():
    with db() as con:
        con.executescript(SCHEMA)
