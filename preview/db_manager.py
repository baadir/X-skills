"""
TwitterYoldas — DB Manager
PostgreSQL (Docker) veya SQLite fallback ile çalışır.

Env değişkenleri:
  YOLDAS_DB=postgres    → PostgreSQL kullan (varsayılan: sqlite)
  YOLDAS_DB_DSN=...     → PostgreSQL bağlantı string'i
"""

import os, json, re, sqlite3, uuid
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone

# ── Konfigürasyon ────────────────────────────────────────────
_HERE     = Path(__file__).resolve().parent
DB_MODE   = os.getenv("YOLDAS_DB", "postgres").lower()
SQLITE_DB = _HERE / "data" / "drafts.db"
PG_DSN    = os.getenv(
    "YOLDAS_DB_DSN",
    "postgresql://yoldas:yoldas_secret@localhost:5434/twitter_yoldas"
)

# ── Slug yardımcısı ──────────────────────────────────────────
def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:80].strip("-")

def make_draft_key(title: str, generated_at: str) -> str:
    date_part = (generated_at or "")[:10]   # "2026-03-18"
    return f"{_slugify(title)}__{date_part}"

# ── URL → tweet_id ayrıştırıcı ───────────────────────────────
def extract_tweet_id(url_or_id: str) -> str | None:
    """
    x.com/user/status/12345   veya   twitter.com/user/status/12345
    ya da doğrudan ID string → ID string döndürür.
    """
    url_or_id = url_or_id.strip()
    m = re.search(r"/status/(\d{10,20})", url_or_id)
    if m:
        return m.group(1)
    if re.fullmatch(r"\d{10,20}", url_or_id):
        return url_or_id
    return None

# ════════════════════════════════════════════════════════════
# PostgreSQL context
# ════════════════════════════════════════════════════════════
def _pg_connect():
    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(PG_DSN)
    conn.autocommit = False
    return conn

@contextmanager
def _pg_cursor():
    import psycopg2.extras
    conn = _pg_connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# ════════════════════════════════════════════════════════════
# SQLite context + init
# ════════════════════════════════════════════════════════════
_SQLITE_INIT = """
CREATE TABLE IF NOT EXISTS thread_drafts (
    id              TEXT PRIMARY KEY,
    draft_key       TEXT NOT NULL UNIQUE,
    thread_title    TEXT NOT NULL,
    generated_at    TEXT NOT NULL,
    author_name     TEXT,
    author_handle   TEXT,
    tweets_json     TEXT NOT NULL,
    analysis_json   TEXT,
    status          TEXT NOT NULL DEFAULT 'öneri',
    posted_at       TEXT,
    tweet_url       TEXT,
    first_tweet_id  TEXT,
    notes           TEXT,
    created_at      TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at      TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS performance_snapshots (
    id              TEXT PRIMARY KEY,
    draft_id        TEXT NOT NULL,
    first_tweet_id  TEXT NOT NULL,
    day_number      INTEGER NOT NULL,
    likes           INTEGER DEFAULT 0,
    retweets        INTEGER DEFAULT 0,
    replies         INTEGER DEFAULT 0,
    quotes          INTEGER DEFAULT 0,
    bookmarks       INTEGER DEFAULT 0,
    impressions     INTEGER DEFAULT 0,
    engagement_rate REAL,
    source          TEXT DEFAULT 'twikit',
    fetched_at      TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (draft_id, day_number)
);
"""

def _sqlite_init():
    SQLITE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_DB)
    conn.executescript(_SQLITE_INIT)
    conn.close()

@contextmanager
def _sqlite_cursor():
    _sqlite_init()
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# ── Aktif context seçici ─────────────────────────────────────
@contextmanager
def get_cursor():
    if DB_MODE == "postgres":
        try:
            with _pg_cursor() as cur:
                yield cur, "postgres"
            return
        except Exception as e:
            print(f"[DB] PostgreSQL bağlantısı başarısız ({e}), SQLite'a geçiliyor...")
    with _sqlite_cursor() as cur:
        yield cur, "sqlite"

# ════════════════════════════════════════════════════════════
# PUBLIC API
# ════════════════════════════════════════════════════════════

