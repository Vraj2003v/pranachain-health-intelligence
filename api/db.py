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
CREATE TABLE IF NOT EXISTS lab_reports (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  patient_id TEXT NOT NULL, collected TEXT NOT NULL, filename TEXT NOT NULL, sha256 TEXT NOT NULL, size INTEGER NOT NULL,
  age REAL, sex TEXT, added INTEGER NOT NULL DEFAULT 0, uploaded_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(user_id, sha256));
CREATE TABLE IF NOT EXISTS lab_values (
  id INTEGER PRIMARY KEY, report_id INTEGER NOT NULL REFERENCES lab_reports(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL, patient_id TEXT NOT NULL, collected TEXT NOT NULL, test TEXT NOT NULL,
  value REAL, unit TEXT, ref_low REAL, ref_high REAL, converted_from TEXT,
  UNIQUE(user_id, patient_id, collected, test));
CREATE INDEX IF NOT EXISTS idx_labvalues_patient ON lab_values(user_id, patient_id);
CREATE TABLE IF NOT EXISTS reading_files (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  patient_id TEXT NOT NULL, first_day TEXT, last_day TEXT, filename TEXT NOT NULL, sha256 TEXT NOT NULL, size INTEGER NOT NULL,
  age REAL, sex TEXT, added INTEGER NOT NULL DEFAULT 0, uploaded_at TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(user_id, sha256));
CREATE TABLE IF NOT EXISTS daily_values (
  id INTEGER PRIMARY KEY, file_id INTEGER NOT NULL REFERENCES reading_files(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL, patient_id TEXT NOT NULL, day TEXT NOT NULL, measure TEXT NOT NULL, value REAL NOT NULL,
  UNIQUE(user_id, patient_id, day, measure));
CREATE TABLE IF NOT EXISTS context_files (
  id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  patient_id TEXT NOT NULL, kind TEXT NOT NULL, filename TEXT NOT NULL, sha256 TEXT NOT NULL, size INTEGER NOT NULL,
  doc_date TEXT, age REAL, sex TEXT, note TEXT, ocr INTEGER NOT NULL DEFAULT 0, added INTEGER NOT NULL DEFAULT 0,
  uploaded_at TEXT NOT NULL DEFAULT (datetime('now')), UNIQUE(user_id, sha256));
CREATE TABLE IF NOT EXISTS context_items (
  id INTEGER PRIMARY KEY, file_id INTEGER NOT NULL REFERENCES context_files(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL, patient_id TEXT NOT NULL, kind TEXT NOT NULL, date TEXT NOT NULL, name TEXT NOT NULL,
  detail TEXT, status TEXT, end_date TEXT, value REAL, extra TEXT,
  UNIQUE(user_id, patient_id, kind, date, name));
CREATE INDEX IF NOT EXISTS idx_context_patient ON context_items(user_id, patient_id);
CREATE INDEX IF NOT EXISTS idx_daily_patient ON daily_values(user_id, patient_id);
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
