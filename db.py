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


def get_best_scores(user):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT song, MAX(score)
    FROM scores
    WHERE user=?
    GROUP BY song
    """, (user,))

    rows = cur.fetchall()

    conn.close()

    return rows


def get_song_stats(user, song):

    conn = get_conn()
    cur = conn.cursor()

    # 最新

    cur.execute("""
    SELECT score, mode, input_date
    FROM scores
    WHERE user=? AND song=?
    ORDER BY id DESC
    LIMIT 1
    """, (user, song))

    last = cur.fetchone()

    # 最高

    cur.execute("""
    SELECT score, mode, input_date
    FROM scores
    WHERE user=? AND song=?
    ORDER BY score DESC
    LIMIT 1
    """, (user, song))

    best = cur.fetchone()

    conn.close()

    return last, best


def get_last_full(user, song):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    SELECT score, mode
    FROM scores
    WHERE user=? AND song=?
    ORDER BY id DESC
    LIMIT 1
    """, (user, song))

    row = cur.fetchone()

    conn.close()

    return row


def delete_by_id(record_id):

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM scores WHERE id=?",
        (record_id,)
    )

    conn.commit()
    conn.close()


def delete_by_user(user):

    conn = sqlite3.connect("data.db")
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM scores WHERE user=?",
        (user,)
    )

    conn.commit()
    conn.close()