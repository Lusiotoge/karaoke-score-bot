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


def update_score(user_id, song, score, mode):

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT score FROM scores
        WHERE user_id=? AND song=? AND mode=?
        """,
        (user_id, song, mode)
    )

    row = cur.fetchone()

    # 初回登録
    if row is None:

        cur.execute(
            """
            INSERT INTO scores (user_id, song, score, mode)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, song, score, mode)
        )

        conn.commit()
        conn.close()

        return "new"

    old_score = row[0]

    # 更新
    if score > old_score:

        cur.execute(
            """
            UPDATE scores
            SET score=?
            WHERE user_id=? AND song=? AND mode=?
            """,
            (score, user_id, song, mode)
        )

        conn.commit()
        conn.close()

        return "update"

    conn.close()

    return "nochange"


def get_all_scores():
    conn = sqlite3.connect("score.db")
    c = conn.cursor()

    c.execute("""
    SELECT user, MAX(score)
    FROM scores
    GROUP BY user
    ORDER BY MAX(score) DESC
    """)

    rows = c.fetchall()
    conn.close()

    return rows


def add_exp(user, exp):
    conn = sqlite3.connect("score.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS user_level (
        user TEXT PRIMARY KEY,
        exp INTEGER,
        level INTEGER
    )
    """)

    c.execute("SELECT exp, level FROM user_level WHERE user=?", (user,))
    row = c.fetchone()

    if row:
        current_exp, level = row
    else:
        current_exp, level = 0, 1

    current_exp += int(exp)

    # レベル計算（簡易）
    new_level = current_exp // 100 + 1

    c.execute("""
    INSERT OR REPLACE INTO user_level (user, exp, level)
    VALUES (?, ?, ?)
    """, (user, current_exp, new_level))

    conn.commit()
    conn.close()

    return current_exp, new_level


def get_level(user):
    conn = sqlite3.connect("score.db")
    c = conn.cursor()

    c.execute("SELECT exp, level FROM user_level WHERE user=?", (user,))
    row = c.fetchone()

    conn.close()

    if row:
        return row
    return 0, 1


def set_monthly_song(song):
    conn = sqlite3.connect("score.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS monthly (
        song TEXT,
        month TEXT
    )
    """)

    month = datetime.now().strftime("%Y-%m")

    c.execute("DELETE FROM monthly WHERE month=?", (month,))
    c.execute("INSERT INTO monthly VALUES (?, ?)", (song, month))

    conn.commit()
    conn.close()


def get_monthly_song():
    conn = sqlite3.connect("score.db")
    c = conn.cursor()

    month = datetime.now().strftime("%Y-%m")

    c.execute("SELECT song FROM monthly WHERE month=?", (month,))
    row = c.fetchone()

    conn.close()

    return row[0] if row else None