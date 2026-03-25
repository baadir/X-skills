"""
Ana ingestion pipeline.

Akış:
  1. Load     — session JSON dosyasını oku
  2. Validate — Pydantic ile doğrula
  3. Expand   — Thread bütünlüğünü sağla (eksik kardeş tweet'leri X API'den çek)
  4. Dedup    — tweet_id çakışması kontrolü
  5. Transform — thread_role, viral_level hesapla
  6. Embed    — text → vector(384)
  7. Upsert   — PostgreSQL'e yaz
  8. Session  — miner_sessions kaydı oluştur

Kullanım:
  python ingestion/ingester.py data/collections/session_20250317_001.json
  python ingestion/ingester.py --all   # data/collections/ altındaki tüm session'ları işle
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psycopg2  # type: ignore
from psycopg2.extras import execute_values  # type: ignore
from dotenv import load_dotenv  # type: ignore

# Proje kökünü path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.embedder import Embedder
from ingestion.models import MinerSession, TweetRecord

load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# DB bağlantısı
# ─────────────────────────────────────────────

def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "twitter_yoldas"),
        user=os.getenv("DB_USER", "yoldas"),
        password=os.getenv("DB_PASSWORD", "yoldas_secret"),
    )


# ─────────────────────────────────────────────
# Thread genişletme (X API'den eksik kardeşleri çek)
# ─────────────────────────────────────────────

def fetch_missing_thread_siblings(
    tweet: TweetRecord,
    existing_ids: set[str],
    bearer_token: Optional[str],
) -> List[Dict[str, Any]]:
    """
    thread_tweet_ids içinde DB'de olmayan tweet'leri X API'den çeker.
    bearer_token yoksa boş döner (thread_complete=False kalır).
    """
    if not bearer_token:
        return []

    missing_ids = [tid for tid in tweet.thread_tweet_ids if tid not in existing_ids]
    if not missing_ids:
        return []

    logger.info(f"  Thread genişletme: {len(missing_ids)} eksik tweet çekiliyor...")

    try:
        import httpx  # type: ignore
    except ImportError:
        logger.warning("httpx bulunamadı. Thread genişletme atlandı. pip install httpx")
        return []

    FIELDS = (
        "id,text,author_id,created_at,public_metrics,"
        "non_public_metrics,organic_metrics,attachments,"
        "entities,referenced_tweets,conversation_id,lang"
    )

    raw_tweets: List[Dict[str, Any]] = []

    # X API batch: max 100 ID per request
    for i in range(0, len(missing_ids), 100):
        batch = missing_ids[i:i + 100]
        url = "https://api.twitter.com/2/tweets"
        params = {
            "ids": ",".join(batch),
            "tweet.fields": FIELDS,
            "expansions": "author_id",
            "user.fields": "id,name,username,public_metrics,verified",
        }
        headers = {"Authorization": f"Bearer {bearer_token}"}

        try:
            resp = httpx.get(url, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            raw_tweets.extend(data.get("data", []))
        except Exception as e:
            logger.warning(f"  X API batch çekme hatası: {e}")

    return raw_tweets


def raw_to_tweet_record(raw: Dict[str, Any], session_id: str) -> Optional[TweetRecord]:
    """Ham X API yanıtını TweetRecord'a dönüştür."""
    try:
        metrics = raw.get("public_metrics", {})
        return TweetRecord(
            tweet_id=raw["id"],
            text=raw.get("text", ""),
            language=raw.get("lang"),
            likes=metrics.get("like_count", 0),
            retweets=metrics.get("retweet_count", 0),
            replies=metrics.get("reply_count", 0),
            quotes=metrics.get("quote_count", 0),
            bookmarks=metrics.get("bookmark_count", 0),
            impressions=metrics.get("impression_count", 0),
            created_at=raw.get("created_at"),
            source="x_api",
            collection_session_id=session_id,
        )
    except Exception as e:
        logger.warning(f"  raw_to_tweet_record hatası ({raw.get('id')}): {e}")
        return None


