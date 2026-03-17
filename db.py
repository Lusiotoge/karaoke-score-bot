import sqlite3

DB_NAME = "data.db"


def get_conn():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        song TEXT,
        score REAL,
        mode TEXT,
        input_date TEXT
    )
    """)

    conn.commit()
    conn.close()


def add_score(user, song, score, mode, date):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO scores
        (user, song, score, mode, input_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user, song, score, mode, date),
    )

    conn.commit()
    conn.close()


def get_scores(user):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, song, score, mode, input_date
        FROM scores
        WHERE user=?
        """,
        (user,),
    )

    rows = cur.fetchall()

    conn.close()
    return rows


def delete_score(score_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM scores WHERE id=?",
        (score_id,),
    )

    conn.commit()
    conn.close()