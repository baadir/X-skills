"""
Agent erişim katmanı — SQL filtresi + full-text search + pgvector semantik arama.

Bu modül doğrudan Agent tarafından veya MCP tool olarak çağrılır.
Her fonksiyon bağımsız bir DB bağlantısı açar, sonuç döndürür, kapatır.

─── EMBEDDING GEREKTİRMEYEN FONKSİYONLAR (agent her zaman çağırabilir) ───
  filter_tweets()        — tag, kalite, dil, etkileşim filtresi
  full_text_search()     — PostgreSQL tsvector arama (embedding yok)
  get_top_tweets()       — metriğe göre sıralı liste
  get_full_thread()      — tam thread getir
  signal_distribution()  — algoritma sinyal analizi
  db_stats()             — DB durumu

─── EMBEDDING GEREKTİREN FONKSİYONLAR (OPENAI_API_KEY .env'den okunur) ───
  find_similar_tweets()  — pgvector cosine similarity (query → embed → search)

Örnek:
  from ingestion.agent_tools import full_text_search, filter_tweets, find_similar_tweets

  # Embedding yok — anında çalışır
  results = full_text_search("agentic AI pipeline demo", limit=10)
  results = filter_tweets(ton="egitici", quality_tier=["S","A"])

  # Embedding gerekli — .env'deki OPENAI_API_KEY kullanılır
  results = find_similar_tweets("agentic AI pipeline demo", top_k=5)
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg2  # type: ignore
import psycopg2.extras  # type: ignore
from dotenv import load_dotenv  # type: ignore

sys.path.insert(0, str(Path(__file__).parent.parent))
from ingestion.embedder import Embedder

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

# Lazy singleton embedder (ilk çağrıda init edilir)
_embedder: Optional[Embedder] = None


def _get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


def _get_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "twitter_yoldas"),
        user=os.getenv("DB_USER", "yoldas"),
        password=os.getenv("DB_PASSWORD", "yoldas_secret"),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def _rows_to_list(cur) -> List[Dict[str, Any]]:
    return [dict(row) for row in cur.fetchall()]


# ─────────────────────────────────────────────
# 1. Semantik arama (pgvector cosine similarity)
# ─────────────────────────────────────────────

def find_similar_tweets(
    query_text: str,
    top_k: int = 10,
    language: Optional[str] = None,          # "en" | "tr" | None
    min_quality_tier: Optional[str] = None,  # "S" | "A" | "B" | "C"
    icerik_formu: Optional[str] = None,
    ton: Optional[str] = None,
    only_complete_threads: bool = False,
) -> List[Dict[str, Any]]:
    """
    Semantik benzerlik araması.
    Döner: tweet_id, text, username, similarity, quality_score, icerik_formu, ton, ...
    """
    emb = _get_embedder().embed(query_text)
    vec_str = "[" + ",".join(str(x) for x in emb) + "]"

    filters = ["t.embedding IS NOT NULL"]
    params: List[Any] = [vec_str, vec_str, top_k]

    if language:
        filters.append("t.language = %s")
        params.insert(2, language)

    where = "WHERE " + " AND ".join(filters) if filters else ""

    # quality_tier ve diğer label filtreleri
    label_joins = ""
    if min_quality_tier or icerik_formu or ton:
        label_joins = "JOIN tweet_labels tl ON t.tweet_id = tl.tweet_id"
        tier_order = {"S": 0, "A": 1, "B": 2, "C": 3}
        if min_quality_tier and min_quality_tier in tier_order:
            allowed_tiers = [t for t, o in tier_order.items() if o <= tier_order[min_quality_tier]]
            filters.append(f"tl.quality_tier = ANY(%s)")
            params.insert(2, allowed_tiers)
        if icerik_formu:
            filters.append("tl.icerik_formu = %s")
            params.insert(2, icerik_formu)
        if ton:
            filters.append("tl.ton = %s")
            params.insert(2, ton)

    if only_complete_threads:
        filters.append("t.thread_complete = TRUE")

    where = "WHERE " + " AND ".join(filters) if filters else ""

    sql = f"""
        SELECT
            t.tweet_id, t.text, t.username, t.created_at,
            t.likes, t.retweets, t.bookmarks, t.impressions,
            t.engagement_rate, t.priority_score,
            t.is_thread, t.thread_length, t.thread_role, t.viral_level,
            t.language, t.has_media, t.media_type,
            tl.quality_score, tl.quality_tier,
            tl.icerik_formu, tl.ton, tl.kanca_tipi,
            tl.psikolojik_tetikleyici, tl.algoritma_sinyal,
            tl.hook_text, tl.reasoning,
            1 - (t.embedding <=> %s::vector) AS similarity
        FROM tweets t
        LEFT JOIN tweet_labels tl ON t.tweet_id = tl.tweet_id
        {where}
        ORDER BY t.embedding <=> %s::vector
        LIMIT %s
    """

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            # Params sıralaması: vec_str, (language?), (label filters...), vec_str, top_k
            # Yeniden düzelt: positional
            final_params = _build_params_for_similarity(
                emb, language, min_quality_tier, icerik_formu, ton, only_complete_threads, top_k
            )
            cur.execute(sql, final_params)
            return _rows_to_list(cur)
    finally:
        conn.close()


def _build_params_for_similarity(
    emb, language, min_quality_tier, icerik_formu, ton, only_complete_threads, top_k
):
    """Parametre listesini doğru sırayla oluştur."""
    tier_order = {"S": 0, "A": 1, "B": 2, "C": 3}
    vec_str = "[" + ",".join(str(x) for x in emb) + "]"

    p1 = [vec_str]  # embedding <=> %s (ORDER BY kısmı için ilk)

    middle: List[Any] = []
    if language:
        middle.append(language)
    if min_quality_tier and min_quality_tier in tier_order:
        allowed = [t for t, o in tier_order.items() if o <= tier_order[min_quality_tier]]
        middle.append(allowed)
    if icerik_formu:
        middle.append(icerik_formu)
    if ton:
        middle.append(ton)

    return p1 + middle + [vec_str, top_k]


# ─────────────────────────────────────────────
# 2. Tag filtreli arama
# ─────────────────────────────────────────────

def filter_tweets(
    icerik_formu: Optional[str] = None,
    ton: Optional[str] = None,
    kanca_tipi: Optional[str] = None,
    psikolojik_tetikleyici: Optional[List[str]] = None,  # herhangi biri eşleşsin
    algoritma_sinyal: Optional[str] = None,              # ilk sinyalde arama
    quality_tier: Optional[List[str]] = None,            # ["S", "A"]
    language: Optional[str] = None,
    min_engagement_rate: Optional[float] = None,
    min_bookmarks: Optional[int] = None,
    is_thread: Optional[bool] = None,
    viral_level: Optional[str] = None,
    limit: int = 20,
    order_by: str = "quality_score",                     # quality_score | priority_score | engagement_rate | created_at
) -> List[Dict[str, Any]]:
    """
    Tag filtreli tweet listesi.
    Tüm parametreler opsiyoneldir — sağlanmayan filtrelenmez.
    """
    conditions = ["1=1"]
    params: List[Any] = []

    # Tweet tablosu filtreleri
    if language:
        conditions.append("t.language = %s")
        params.append(language)
    if min_engagement_rate is not None:
        conditions.append("t.engagement_rate >= %s")
        params.append(min_engagement_rate)
    if min_bookmarks is not None:
        conditions.append("t.bookmarks >= %s")
        params.append(min_bookmarks)
    if is_thread is not None:
        conditions.append("t.is_thread = %s")
        params.append(is_thread)
    if viral_level:
        conditions.append("t.viral_level = %s")
        params.append(viral_level)

    # Label filtreleri
    label_conditions = []
    if icerik_formu:
        label_conditions.append("tl.icerik_formu = %s")
        params.append(icerik_formu)
    if ton:
        label_conditions.append("tl.ton = %s")
        params.append(ton)
    if kanca_tipi:
        label_conditions.append("tl.kanca_tipi = %s")
        params.append(kanca_tipi)
    if quality_tier:
        label_conditions.append("tl.quality_tier = ANY(%s)")
        params.append(quality_tier)
    if psikolojik_tetikleyici:
        label_conditions.append("tl.psikolojik_tetikleyici && %s")
        params.append(psikolojik_tetikleyici)
    if algoritma_sinyal:
        label_conditions.append("tl.algoritma_sinyal[1] = %s")
        params.append(algoritma_sinyal)

    join_type = "JOIN" if label_conditions else "LEFT JOIN"
    all_conditions = conditions + label_conditions
    where = "WHERE " + " AND ".join(all_conditions)

    # Güvenli order_by
    order_col_map = {
        "quality_score":   "tl.quality_score",
        "priority_score":  "t.priority_score",
        "engagement_rate": "t.engagement_rate",
        "created_at":      "t.created_at",
        "bookmarks":       "t.bookmarks",
    }
    order_col = order_col_map.get(order_by, "tl.quality_score")

    sql = f"""
        SELECT
            t.tweet_id, t.text, t.username, t.created_at,
            t.likes, t.retweets, t.replies, t.quotes, t.bookmarks, t.impressions,
            t.engagement_rate, t.priority_score,
            t.is_thread, t.thread_length, t.thread_position, t.thread_role,
            t.viral_level, t.language, t.has_media, t.media_type,
            tl.quality_score, tl.quality_tier,
            tl.icerik_formu, tl.ton, tl.kanca_tipi,
            tl.psikolojik_tetikleyici, tl.algoritma_sinyal,
            tl.hook_text, tl.reasoning
        FROM tweets t
        {join_type} tweet_labels tl ON t.tweet_id = tl.tweet_id
        {where}
        ORDER BY {order_col} DESC NULLS LAST
        LIMIT %s
    """
    params.append(limit)

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return _rows_to_list(cur)
    finally:
        conn.close()


# ─────────────────────────────────────────────
# 3. Full-text search — embedding gerektirmez
# ─────────────────────────────────────────────

def full_text_search(
    query: str,
    limit: int = 20,
    language: Optional[str] = None,
    quality_tier: Optional[List[str]] = None,
    icerik_formu: Optional[str] = None,
    ton: Optional[str] = None,
    order_by: str = "rank",   # "rank" | "priority_score" | "quality_score"
) -> List[Dict[str, Any]]:
    """
    PostgreSQL full-text search — OpenAI API gerektirmez.

    query örnekleri:
      "agentic AI"               → her iki kelime geçsin
      "agentic & AI"             → AND
      "thread | liste"           → OR
      "vibe coding"              → tam ibare
      "!langchain"               → langchain olmayan

    Trigram veya stemming yerine tsquery kullanır;
    TR metinler için 'simple' config (stopword'siz) desteklidir.
    """
    if not query or not query.strip():
        return []

    conditions = ["t.search_vector IS NOT NULL"]
    params: List[Any] = []

    # Basit serbest metin → tsquery dönüşümü
    # plainto_tsquery: "agentic AI" → 'agentic' & 'ai'
    conditions.append("t.search_vector @@ plainto_tsquery('english', %s)")
    params.append(query.strip())

    if language:
        conditions.append("t.language = %s")
        params.append(language)

    label_joins = ""
    label_conditions = []
    if quality_tier or icerik_formu or ton:
        label_joins = "LEFT JOIN tweet_labels tl ON t.tweet_id = tl.tweet_id"
        if quality_tier:
            label_conditions.append("tl.quality_tier = ANY(%s)")
            params.append(quality_tier)
        if icerik_formu:
            label_conditions.append("tl.icerik_formu = %s")
            params.append(icerik_formu)
        if ton:
            label_conditions.append("tl.ton = %s")
            params.append(ton)
    else:
        label_joins = "LEFT JOIN tweet_labels tl ON t.tweet_id = tl.tweet_id"

    all_conditions = conditions + label_conditions
    where = "WHERE " + " AND ".join(all_conditions)

    # Sıralama: rank (relevance) veya metrik
    if order_by == "rank":
        order_sql = "ts_rank(t.search_vector, plainto_tsquery('english', %s)) DESC"
        params.append(query.strip())
    elif order_by == "priority_score":
        order_sql = "t.priority_score DESC NULLS LAST"
    elif order_by == "quality_score":
        order_sql = "tl.quality_score DESC NULLS LAST"
    else:
        order_sql = "ts_rank(t.search_vector, plainto_tsquery('english', %s)) DESC"
        params.append(query.strip())

    params.append(limit)

    sql = f"""
        SELECT
            t.tweet_id, t.text, t.username, t.created_at,
            t.likes, t.retweets, t.replies, t.bookmarks, t.impressions,
            t.engagement_rate, t.priority_score,
            t.is_thread, t.thread_length, t.thread_role, t.viral_level,
            t.language, t.has_media, t.media_type,
            tl.quality_score, tl.quality_tier,
            tl.icerik_formu, tl.ton, tl.kanca_tipi,
            tl.hook_text, tl.reasoning,
            ts_rank(t.search_vector, plainto_tsquery('english', '{query.strip()}')) AS fts_rank
        FROM tweets t
        {label_joins}
        {where}
        ORDER BY {order_sql}
        LIMIT %s
    """

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return _rows_to_list(cur)
    finally:
        conn.close()


# ─────────────────────────────────────────────
# 4. En iyi tweet'ler
# ─────────────────────────────────────────────

def get_top_tweets(
    limit: int = 20,
    metric: str = "priority_score",   # priority_score | quality_score | bookmarks | engagement_rate
    quality_tier: Optional[List[str]] = None,
    icerik_formu: Optional[str] = None,
    language: Optional[str] = None,
    only_threads: bool = False,
) -> List[Dict[str, Any]]:
    """En yüksek metrikli tweet'leri getir."""
    return filter_tweets(
        icerik_formu=icerik_formu,
        quality_tier=quality_tier or ["S", "A"],
        language=language,
        is_thread=True if only_threads else None,
        limit=limit,
        order_by=metric,
    )


# ─────────────────────────────────────────────
# 4. Thread bütünlüğü — tam thread getir
# ─────────────────────────────────────────────

def get_full_thread(tweet_id: str) -> List[Dict[str, Any]]:
    """
    Bir tweet'in tüm thread kardeşlerini sıralı döndür.
    thread_position'a göre sıralı.
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            # Önce thread_tweet_ids'i bul
            cur.execute(
                "SELECT thread_tweet_ids FROM tweets WHERE tweet_id = %s",
                (tweet_id,),
            )
            row = cur.fetchone()
            if not row or not row["thread_tweet_ids"]:
                # Tek tweet
                cur.execute(
                    "SELECT * FROM v_tweets_labeled WHERE tweet_id = %s",
                    (tweet_id,),
                )
                return _rows_to_list(cur)

            all_ids = row["thread_tweet_ids"]
            cur.execute(
                """
                SELECT * FROM v_tweets_labeled
                WHERE tweet_id = ANY(%s)
                ORDER BY thread_position ASC
                """,
                (all_ids,),
            )
            return _rows_to_list(cur)
    finally:
        conn.close()


# ─────────────────────────────────────────────
# 5. Algoritma sinyal dağılımı
# ─────────────────────────────────────────────

def signal_distribution(
    signal: Optional[str] = None,  # None → tüm sinyallerin dağılımı
    quality_tier: Optional[List[str]] = None,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    """
    signal=None  → her sinyal için tweet sayısı ve ort engagement
    signal="bookmark_odaklı" → bu sinyale sahip top_n tweet
    """
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            if signal is None:
                # Genel dağılım
                cur.execute(
                    """
                    SELECT
                        unnest(tl.algoritma_sinyal) AS sinyal,
                        COUNT(*) AS tweet_count,
                        ROUND(AVG(t.engagement_rate)::numeric, 4) AS avg_engagement,
                        ROUND(AVG(tl.quality_score)::numeric, 2) AS avg_quality
                    FROM tweet_labels tl
                    JOIN tweets t ON t.tweet_id = tl.tweet_id
                    GROUP BY sinyal
                    ORDER BY tweet_count DESC
                    LIMIT %s
                    """,
                    (top_n,),
                )
            else:
                tier_filter = ""
                params: List[Any] = [signal, top_n]
                if quality_tier:
                    tier_filter = "AND tl.quality_tier = ANY(%s)"
                    params.insert(1, quality_tier)
                cur.execute(
                    f"""
                    SELECT
                        t.tweet_id, t.text, t.username,
                        t.engagement_rate, t.priority_score,
                        tl.quality_score, tl.quality_tier,
                        tl.icerik_formu, tl.ton,
                        tl.algoritma_sinyal
                    FROM tweet_labels tl
                    JOIN tweets t ON t.tweet_id = tl.tweet_id
                    WHERE %s = ANY(tl.algoritma_sinyal)
                    {tier_filter}
                    ORDER BY t.priority_score DESC NULLS LAST
                    LIMIT %s
                    """,
                    params,
                )
            return _rows_to_list(cur)
    finally:
        conn.close()


# ─────────────────────────────────────────────
# 6. DB istatistikleri
# ─────────────────────────────────────────────

def db_stats() -> Dict[str, Any]:
    """Genel DB durumu — monitoring için."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            stats: Dict[str, Any] = {}

            cur.execute("SELECT COUNT(*) AS n FROM tweets")
            stats["total_tweets"] = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM tweets WHERE lab_processed = FALSE")
            stats["pending_lab"] = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM tweets WHERE embedding IS NOT NULL")
            stats["embedded"] = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM tweet_labels")
            stats["labeled"] = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM miner_sessions")
            stats["sessions"] = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM arxiv_papers")
            stats["papers"] = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM tweets WHERE thread_complete = FALSE AND is_thread = TRUE")
            stats["incomplete_threads"] = cur.fetchone()["n"]

            cur.execute(
                """
                SELECT quality_tier, COUNT(*) AS n
                FROM tweet_labels
                GROUP BY quality_tier
                ORDER BY quality_tier
                """
            )
            stats["quality_distribution"] = {r["quality_tier"]: r["n"] for r in cur.fetchall()}

            cur.execute(
                """
                SELECT language, COUNT(*) AS n
                FROM tweets
                GROUP BY language
                ORDER BY n DESC
                """
            )
            stats["language_distribution"] = {r["language"]: r["n"] for r in cur.fetchall()}

            return stats
    finally:
        conn.close()