# ─────────────────────────────────────────────
# Transform — türetilmiş alanlar
# ─────────────────────────────────────────────

def compute_thread_role(tweet: TweetRecord) -> str:
    if not tweet.is_thread:
        return "tek_tweet"
    if tweet.thread_position == 1:
        return "hook_tweet"
    if tweet.thread_position == tweet.thread_length:
        return "close_tweet"
    return "body_tweet"


def compute_viral_level(score: Optional[float]) -> str:
    if score is None:
        return "low"
    if score >= 12:
        return "viral"
    if score >= 8:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


# ─────────────────────────────────────────────
# DB işlemleri
# ─────────────────────────────────────────────

def get_existing_tweet_ids(conn, tweet_ids: List[str]) -> set[str]:
    if not tweet_ids:
        return set()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT tweet_id FROM tweets WHERE tweet_id = ANY(%s)",
            (tweet_ids,),
        )
        return {row[0] for row in cur.fetchall()}


def upsert_session(conn, session: MinerSession) -> None:
    stats = session.collection_stats
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO miner_sessions (
                session_id, collected_at, target_user, niche, mode,
                tweet_count_raw, tweet_count_filtered, paper_count,
                dataset_count, api_calls_made, filter_pass_rate,
                avg_engagement_rate, errors, warnings, raw_json
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (session_id) DO UPDATE SET
                tweet_count_filtered = EXCLUDED.tweet_count_filtered,
                paper_count          = EXCLUDED.paper_count,
                dataset_count        = EXCLUDED.dataset_count,
                warnings             = EXCLUDED.warnings
            """,
            (
                session.session_id,
                session.collected_at,
                session.target_user,
                session.niche,
                None,  # mode — Miner JSON'dan gelmiyorsa null
                stats.tweets_fetched_raw if stats else 0,
                session.tweet_count,
                session.paper_count,
                session.dataset_count,
                stats.api_calls_made if stats else 0,
                stats.filter_pass_rate if stats else None,
                stats.avg_engagement_rate if stats else None,
                json.dumps(session.errors),
                json.dumps(session.warnings),
                session.model_dump_json(),
            ),
        )
    conn.commit()


def upsert_tweets(
    conn,
    tweets: List[TweetRecord],
    embeddings: List[List[float]],
    session_id: str,
    existing_ids: set[str],
) -> Tuple[int, int]:
    """
    Döner: (inserted, updated)
    """
    inserted = updated = 0

    rows = []
    for tweet, emb in zip(tweets, embeddings):
        thread_role  = compute_thread_role(tweet)
        viral_level  = compute_viral_level(tweet.priority_score)

        # thread_complete: tüm kardeşler zaten DB'deyse true (basit kontrol)
        thread_complete = (
            not tweet.is_thread
            or len(tweet.thread_tweet_ids) == 0
            or all(tid in existing_ids for tid in tweet.thread_tweet_ids)
        )

        rows.append((
            tweet.tweet_id,
            session_id,
            tweet.text,
            tweet.language,
            None,  # hook_text — Lab doldurur
            tweet.username,
            tweet.display_name,
            tweet.author_followers,
            tweet.author_verified,
            tweet.created_at,
            tweet.collected_at,
            tweet.likes,
            tweet.retweets,
            tweet.replies,
            tweet.quotes,
            tweet.bookmarks,
            tweet.impressions,
            tweet.engagement_rate,
            tweet.bookmark_rate,
            tweet.reply_to_like_ratio,
            tweet.priority_score,
            tweet.priority,
            tweet.has_media,
            tweet.media_type,
            tweet.media_count,
            tweet.is_thread,
            tweet.thread_position,
            tweet.thread_length,
            tweet.thread_tweet_ids or None,
            thread_complete,
            tweet.has_link,
            tweet.link_domain,
            tweet.hashtags or None,
            tweet.hashtag_count,
            tweet.mention_count,
            tweet.source,
            tweet.query_used,
            thread_role,
            viral_level,
            emb,            # vector(1536)
            False,          # lab_processed
            True,           # embedding_generated
            tweet.tweet_url,
            tweet.virality_punch,
        ))

    if not rows:
        return 0, 0

    query = """
        INSERT INTO tweets (
            tweet_id, session_id, text, language, hook_text,
            username, display_name, author_followers, author_verified,
            created_at, collected_at,
            likes, retweets, replies, quotes, bookmarks, impressions,
            engagement_rate, bookmark_rate, reply_to_like_ratio,
            priority_score, priority,
            has_media, media_type, media_count,
            is_thread, thread_position, thread_length, thread_tweet_ids, thread_complete,
            has_link, link_domain,
            hashtags, hashtag_count, mention_count,
            source, query_used,
            thread_role, viral_level,
            embedding, lab_processed, embedding_generated,
            tweet_url, virality_punch
        ) VALUES %s
        ON CONFLICT (tweet_id) DO UPDATE SET
            likes                = EXCLUDED.likes,
            retweets             = EXCLUDED.retweets,
            replies              = EXCLUDED.replies,
            quotes               = EXCLUDED.quotes,
            bookmarks            = EXCLUDED.bookmarks,
            impressions          = EXCLUDED.impressions,
            engagement_rate      = EXCLUDED.engagement_rate,
            bookmark_rate        = EXCLUDED.bookmark_rate,
            reply_to_like_ratio  = EXCLUDED.reply_to_like_ratio,
            priority_score       = EXCLUDED.priority_score,
            viral_level          = EXCLUDED.viral_level,
            thread_complete      = EXCLUDED.thread_complete,
            tweet_url            = COALESCE(EXCLUDED.tweet_url, tweets.tweet_url),
            virality_punch       = EXCLUDED.virality_punch,
            updated_at           = NOW()
        RETURNING (xmax = 0) AS is_insert
    """

    from psycopg2.extras import execute_values  # noqa

    with conn.cursor() as cur:
        execute_values(cur, query, rows, template=None, page_size=500)
        results = cur.fetchall()
        inserted = sum(1 for r in results if r[0])
        updated  = sum(1 for r in results if not r[0])

    conn.commit()
    return inserted, updated


def upsert_arxiv_papers(conn, papers, session_id: str, embedder: Embedder) -> int:
    if not papers:
        return 0

    rows = []
    texts = [f"{p.title or ''} {p.abstract_snippet or ''}".strip() for p in papers]
    embeddings = embedder.embed_batch(texts)

    for paper, emb in zip(papers, embeddings):
        rows.append((
            session_id,
            paper.arxiv_id,
            paper.title,
            paper.abstract_snippet,
            paper.authors or None,
            paper.submitted_date,
            paper.pdf_url,
            paper.relevance_score,
            paper.primary_category,
            emb,
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO arxiv_papers (
                session_id, arxiv_id, title, abstract_snippet, authors,
                submitted_date, pdf_url, relevance_score, primary_category, embedding
            ) VALUES %s
            ON CONFLICT (arxiv_id) DO NOTHING
            """,
            rows,
        )
    conn.commit()
    return len(rows)