def save_draft(thread_data: dict) -> dict:
    """
    current_thread.json içeriğini 'öneri' olarak kaydeder.
    Aynı draft_key varsa {"conflict": True, "draft_id": ...} döndürür.
    """
    title        = thread_data.get("thread_title", "Başlıksız")
    generated_at = thread_data.get("generated_at", datetime.now(timezone.utc).isoformat())
    draft_key    = make_draft_key(title, generated_at)
    draft_id     = str(uuid.uuid4())

    tweets_json   = json.dumps(thread_data.get("tweets", []),   ensure_ascii=False)
    analysis_json = json.dumps(thread_data.get("analysis", {}), ensure_ascii=False)
    author        = thread_data.get("author", {})

    with get_cursor() as (cur, mode):
        if mode == "postgres":
            # Conflict kontrolü
            cur.execute("SELECT id FROM thread_drafts WHERE draft_key = %s", (draft_key,))
            row = cur.fetchone()
            if row:
                return {"conflict": True, "draft_id": str(row["id"]), "draft_key": draft_key}

            cur.execute("""
                INSERT INTO thread_drafts
                    (id, draft_key, thread_title, generated_at,
                     author_name, author_handle, tweets_json, analysis_json)
                VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
            """, (
                draft_id, draft_key, title, generated_at,
                author.get("name"), author.get("handle"),
                tweets_json, analysis_json
            ))
        else:
            cur.execute("SELECT id FROM thread_drafts WHERE draft_key = ?", (draft_key,))
            row = cur.fetchone()
            if row:
                return {"conflict": True, "draft_id": row["id"], "draft_key": draft_key}

            cur.execute("""
                INSERT INTO thread_drafts
                    (id, draft_key, thread_title, generated_at,
                     author_name, author_handle, tweets_json, analysis_json)
                VALUES (?,?,?,?,?,?,?,?)
            """, (
                draft_id, draft_key, title, generated_at,
                author.get("name"), author.get("handle"),
                tweets_json, analysis_json
            ))

    return {"ok": True, "draft_id": draft_id, "draft_key": draft_key}


def list_drafts(status: str | None = None) -> list[dict]:
    """Tüm taslakları (isteğe bağlı status filtresiyle) döndürür."""
    with get_cursor() as (cur, mode):
        if mode == "postgres":
            if status:
                cur.execute(
                    "SELECT * FROM v_drafts_with_performance WHERE status = %s",
                    (status,)
                )
            else:
                cur.execute("SELECT * FROM v_drafts_with_performance")
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        else:
            if status:
                cur.execute(
                    "SELECT * FROM thread_drafts WHERE status = ? ORDER BY created_at DESC",
                    (status,)
                )
            else:
                cur.execute("SELECT * FROM thread_drafts ORDER BY created_at DESC")
            rows = cur.fetchall()
            result = []
            for r in rows:
                d = dict(r)
                # SQLite'ta JSON string → parse etme (listing'de gerekmez)
                result.append(d)
            return result


