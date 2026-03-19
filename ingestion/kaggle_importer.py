#!/usr/bin/env python3
"""
kaggle_importer.py — Kaggle tweet dataset → TwitterYoldas DB

Kaggle JSON formatındaki tweet datasetini okur,
Miner pipeline'ı ile aynı threshold + transform mantığını uygular
ve ingester.py üzerinden DB'ye yazar.

Kullanım:
  python ingestion/kaggle_importer.py --file data/kaggle/twitter-march-2024/dataset_*.json
  python ingestion/kaggle_importer.py --file data/kaggle/twitter-march-2024/dataset_*.json --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("kaggle_importer")

# ─── Eşikler (Miner ile aynı) ───────────────────────────────────────────────
MIN_THRESHOLDS = {
    "en": {"likes": 500, "impressions": 10_000},
    "tr": {"likes": 100, "impressions": 3_000},
}

# ─── Yardımcı fonksiyonlar ───────────────────────────────────────────────────

def _safe_int(val) -> int:
    try:
        return int(val) if val is not None else 0
    except (ValueError, TypeError):
        return 0


def _parse_date(raw) -> Optional[str]:
    """Twitter date string → ISO 8601."""
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw.isoformat()
    for fmt in ("%a %b %d %H:%M:%S %z %Y", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(raw, fmt).isoformat()
        except ValueError:
            continue
    return None


def _extract_hashtags(text: str) -> List[str]:
    return re.findall(r"#(\w+)", text)


def _compute_priority_score(likes, retweets, replies, quotes, bookmarks, impressions) -> Optional[float]:
    if impressions <= 0:
        return None
    return round(
        (likes * 1.0 + retweets * 2.5 + replies * 1.5 + quotes * 3.0 + bookmarks * 4.0)
        / impressions * 100,
        4,
    )


def _viral_level(score: Optional[float]) -> str:
    if score is None:
        return "low"
    if score >= 12:
        return "viral"
    if score >= 8:
        return "high"
    if score >= 4:
        return "medium"
    return "low"


# ─── Kaggle JSON satırı → TweetRecord dict ───────────────────────────────────

def kaggle_row_to_record(row: Dict[str, Any], session_id: str) -> Optional[Dict[str, Any]]:
    """
    Kaggle tweet-scraper JSON formatını Miner TweetRecord formatına dönüştürür.
    Filtreden geçemezse None döner.
    """
    # RT ve reply'leri atla
    if row.get("isRetweet") or row.get("isReply"):
        return None

    text = (row.get("text") or "").strip()
    if not text or text.startswith("RT @"):
        return None

    # Engagement metrikleri
    likes       = _safe_int(row.get("likeCount"))
    retweets    = _safe_int(row.get("retweetCount"))
    replies     = _safe_int(row.get("replyCount"))
    quotes      = _safe_int(row.get("quoteCount"))
    bookmarks   = _safe_int(row.get("bookmarkCount"))
    impressions = _safe_int(row.get("viewCount"))

    lang = row.get("lang", "en") or "en"
    # Desteklenmeyen dilleri EN olarak işle
    if lang not in ("tr",):
        lang = "en"

    thresholds = MIN_THRESHOLDS.get(lang, MIN_THRESHOLDS["en"])

    # Hesaplanan oranlar
    eng_rate = round((likes + retweets + replies + quotes) / impressions, 6) if impressions > 0 else None
    bkm_rate = round(bookmarks / impressions, 6) if impressions > 0 else None
    r2l_rate = round(replies / likes, 6) if likes > 0 else None
    priority_score = _compute_priority_score(likes, retweets, replies, quotes, bookmarks, impressions)

    # Threshold filtresi — minimum kalite bariyeri
    if impressions < 1_000 or likes < 50:
        return None

    passes = False
    if likes >= thresholds["likes"] and impressions >= thresholds["impressions"]:
        passes = True
    if (eng_rate or 0) >= 0.03 and impressions >= 1_000:
        passes = True
    if (bkm_rate or 0) >= 0.015 and impressions >= 1_000:
        passes = True
    if not passes:
        return None

    # Yazar bilgileri
    author = row.get("author") or {}
    username     = author.get("userName") or author.get("name")
    display_name = author.get("name") or username
    followers    = _safe_int(author.get("followers"))
    verified     = bool(author.get("isBlueVerified") or author.get("verified"))

    # Medya
    media_list = row.get("media") or row.get("extendedEntities", {}).get("media", [])
    has_media  = bool(media_list)
    media_type = None
    if has_media and media_list:
        mt = media_list[0].get("type", "") if isinstance(media_list[0], dict) else ""
        if "video" in str(mt).lower():
            media_type = "video"
        elif "animated_gif" in str(mt).lower():
            media_type = "gif"
        else:
            media_type = "görsel"

    # Thread tespiti
    is_thread    = "🧵" in text or text.count("\n\n") >= 2
    thread_length = text.count("🧵") + 1 if is_thread else 1

    # Hashtag
    hashtags = _extract_hashtags(text)

    # Link
    has_link = "https://" in text or "http://" in text

    # Thread role
    thread_role = "tek_tweet"
    if is_thread:
        thread_role = "hook_tweet"

    tweet_id = str(row.get("id", ""))
    if not tweet_id:
        return None

    return {
        "tweet_id":              tweet_id,
        "text":                  text,
        "username":              username,
        "display_name":          display_name,
        "author_followers":      followers,
        "author_verified":       verified,
        "created_at":            _parse_date(row.get("createdAt")),
        "collected_at":          datetime.now(timezone.utc).isoformat(),

        "likes":                 likes,
        "retweets":              retweets,
        "replies":               replies,
        "quotes":                quotes,
        "bookmarks":             bookmarks,
        "impressions":           impressions,

        "engagement_rate":       eng_rate,
        "bookmark_rate":         bkm_rate,
        "reply_to_like_ratio":   r2l_rate,
        "priority_score":        priority_score,
        "priority":              "high" if priority_score and priority_score >= 8 else "normal",

        "has_media":             has_media,
        "media_type":            media_type,
        "media_count":           len(media_list) if media_list else 0,

        "is_thread":             is_thread,
        "thread_position":       1,
        "thread_length":         thread_length,
        "thread_tweet_ids":      [],

        "has_link":              has_link,
        "link_domain":           None,

        "language":              lang,
        "hashtag_count":         len(hashtags),
        "hashtags":              hashtags,
        "mention_count":         text.count("@"),

        "source":                "kaggle",
        "query_used":            f"kaggle:{Path(row.get('_source_file', '')).stem}",
        "collection_session_id": session_id,

        # Türetilmiş
        "thread_role":           thread_role,
        "viral_level":           _viral_level(priority_score),
    }


# ─── MinerSession JSON builder ────────────────────────────────────────────────

def build_session_json(session_id: str, tweets: List[Dict[str, Any]], source_file: str) -> Dict[str, Any]:
    rates = [t["engagement_rate"] for t in tweets if t.get("engagement_rate")]
    avg_eng = round(sum(rates) / len(rates), 6) if rates else None

    return {
        "session_id":   session_id,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "target_user":  "@ciftcibahadir",
        "niche":        "broad_viral",
        "mode":         "kaggle_import",

        "tweets":        tweets,
        "tweet_count":   len(tweets),
        "arxiv_papers":  [],
        "paper_count":   0,
        "kaggle_datasets": [],
        "dataset_count": 0,

        "collection_stats": {
            "api_calls_made":      0,
            "tweets_fetched_raw":  len(tweets),
            "tweets_after_filter": len(tweets),
            "filter_pass_rate":    1.0,
            "avg_engagement_rate": avg_eng,
            "avg_bookmarks":       round(sum(t["bookmarks"] for t in tweets) / len(tweets), 1) if tweets else 0,
            "top_media_type":      None,
            "thread_percentage":   round(sum(1 for t in tweets if t["is_thread"]) / len(tweets), 4) if tweets else 0,
            "source_file":         source_file,
        },
        "errors":   [],
        "warnings": [],
    }


# ─── Ana fonksiyon ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Kaggle Tweet Dataset → TwitterYoldas DB")
    parser.add_argument("--file", required=True, help="Kaggle JSON dosya yolu")
    parser.add_argument("--dry-run", action="store_true", help="Sadece say, DB'ye yazma")
    parser.add_argument("--no-ingest", action="store_true", help="JSON üret ama DB'ye yazma")
    args = parser.parse_args()

    json_path = Path(args.file)
    if not json_path.exists():
        logger.error(f"Dosya bulunamadı: {json_path}")
        sys.exit(1)

    logger.info(f"━━━ Kaggle Importer — {json_path.name} ━━━")

    # JSON oku
    with open(json_path, encoding="utf-8") as f:
        raw_data = json.load(f)

    if not isinstance(raw_data, list):
        logger.error("Beklenen format: JSON array")
        sys.exit(1)

    logger.info(f"Ham kayıt sayısı: {len(raw_data)}")

    # Session ID
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    output_dir = ROOT / "data" / "collections"
    output_dir.mkdir(parents=True, exist_ok=True)
    existing = list(output_dir.glob(f"session_{today}_*.json"))
    session_num = str(len(existing) + 1).zfill(3)
    session_id = f"session_{today}_{session_num}_kaggle"

    # Dönüştür + filtrele
    tweets: List[Dict[str, Any]] = []
    seen_ids: set = set()
    skipped_rt    = 0
    skipped_reply = 0
    skipped_threshold = 0
    skipped_dup   = 0

    for row in raw_data:
        if row.get("isRetweet"):
            skipped_rt += 1
            continue
        if row.get("isReply"):
            skipped_reply += 1
            continue

        rec = kaggle_row_to_record(row, session_id)
        if rec is None:
            skipped_threshold += 1
            continue

        # Duplicate tweet_id kontrolü
        tid = rec["tweet_id"]
        if tid in seen_ids:
            skipped_dup += 1
            continue
        seen_ids.add(tid)
        tweets.append(rec)

    logger.info(f"Retweet atlandı:  {skipped_rt}")
    logger.info(f"Reply atlandı:    {skipped_reply}")
    logger.info(f"Threshold dışı:   {skipped_threshold}")
    logger.info(f"Duplicate atlandı:{skipped_dup}")
    logger.info(f"İşlenecek tweet:  {len(tweets)}")

    # Viral dağılımı
    from collections import Counter
    viral_dist = Counter(t["viral_level"] for t in tweets)
    logger.info(f"Viral dağılımı: {dict(viral_dist)}")

    if args.dry_run:
        logger.info("[dry-run] DB'ye yazılmıyor.")

        # Top 5 göster
        top5 = sorted(tweets, key=lambda t: t["priority_score"] or 0, reverse=True)[:5]
        for i, t in enumerate(top5, 1):
            logger.info(f"  #{i} @{t['username']} | likes:{t['likes']} views:{t['impressions']} score:{t['priority_score']} | {t['text'][:70]}")
        return

    # Session JSON kaydet
    session_data = build_session_json(session_id, tweets, str(json_path))
    output_path  = output_dir / f"{session_id}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"Session JSON: {output_path}")

    if args.no_ingest:
        logger.info("--no-ingest: DB yazma atlandı.")
        return

    # Ingester'a besle
    logger.info("Ingestion başlatılıyor...")
    from ingestion.ingester import ingest_session, get_connection
    from ingestion.embedder import Embedder

    embedder = Embedder()
    conn = get_connection()
    try:
        result = ingest_session(output_path, embedder, conn)
        logger.info(f"✅ Ingestion tamamlandı: {result}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