def upsert_kaggle_datasets(conn, datasets, session_id: str) -> int:
    if not datasets:
        return 0

    rows = [
        (
            session_id,
            d.dataset_id,
            d.title,
            d.url,
            d.usability_rating,
            d.total_votes,
            d.last_updated,
            d.file_formats or None,
            d.row_count_estimate,
            d.relevant_columns or None,
            d.notes,
        )
        for d in datasets
    ]

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO kaggle_datasets (
                session_id, dataset_id, title, url,
                usability_rating, total_votes, last_updated,
                file_formats, row_count_estimate, relevant_columns, notes
            ) VALUES %s
            ON CONFLICT (dataset_id) DO NOTHING
            """,
            rows,
        )
    conn.commit()
    return len(rows)


# ─────────────────────────────────────────────
# Ana pipeline
# ─────────────────────────────────────────────

def ingest_session(json_path: Path, embedder: Embedder, conn) -> Dict[str, Any]:
    """Tek bir session JSON'unu işle."""
    logger.info(f"━━━ Session: {json_path.name} ━━━")

    # 1. Load
    with open(json_path, encoding="utf-8") as f:
        raw = json.load(f)

    # 2. Validate
    try:
        session = MinerSession.model_validate(raw)
    except Exception as e:
        logger.error(f"Validasyon hatası: {e}")
        return {"status": "error", "file": str(json_path), "error": str(e)}

    logger.info(f"  {session.tweet_count} tweet, {session.paper_count} paper, {session.dataset_count} dataset")

    # Session kaydı
    upsert_session(conn, session)

    # Tüm tweet ID'lerini topla
    all_tweet_ids = [t.tweet_id for t in session.tweets]
    existing_ids  = get_existing_tweet_ids(conn, all_tweet_ids)

    # 3. Thread genişletme
    bearer_token = os.getenv("X_BEARER_TOKEN")
    extra_tweets: List[TweetRecord] = []

    for tweet in session.tweets:
        if tweet.is_thread and tweet.thread_tweet_ids:
            raws = fetch_missing_thread_siblings(tweet, existing_ids, bearer_token)
            for r in raws:
                rec = raw_to_tweet_record(r, session.session_id)
                if rec and rec.tweet_id not in existing_ids:
                    extra_tweets.append(rec)
                    existing_ids.add(rec.tweet_id)

    all_tweets = session.tweets + extra_tweets
    if extra_tweets:
        logger.info(f"  Thread genişletme: +{len(extra_tweets)} ek tweet eklendi")

    # 4 & 5. Dedup + Transform (upsert içinde yapılır)

    # 6. Embed
    logger.info(f"  Embedding hesaplanıyor ({len(all_tweets)} tweet)...")
    texts = [t.text for t in all_tweets]
    embeddings = embedder.embed_batch(texts)

    # 7. Upsert tweets
    inserted, updated = upsert_tweets(conn, all_tweets, embeddings, session.session_id, existing_ids)
    logger.info(f"  Tweets → {inserted} eklendi, {updated} güncellendi")

    # arXiv
    paper_count = upsert_arxiv_papers(conn, session.arxiv_papers, session.session_id, embedder)
    if paper_count:
        logger.info(f"  arXiv → {paper_count} paper eklendi")

    # Kaggle
    dataset_count = upsert_kaggle_datasets(conn, session.kaggle_datasets, session.session_id)
    if dataset_count:
        logger.info(f"  Kaggle → {dataset_count} dataset eklendi")

    return {
        "status": "ok",
        "session_id": session.session_id,
        "tweets_inserted": inserted,
        "tweets_updated": updated,
        "papers": paper_count,
        "datasets": dataset_count,
    }


def ingest_all(data_dir: Path, embedder: Embedder, conn) -> List[Dict[str, Any]]:
    """data/collections/ altındaki tüm session JSON'larını işle."""
    files = sorted(data_dir.glob("session_*.json"))
    if not files:
        logger.warning(f"Hiç session JSON bulunamadı: {data_dir}")
        return []

    results = []
    for f in files:
        result = ingest_session(f, embedder, conn)
        results.append(result)

    ok  = sum(1 for r in results if r["status"] == "ok")
    err = len(results) - ok
    logger.info(f"\n✅ Tamamlandı: {ok} session işlendi, {err} hata")
    return results


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="TwitterYoldas Ingestion Pipeline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("json_file", nargs="?", help="İşlenecek session JSON dosyası")
    group.add_argument("--all", action="store_true", help="data/collections/ altındaki tümünü işle")
    args = parser.parse_args()

    embedder = Embedder()
    conn = get_connection()

    try:
        if args.all:
            data_dir = Path(__file__).parent.parent / "data" / "collections"
            ingest_all(data_dir, embedder, conn)
        else:
            ingest_session(Path(args.json_file), embedder, conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
