"""SQLite access layer.

All replicas share one database file on a PersistentVolume. WAL mode lets
readers and a writer work at the same time, and busy_timeout makes writers
wait for the lock instead of failing immediately.
"""
import json
import os
import sqlite3
from importlib import resources

from flask import current_app, g


def connect(path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DB_PATH"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_schema(conn):
    schema = resources.files("kubequiz").joinpath("schema.sql").read_text()
    conn.executescript(schema)
    conn.commit()


def init_app(app):
    app.teardown_appcontext(close_db)


# ---- queries -------------------------------------------------------------

def list_quizzes(db):
    return db.execute(
        """SELECT q.id, q.title, q.description, q.time_limit_seconds,
                  COUNT(qs.id) AS question_count
           FROM quizzes q LEFT JOIN questions qs ON qs.quiz_id = q.id
           GROUP BY q.id ORDER BY q.id"""
    ).fetchall()


def get_quiz(db, quiz_id):
    return db.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()


def get_questions(db, quiz_id):
    rows = db.execute(
        "SELECT * FROM questions WHERE quiz_id = ? ORDER BY id", (quiz_id,)
    ).fetchall()
    return [
        {
            "id": r["id"],
            "text": r["text"],
            "options": json.loads(r["options"]),
            "correct_index": r["correct_index"],
        }
        for r in rows
    ]


def create_quiz(db, title, description, time_limit_seconds):
    cur = db.execute(
        "INSERT INTO quizzes (title, description, time_limit_seconds) VALUES (?, ?, ?)",
        (title, description, time_limit_seconds),
    )
    db.commit()
    return cur.lastrowid


def update_quiz(db, quiz_id, title, description, time_limit_seconds):
    db.execute(
        "UPDATE quizzes SET title = ?, description = ?, time_limit_seconds = ? WHERE id = ?",
        (title, description, time_limit_seconds, quiz_id),
    )
    db.commit()


def delete_quiz(db, quiz_id):
    db.execute("DELETE FROM quizzes WHERE id = ?", (quiz_id,))
    db.commit()


def add_question(db, quiz_id, text, options, correct_index):
    cur = db.execute(
        "INSERT INTO questions (quiz_id, text, options, correct_index) VALUES (?, ?, ?, ?)",
        (quiz_id, text, json.dumps(options), correct_index),
    )
    db.commit()
    return cur.lastrowid


def delete_question(db, question_id):
    db.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    db.commit()


def record_attempt(db, quiz_id, username, score, total, duration_seconds, answers, served_by):
    cur = db.execute(
        """INSERT INTO attempts
               (quiz_id, username, score, total, duration_seconds, answers, served_by)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (quiz_id, username, score, total, duration_seconds,
         json.dumps({str(k): v for k, v in answers.items()}), served_by),
    )
    db.commit()
    return cur.lastrowid


def get_attempt(db, attempt_id):
    return db.execute(
        """SELECT a.*, q.title AS quiz_title FROM attempts a
           JOIN quizzes q ON q.id = a.quiz_id WHERE a.id = ?""",
        (attempt_id,),
    ).fetchone()


def leaderboard(db, quiz_id, limit=10):
    return db.execute(
        """SELECT username, score, total, duration_seconds, submitted_at
           FROM attempts WHERE quiz_id = ?
           ORDER BY score DESC, duration_seconds ASC, id ASC LIMIT ?""",
        (quiz_id, limit),
    ).fetchall()


def stats(db):
    row = db.execute(
        """SELECT (SELECT COUNT(*) FROM quizzes) AS quizzes,
                  (SELECT COUNT(*) FROM questions) AS questions,
                  (SELECT COUNT(*) FROM attempts) AS attempts"""
    ).fetchone()
    return dict(row)