def get_draft(draft_id: str) -> dict | None:
    """Tek draft + tüm performance snapshot'larını döndürür."""
    with get_cursor() as (cur, mode):
        if mode == "postgres":
            cur.execute(
                "SELECT * FROM thread_drafts WHERE id = %s",
                (draft_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            draft = dict(row)
            # tweets_json ve analysis_json zaten JSONB olarak parse edilmiş gelir
            cur.execute(
                "SELECT * FROM performance_snapshots WHERE draft_id = %s ORDER BY day_number",
                (draft_id,)
            )
            snapshots = [dict(r) for r in cur.fetchall()]
        else:
            cur.execute(
                "SELECT * FROM thread_drafts WHERE id = ?",
                (draft_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            draft = dict(row)
            draft["tweets_json"]   = json.loads(draft.get("tweets_json") or "[]")
            draft["analysis_json"] = json.loads(draft.get("analysis_json") or "{}")
            cur.execute(
                "SELECT * FROM performance_snapshots WHERE draft_id = ? ORDER BY day_number",
                (draft_id,)
            )
            snapshots = [dict(r) for r in cur.fetchall()]

        draft["snapshots"] = snapshots
        return draft


def get_draft_by_key(draft_key: str) -> dict | None:
    """draft_key ile draft arar."""
    with get_cursor() as (cur, mode):
        if mode == "postgres":
            cur.execute("SELECT id, status, first_tweet_id, tweet_url FROM thread_drafts WHERE draft_key = %s", (draft_key,))
            row = cur.fetchone()
        else:
            cur.execute("SELECT id, status, first_tweet_id, tweet_url FROM thread_drafts WHERE draft_key = ?", (draft_key,))
            row = cur.fetchone()
        return dict(row) if row else None


def mark_posted(draft_id: str, tweet_url: str) -> dict:
    """
    Tweet URL'ini kaydeder, status='atılmış' yapar, tweet_id'yi URL'den çeker.
    """
    tweet_id = extract_tweet_id(tweet_url)
    if not tweet_id:
        return {"error": "Geçersiz tweet URL'i. Örnek: https://x.com/kullanici/status/1234567890"}

    posted_at = datetime.now(timezone.utc).isoformat()

    with get_cursor() as (cur, mode):
        if mode == "postgres":
            cur.execute("""
                UPDATE thread_drafts
                SET status='atılmış', posted_at=%s, tweet_url=%s, first_tweet_id=%s
                WHERE id=%s AND status='öneri'
                RETURNING id
            """, (posted_at, tweet_url, tweet_id, draft_id))
            row = cur.fetchone()
        else:
            cur.execute("""
                UPDATE thread_drafts
                SET status='atılmış', posted_at=?, tweet_url=?, first_tweet_id=?,
                    updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now')
                WHERE id=? AND status='öneri'
            """, (posted_at, tweet_url, tweet_id, draft_id))
            row = {"id": draft_id} if cur.rowcount > 0 else None

    if not row:
        return {"error": "Draft bulunamadı veya zaten 'atılmış' durumunda."}

    return {
        "ok": True,
        "draft_id": draft_id,
        "tweet_id": tweet_id,
        "tweet_url": tweet_url,
        "posted_at": posted_at
    }


def save_snapshot(draft_id: str, first_tweet_id: str, day_number: int, metrics: dict, source: str = "twikit") -> dict:
    """Performance snapshot kaydeder (upsert — aynı gün varsa günceller)."""
    snap_id = str(uuid.uuid4())
    eng     = _calc_engagement(metrics)
    now     = datetime.now(timezone.utc).isoformat()

    with get_cursor() as (cur, mode):
        if mode == "postgres":
            cur.execute("""
                INSERT INTO performance_snapshots
                    (id, draft_id, first_tweet_id, day_number,
                     likes, retweets, replies, quotes, bookmarks, impressions,
                     engagement_rate, source, fetched_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (draft_id, day_number)
                DO UPDATE SET
                    likes=EXCLUDED.likes, retweets=EXCLUDED.retweets,
                    replies=EXCLUDED.replies, quotes=EXCLUDED.quotes,
                    bookmarks=EXCLUDED.bookmarks, impressions=EXCLUDED.impressions,
                    engagement_rate=EXCLUDED.engagement_rate,
                    source=EXCLUDED.source, fetched_at=EXCLUDED.fetched_at
            """, (
                snap_id, draft_id, first_tweet_id, day_number,
                metrics.get("likes",0), metrics.get("retweets",0),
                metrics.get("replies",0), metrics.get("quotes",0),
                metrics.get("bookmarks",0), metrics.get("impressions",0),
                eng, source, now
            ))
        else:
            cur.execute("""
                INSERT INTO performance_snapshots
                    (id, draft_id, first_tweet_id, day_number,
                     likes, retweets, replies, quotes, bookmarks, impressions,
                     engagement_rate, source, fetched_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT (draft_id, day_number)
                DO UPDATE SET
                    likes=excluded.likes, retweets=excluded.retweets,
                    replies=excluded.replies, quotes=excluded.quotes,
                    bookmarks=excluded.bookmarks, impressions=excluded.impressions,
                    engagement_rate=excluded.engagement_rate,
                    source=excluded.source, fetched_at=excluded.fetched_at
            """, (
                snap_id, draft_id, first_tweet_id, day_number,
                metrics.get("likes",0), metrics.get("retweets",0),
                metrics.get("replies",0), metrics.get("quotes",0),
                metrics.get("bookmarks",0), metrics.get("impressions",0),
                eng, source, now
            ))

    return {"ok": True, "day_number": day_number, "engagement_rate": eng}


def get_snapshots(draft_id: str) -> list[dict]:
    """Draft'ın tüm snapshot'larını döndürür."""
    with get_cursor() as (cur, mode):
        if mode == "postgres":
            cur.execute(
                "SELECT * FROM performance_snapshots WHERE draft_id = %s ORDER BY day_number",
                (draft_id,)
            )
        else:
            cur.execute(
                "SELECT * FROM performance_snapshots WHERE draft_id = ? ORDER BY day_number",
                (draft_id,)
            )
        return [dict(r) for r in cur.fetchall()]


def _calc_engagement(m: dict) -> float:
    imp = max(m.get("impressions", 0), 1)
    interactions = (
        m.get("likes", 0) + m.get("retweets", 0) +
        m.get("replies", 0) + m.get("quotes", 0) +
        m.get("bookmarks", 0)
    )
    return round(interactions / imp * 100, 4)
