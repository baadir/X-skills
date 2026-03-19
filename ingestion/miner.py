#!/usr/bin/env python3
"""
miner.py — The Miner (Twitter API v2 — cookie'siz)

Twitter API v2 Bearer Token ile viral tweet toplar.
İki strateji paralel çalışır:
  1. NİŞ sorguları  — AI, MCP, LangChain, vibe coding vb.
  2. GENEL VİRAL    — niş bağımsız, sadece engagement eşiğiyle

Kullanım:
  python ingestion/miner.py                     # quick mode (varsayılan)
  python ingestion/miner.py --mode deep         # daha fazla tweet
  python ingestion/miner.py --dry-run           # DB'ye yazma, sadece logla
  python ingestion/miner.py --no-ingest         # JSON kaydet, DB'ye yazma

Gerekli:
  - .env  (X_BEARER_TOKEN + DB_*)
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("miner")

DATA_DIR = ROOT / "data" / "collections"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TWITTER_API_BASE = "https://api.twitter.com/2"

# ─────────────────────────────────────────────────────────────────────────────
# Sorgu stratejileri
# ─────────────────────────────────────────────────────────────────────────────

# 1. Nişe özel — topic keyword (free tier: engagement operatörü yok, post-fetch filtre)
NICHE_QUERIES = [
    # AI agent / agentic
    "(\"AI agent\" OR \"agentic AI\" OR \"multi-agent\") -is:retweet",
    # MCP / araçlar
    "(\"MCP\" OR \"model context protocol\" OR \"claude mcp\") -is:retweet",
    # Framework / tooling
    "(LangChain OR LangGraph OR CrewAI OR AutoGen) -is:retweet",
    # Vibe coding / AI coding
    "(\"vibe coding\" OR \"claude code\" OR \"cursor ai\" OR windsurf) -is:retweet",
    # Türkçe niş
    "(\"yapay zeka\" OR \"AI agent\") lang:tr -is:retweet",
]

# 2. Genel viral — niş bağımsız: bilinen viral hesaplar + high-signal topic'ler
# min_faves free tier'da yok → post-fetch filtre ile yüksek like eşiği uygulanır
VIRAL_QUERIES = [
    # Referans AI hesaplar — kaliteli + viral içerik üretirler
    "(from:karpathy OR from:swyx OR from:levelsio OR from:mckaywrigley OR from:bentossell) -is:retweet",
    # Üst düzey founder/builder hesapları
    "(from:sama OR from:elonmusk OR from:paulg OR from:naval OR from:dhh) -is:retweet",
    # AI startup / araştırma hesapları
    "(from:AnthropicAI OR from:OpenAI OR from:GoogleDeepMind OR from:mistralai) -is:retweet",
    # Thread formatı — genellikle yüksek engagement
    "\U0001f9f5 lang:en -is:retweet",
    # Türkçe genel viral
    "lang:tr -is:retweet (teknoloji OR yazılım OR kariyer OR girişim OR iş)",
]

# Mode başına sorgu başına tweet limiti
LIMIT_PER_QUERY = {
    "quick": 20,
    "deep":  50,
}

# Post-fetch filtre — free tier'da engagement operatörü olmadığından burada uygula
MIN_LIKES = {
    "niche":  {"en": 30,  "tr": 10},
    "viral":  {"en": 200, "tr": 50},
}


# ─────────────────────────────────────────────────────────────────────────────
# Twitter API v2 arama
# ─────────────────────────────────────────────────────────────────────────────

def _make_headers() -> dict:
    token = os.getenv("X_BEARER_TOKEN")
    if not token:
        raise RuntimeError("X_BEARER_TOKEN eksik. .env dosyasını kontrol et.")
    return {"Authorization": f"Bearer {token}"}


def search_tweets(
    query: str,
    max_results: int = 20,
    headers: dict | None = None,
) -> list[dict]:
    """
    Twitter API v2 recent search — query başına max_results tweet döner.
    Rate limit (429) otomatik beklenir. Impression_count sadece kendi
    tweetlerimiz için dolu olur; burada 0 kabul edilir.
    """
    if headers is None:
        headers = _make_headers()

    # max_results 10-100 arası olmalı
    max_results = max(10, min(100, max_results))

    params = {
        "query": query,
        "max_results": max_results,
        "tweet.fields": "public_metrics,created_at,lang,author_id,entities,attachments,referenced_tweets",
        "expansions": "author_id,attachments.media_keys",
        "user.fields": "username,name,public_metrics,verified",
        "media.fields": "type,duration_ms",
        "sort_order": "relevancy",
    }

    while True:
        resp = requests.get(
            f"{TWITTER_API_BASE}/tweets/search/recent",
            headers=headers,
            params=params,
            timeout=30,
        )

        if resp.status_code == 429:
            reset = int(resp.headers.get("x-rate-limit-reset", time.time() + 60))
            wait = max(5, reset - int(time.time())) + 5
            logger.warning("Rate limit aşıldı. %d saniye bekleniyor...", wait)
            time.sleep(wait)
            continue

        if not resp.ok:
            logger.warning("API hata %d: %s | query: %s", resp.status_code, resp.text[:200], query[:60])
            return []

        data = resp.json()
        tweets = data.get("data", [])
        if not tweets:
            return []

        # Kullanıcı bilgilerini indexle (expansions)
        users_by_id: dict[str, dict] = {}
        for u in data.get("includes", {}).get("users", []):
            users_by_id[u["id"]] = u

        # Medya bilgilerini indexle
        media_by_key: dict[str, dict] = {}
        for m in data.get("includes", {}).get("media", []):
            media_by_key[m["media_key"]] = m

        results = []
        for t in tweets:
            results.append(_build_record(t, users_by_id, media_by_key, query))

        return results


def _build_record(
    tweet: dict,
    users_by_id: dict[str, dict],
    media_by_key: dict[str, dict],
    query: str,
) -> dict[str, Any]:
    """Twitter API v2 tweet dict → Miner/ingester uyumlu record dict."""
    metrics = tweet.get("public_metrics", {})
    likes       = metrics.get("like_count", 0) or 0
    retweets    = metrics.get("retweet_count", 0) or 0
    replies     = metrics.get("reply_count", 0) or 0
    quotes      = metrics.get("quote_count", 0) or 0
    bookmarks   = metrics.get("bookmark_count", 0) or 0
    impressions = metrics.get("impression_count", 0) or 0  # kendi tweetimiz değilse 0

    # Engagement hesaplama — impressions yoksa likes bazlı proxy
    if impressions > 0:
        eng_rate    = round((likes + retweets + replies + quotes) / impressions, 6)
        bkm_rate    = round(bookmarks / impressions, 6)
    else:
        eng_rate = None
        bkm_rate = None

    reply_like_ratio = round(replies / likes, 6) if likes > 0 else None

    # Priority score (impressions olmadan likes ağırlıklı)
    if impressions > 0:
        priority_score = round(
            (likes * 1.0 + retweets * 2.5 + replies * 1.5 + quotes * 3.0 + bookmarks * 4.0)
            / impressions * 100, 4
        )
    else:
        # Impressions yoksa: likes normalize edilmiş proxy
        base = max(likes, 1)
        priority_score = round(
            (likes * 1.0 + retweets * 2.5 + replies * 1.5 + quotes * 3.0 + bookmarks * 4.0)
            / base, 4
        )

    if priority_score >= 12:
        priority = "viral"
    elif priority_score >= 8:
        priority = "high"
    elif priority_score >= 4:
        priority = "medium"
    else:
        priority = "normal"

    # Yazar
    user = users_by_id.get(tweet.get("author_id", ""), {})
    user_metrics = user.get("public_metrics", {})

    # Medya
    attachment_keys = (tweet.get("attachments") or {}).get("media_keys", [])
    media_items = [media_by_key[k] for k in attachment_keys if k in media_by_key]
    has_media = bool(media_items)
    media_type = None
    if media_items:
        types = [m.get("type", "") for m in media_items]
        if "video" in types:
            media_type = "video"
        elif "animated_gif" in types:
            media_type = "gif"
        else:
            media_type = "görsel"

    # Link + hashtag
    entities = tweet.get("entities", {}) or {}
    urls = entities.get("urls", [])
    external_urls = [u for u in urls if "twitter.com" not in u.get("expanded_url", "") and "t.co" != u.get("expanded_url", "")]
    has_link = bool(external_urls)
    link_domain = None
    if has_link:
        try:
            link_domain = urlparse(external_urls[0]["expanded_url"]).netloc
        except Exception:
            pass

    hashtags = [h["tag"] for h in entities.get("hashtags", [])]

    text = tweet.get("text", "")

    # Thread tespiti
    refs = tweet.get("referenced_tweets") or []
    is_thread = "🧵" in text

    # Tarih
    created_at = tweet.get("created_at", "")

    return {
        "tweet_id":             tweet["id"],
        "text":                 text,
        "language":             tweet.get("lang", "en"),
        "username":             user.get("username"),
        "display_name":         user.get("name"),
        "author_followers":     user_metrics.get("followers_count"),
        "author_verified":      user.get("verified", False),
        "created_at":           created_at,
        "collected_at":         datetime.now(timezone.utc).isoformat(),

        "likes":                likes,
        "retweets":             retweets,
        "replies":              replies,
        "quotes":               quotes,
        "bookmarks":            bookmarks,
        "impressions":          impressions,

        "engagement_rate":      eng_rate,
        "bookmark_rate":        bkm_rate,
        "reply_to_like_ratio":  reply_like_ratio,
        "priority_score":       priority_score,
        "priority":             priority,

        "has_media":            has_media,
        "media_type":           media_type,
        "media_count":          len(media_items),

        "is_thread":            is_thread,
        "thread_position":      1,
        "thread_length":        1,
        "thread_tweet_ids":     [],

        "has_link":             has_link,
        "link_domain":          link_domain,

        "hashtag_count":        len(hashtags),
        "hashtags":             hashtags,
        "mention_count":        len(entities.get("mentions", [])),

        "source":               "x_api",
        "query_used":           query,
        "collection_session_id": "",  # run_collection tarafından doldurulur
    }


# ─────────────────────────────────────────────────────────────────────────────
# Post-fetch filtre
# ─────────────────────────────────────────────────────────────────────────────

def passes_threshold(rec: dict, strategy: str) -> bool:
    """Minimum like eşiğini geç."""
    lang = rec.get("language", "en") if rec.get("language") in ("en", "tr") else "en"
    min_l = MIN_LIKES[strategy][lang]
    return rec.get("likes", 0) >= min_l


# ─────────────────────────────────────────────────────────────────────────────
# Ana toplama
# ─────────────────────────────────────────────────────────────────────────────

def run_collection(mode: str, session_id: str) -> list[dict[str, Any]]:
    headers = _make_headers()
    limit = LIMIT_PER_QUERY.get(mode, 20)
    all_records: list[dict] = []
    seen_ids: set[str] = set()

    def _run_queries(queries: list[str], strategy: str) -> None:
        label = "NİŞ" if strategy == "niche" else "VİRAL"
        for query in queries:
            logger.info("[%s] %s", label, query[:80])
            try:
                records = search_tweets(query, max_results=limit, headers=headers)
            except Exception as e:
                logger.warning("  Arama hatası: %s", e)
                time.sleep(2)
                continue

            passed = 0
            for rec in records:
                tid = rec["tweet_id"]
                if tid in seen_ids:
                    continue
                if rec["text"].startswith("RT @"):
                    continue
                if not passes_threshold(rec, strategy):
                    continue
                seen_ids.add(tid)
                rec["collection_session_id"] = session_id
                all_records.append(rec)
                passed += 1

            logger.info("  %d/%d tweet geçti (toplam: %d)", passed, len(records), len(all_records))
            time.sleep(1.5)  # sorgular arası nazik bekleme

    _run_queries(NICHE_QUERIES, "niche")
    _run_queries(VIRAL_QUERIES, "viral")

    logger.info("Toplam: %d benzersiz tweet toplandı.", len(all_records))
    return all_records


# ─────────────────────────────────────────────────────────────────────────────
# Session JSON
# ─────────────────────────────────────────────────────────────────────────────

def build_session_json(session_id: str, tweets: list[dict], mode: str) -> dict:
    rates = [t["engagement_rate"] for t in tweets if t.get("engagement_rate")]
    avg_eng = round(sum(rates) / len(rates), 6) if rates else None

    media_types = [t["media_type"] for t in tweets if t.get("media_type")]
    top_media = Counter(media_types).most_common(1)[0][0] if media_types else None

    thread_count = sum(1 for t in tweets if t.get("is_thread"))

    return {
        "session_id":   session_id,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "target_user":  "@ciftcibahadir",
        "niche":        "niche+viral",
        "mode":         mode,

        "tweets":           tweets,
        "tweet_count":      len(tweets),
        "arxiv_papers":     [],
        "paper_count":      0,
        "kaggle_datasets":  [],
        "dataset_count":    0,

        "collection_stats": {
            "api_calls_made":       len(NICHE_QUERIES) + len(VIRAL_QUERIES),
            "tweets_fetched_raw":   len(tweets),
            "tweets_after_filter":  len(tweets),
            "filter_pass_rate":     1.0,
            "avg_engagement_rate":  avg_eng,
            "avg_bookmarks":        round(sum(t["bookmarks"] for t in tweets) / len(tweets), 1) if tweets else 0,
            "top_media_type":       top_media,
            "thread_percentage":    round(thread_count / len(tweets), 4) if tweets else 0,
        },
        "errors":   [],
        "warnings": [],
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="TwitterYoldas Miner — Viral Tweet Toplayıcı (Twitter API v2)")
    parser.add_argument("--mode",      choices=["quick", "deep"], default="quick")
    parser.add_argument("--dry-run",   action="store_true", help="Tweet topla ama kaydetme")
    parser.add_argument("--no-ingest", action="store_true", help="JSON kaydet ama DB'ye yazma")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y%m%d")
    existing = list(DATA_DIR.glob(f"session_{date_str}_*.json"))
    session_id = f"session_{date_str}_{str(len(existing) + 1).zfill(3)}"

    logger.info("━━━ The Miner — %s | mode: %s ━━━", session_id, args.mode)

    tweets = run_collection(args.mode, session_id)

    if args.dry_run:
        logger.info("[dry-run] %d tweet toplandı. Kaydedilmedi.", len(tweets))
        return

    session_data = build_session_json(session_id, tweets, args.mode)
    output_path = DATA_DIR / f"{session_id}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Session JSON: %s", output_path)

    if args.no_ingest:
        logger.info("--no-ingest: DB yazma atlandı.")
        return

    logger.info("Ingestion başlatılıyor...")
    from ingestion.ingester import ingest_session, get_connection
    from ingestion.embedder import Embedder

    embedder = Embedder()
    conn = get_connection()
    try:
        result = ingest_session(output_path, embedder, conn)
        logger.info("Ingestion tamamlandı: %s", result)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
