#!/usr/bin/env python3
"""
mirror_sync.py — The Mirror Auto-Sync Bileşeni
=====================================================
Bu script, kullanıcının X (Twitter) hesabındaki tweetleri periyodik olarak çeker,
kategorize eder ve style_memory.json dosyasına kaydeder.

Kullanım:
    python mirror_sync.py                    # Normal sync
    python mirror_sync.py --dry-run          # Gerçek kayıt yapmadan test
    python mirror_sync.py --since 2025-01-01 # Belirli tarihten itibaren sync
    python mirror_sync.py --dry-run --since 2025-06-01

Bağımlılıklar:
    pip install requests python-dotenv
"""

import argparse
import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Logging yapılandırması
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("mirror_sync")

# ---------------------------------------------------------------------------
# Sabitler ve yollar
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.resolve()
STYLE_MEMORY_PATH = SCRIPT_DIR / "style_memory.json"

# .env dosyaları: proje kökü + skill dizini (her ikisi yüklenir, skill override eder)
_root_env = SCRIPT_DIR.parent.parent / ".env"
_skill_env = SCRIPT_DIR / ".env"
ENV_PATH = _skill_env  # logging için gösterilir

TWITTER_API_BASE = "https://api.twitter.com/2"
TWEETS_PER_PAGE = 100        # Twitter API v2 max: 100
MAX_INITIAL_PAGES = 2        # İlk sync: 200 tweet
HIGH_PERFORMER_MULTIPLIER = 1.5

# style_memory.json için başlangıç şeması
DEFAULT_STYLE_MEMORY = {
    "userId": "",
    "handle": "",
    "last_synced_at": None,
    "last_sync_count": 0,
    "version": 0,
    "tweet_archive": [],
    "high_performers": [],
    "performance_snapshot": {
        "total_impressions": 0,
        "total_engagements": 0,
        "avg_engagement_rate": 0.0,
        "verified_follower_ratio": None,
        "top_signal_breakdown": {
            "likes": 0,
            "replies": 0,
            "retweets": 0,
            "bookmarks": 0,
            "shares": 0,
            "quote_tweets": 0,
        },
        "bookmark_to_like_ratio": None,
        "retweet_to_like_ratio": None,
        "reply_to_impression_ratio": None,
    },
    "hook_patterns": {},
    "tone_profile": {},
    "signature_expressions": {},
    "evolution_log": [],
}

# @ciftcibahadir ilk kez çalışmada kullanılacak seed değerleri
CIFTCIBAHADIR_SEED = {
    "handle": "@ciftcibahadir",
    "tweet_count_at_seed": 48,
    "performance_snapshot": {
        "total_impressions": 254800,
        "total_engagements": 5900,
        "avg_engagement_rate": 0.0232,
        "verified_follower_ratio": 0.35,
    },
}


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def load_env() -> dict:
    """
    .env dosyasından API yapılandırmasını yükler.
    Proje kökü .env + skill .env ikisi birden yüklenir.
    USER_ID yoksa X_ACCESS_TOKEN'dan türetir.
    """
    # Kök .env önce yüklenir (X_BEARER_TOKEN, X_ACCESS_TOKEN vb.)
    if _root_env.exists():
        load_dotenv(dotenv_path=_root_env, override=False)
    # Skill .env sonra yüklenir (USERNAME, USER_ID vb. — override etmez)
    if _skill_env.exists():
        load_dotenv(dotenv_path=_skill_env, override=False)

    bearer = os.getenv("X_BEARER_TOKEN")
    if not bearer:
        logger.error("X_BEARER_TOKEN eksik. .env dosyasını kontrol et: %s", ENV_PATH)
        sys.exit(1)

    # USER_ID: ya açıkça .env'de, ya da X_ACCESS_TOKEN'ın başından türetilir
    user_id = os.getenv("USER_ID")
    if not user_id:
        access_token = os.getenv("X_ACCESS_TOKEN", "")
        user_id = access_token.split("-")[0] if "-" in access_token else ""
    if not user_id:
        logger.error(
            "USER_ID belirlenemiyor. .env'e USER_ID=<twitter_user_id> ekle "
            "veya X_ACCESS_TOKEN'ın başı user_id-... formatında olsun."
        )
        sys.exit(1)

    username = os.getenv("USERNAME") or os.getenv("X_USERNAME") or "unknown"

    return {
        "X_BEARER_TOKEN": bearer,
        "USER_ID": user_id,
        "USERNAME": username,
    }


def load_style_memory() -> dict:
    """
    style_memory.json dosyasını yükler.
    Dosya yoksa varsayılan şemayla yeni bir dosya oluşturur.
    """
    import copy

    if not STYLE_MEMORY_PATH.exists():
        logger.info("style_memory.json bulunamadı. Yeni dosya oluşturuluyor: %s", STYLE_MEMORY_PATH)
        data = copy.deepcopy(DEFAULT_STYLE_MEMORY)

        # İlk çalıştırmada @ciftcibahadir seed değerlerini uygula
        if data.get("last_synced_at") is None and not data.get("tweet_archive"):
            data["handle"] = CIFTCIBAHADIR_SEED["handle"]
            seed_perf = CIFTCIBAHADIR_SEED["performance_snapshot"]
            data["performance_snapshot"]["total_impressions"] = seed_perf["total_impressions"]
            data["performance_snapshot"]["total_engagements"] = seed_perf["total_engagements"]
            data["performance_snapshot"]["avg_engagement_rate"] = seed_perf["avg_engagement_rate"]
            data["performance_snapshot"]["verified_follower_ratio"] = seed_perf["verified_follower_ratio"]
            logger.info("@ciftcibahadir seed değerleri uygulandı.")

        save_style_memory(data)
        return data

    with open(STYLE_MEMORY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        logger.info("style_memory.json yüklendi. Versiyon: %s", data.get("version", 0))
        return data


def save_style_memory(data: dict) -> None:
    """style_memory.json dosyasına veriyi UTF-8 formatında atomik olarak yazar."""
    abs_path = os.path.abspath(str(STYLE_MEMORY_PATH))
    target_dir = os.path.dirname(abs_path)
    fd, tmp_path = tempfile.mkstemp(dir=target_dir, suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, abs_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    logger.debug("style_memory.json kaydedildi (atomik).")


# ---------------------------------------------------------------------------
# Twitter API v2 — Tweet çekme
# ---------------------------------------------------------------------------

def fetch_tweets_since(bearer_token: str, user_id: str, cutoff: datetime | None) -> list[dict]:
    """
    Twitter API v2 kullanarak kullanıcının timeline'ını çeker.

    cutoff verilmişse start_time parametresi ile API'ye iletilir (server-side filtre).
    cutoff None ise (ilk sync) MAX_INITIAL_PAGES sayfa çekilir (200 tweet).

    Rate limit (429) ile karşılaşıldığında x-rate-limit-reset başlığını bekler.
    """
    headers = {"Authorization": f"Bearer {bearer_token}"}
    params = {
        "max_results": TWEETS_PER_PAGE,
        "tweet.fields": "public_metrics,created_at,text,referenced_tweets,in_reply_to_user_id,attachments",
        "exclude": "retweets",  # Retweet'ler analize dahil edilmez
    }

    if cutoff:
        # API start_time'ı Z suffix ile bekler
        params["start_time"] = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
        logger.info("API start_time parametresi: %s", params["start_time"])

    collected: list[dict] = []
    next_token: str | None = None
    page_count = 0

    while True:
        if next_token:
            params["pagination_token"] = next_token

        resp = requests.get(
            f"{TWITTER_API_BASE}/users/{user_id}/tweets",
            headers=headers,
            params=params,
            timeout=30,
        )

        if resp.status_code == 429:
            reset_ts = int(resp.headers.get("x-rate-limit-reset", time.time() + 60))
            wait = max(5, reset_ts - int(time.time())) + 5
            logger.warning("Rate limit aşıldı. %d saniye bekleniyor...", wait)
            time.sleep(wait)
            continue

        if not resp.ok:
            logger.error("Twitter API hatası %d: %s", resp.status_code, resp.text)
            resp.raise_for_status()

        data = resp.json()
        tweets = data.get("data", [])
        if not tweets:
            logger.info("Sayfa %d boş döndü, dur.", page_count + 1)
            break

        collected.extend([_tweet_to_dict(t) for t in tweets])
        page_count += 1
        logger.info("Sayfa %d: %d tweet alındı (toplam: %d).", page_count, len(tweets), len(collected))

        # İlk sync'te sayfa sınırı
        if cutoff is None and page_count >= MAX_INITIAL_PAGES:
            logger.info("İlk sync sayfa sınırına ulaşıldı (%d sayfa).", MAX_INITIAL_PAGES)
            break

        next_token = data.get("meta", {}).get("next_token")
        if not next_token:
            break

    return collected


def _tweet_to_dict(tweet: dict) -> dict:
    """Twitter API v2 tweet nesnesini iç format dict'e dönüştürür."""
    metrics = tweet.get("public_metrics", {})

    # Reply tespiti: in_reply_to_user_id alanı veya referenced_tweets
    is_reply = bool(tweet.get("in_reply_to_user_id"))
    if not is_reply:
        refs = tweet.get("referenced_tweets") or []
        is_reply = any(r.get("type") == "replied_to" for r in refs)

    # Medya tespiti: attachments.media_keys alanı
    has_media = bool((tweet.get("attachments") or {}).get("media_keys"))

    created_at = tweet.get("created_at", "")

    return {
        "id": tweet["id"],
        "text": tweet.get("text", ""),
        "created_at": created_at,
        # view_count → Twitter API v2'de impression_count
        "view_count": metrics.get("impression_count", 0),
        "bookmark_count": metrics.get("bookmark_count", 0),
        "favorite_count": metrics.get("like_count", 0),
        "retweet_count": metrics.get("retweet_count", 0),
        "reply_count": metrics.get("reply_count", 0),
        "quote_count": metrics.get("quote_count", 0),
        "in_reply_to": is_reply,
        "has_media": has_media,
    }


# ---------------------------------------------------------------------------
# Kategorize etme fonksiyonları
# ---------------------------------------------------------------------------

def detect_hook_type(text: str) -> str:
    """
    Tweet metninin ilk cümlesine bakarak kanca tipini tespit eder.

    Kategoriler:
      soru           — Soru işareti ile başlayan veya soru içeren açılış
      cesur_iddia    — İddia/gerçek/kanıt ile başlayan keskin ifadeler
      rakam_ile_bas  — Rakamla başlayan tweet (örn: "5 yol...", "3 neden...")
      karsi_gorus    — "Yanlış", "aksine", "herkes söylüyor ama..." gibi kalıplar
      liste_vaadi    — "Liste", "maddeler", "adım" gibi içerikler
      hikaye         — "Bugün", "Geçen", "Bir gün" gibi anlatı başlangıçları
      diger          — Yukarıdaki kategorilere uymayan
    """
    first_sentence = text.split("\n")[0][:280]
    lower = first_sentence.lower().strip()

    if first_sentence and first_sentence[0].isdigit():
        return "rakam_ile_bas"

    soru_indicators = ["?", "nasıl", "neden", "ne zaman", "kim", "hangi", "nereye", "niçin", "kaç"]
    if any(ind in lower for ind in soru_indicators):
        return "soru"

    karsi_indicators = [
        "yanlış", "aksine", "aslında değil", "herkes söylüyor", "çoğu kişi",
        "sanılanın aksine", "beklenmedik", "hayır,", "hayır.",
    ]
    if any(ind in lower for ind in karsi_indicators):
        return "karsi_gorus"

    hikaye_indicators = [
        "bugün", "geçen", "bir gün", "geçenlerde", "dün", "bu sabah",
        "anlatayım", "paylaşayım", "story:",
    ]
    if any(ind in lower for ind in hikaye_indicators):
        return "hikaye"

    liste_indicators = [
        "liste", "maddeler", "adım", "şunları", "şu ", "bunları",
        "ipuçları", "yol ", "neden ", "sebep",
    ]
    if any(ind in lower for ind in liste_indicators):
        return "liste_vaadi"

    cesur_indicators = [
        "gerçek şu ki", "söylemem gereken", "önemli olan", "kritik", "şunu söylemeliyim",
        "kanıtlandı", "artık", "kesin", "en iyi", "en kötü",
    ]
    if any(ind in lower for ind in cesur_indicators):
        return "cesur_iddia"

    return "diger"


def detect_tone(text: str) -> str:
    """
    Tweet metnine bakarak baskın tonu tespit eder.

    Kategoriler:
      profesyonel  — Teknik, analitik, kurumsal dil
      samimi       — Kişisel, rahat, samimi anlatım
      egitici      — Öğretici, açıklayıcı, adım adım
      alaycı       — İroni, hiciv, eleştiri
      heyecanli    — Ünlem, büyük harf, coşku ifadeleri
    """
    lower = text.lower()

    alaycı_indicators = [
        ":)", ":D", "😄", "😂", "lol", "ironi", "tabii ki", "sanki",
        "güya", "sözde", "maşallah", "aferin", "bravo", "hadi be",
    ]
    if any(ind in lower for ind in alaycı_indicators):
        return "alaycı"

    if text.count("!") >= 2 or text.count("🔥") >= 1 or text.count("🚀") >= 1:
        return "heyecanli"

    egitici_indicators = [
        "nasıl", "adım", "öğrenin", "öğrendim", "açıklayayım", "kısaca",
        "ayrıntılı", "detay", "rehber", "guide", "tutorial", "how to",
        "tip:", "not:", "dikkat:",
    ]
    if any(ind in lower for ind in egitici_indicators):
        return "egitici"

    samimi_indicators = [
        "ben ", "benim", "düşünüyorum", "hissediyorum", "itiraf",
        "açıkçası", "dürüst olmak gerekirse", "kişisel", "deneyim",
    ]
    if any(ind in lower for ind in samimi_indicators):
        return "samimi"

    return "profesyonel"


def detect_format(tweet_data: dict, is_reply: bool) -> str:
    """
    Tweet formatını tespit eder.

    Kategoriler:
      thread_basi  — Konuşmanın ilk tweeti ve uzun içerik
      reply        — Başka bir tweete verilen yanıt
      tek_tweet    — Bağımsız, tek tweet
    """
    if is_reply:
        return "reply"

    text = tweet_data.get("text", "") if isinstance(tweet_data, dict) else str(tweet_data)

    if "1/" in text or "(1/" in text or text.strip().endswith("🧵"):
        return "thread_basi"

    return "tek_tweet"


def compute_engagement_rate(metrics: dict) -> float:
    """
    Engagement rate'i hesaplar.
    Formül: (likes + replies + retweets + bookmarks + quotes) / view_count (impressions)
    """
    impressions = int(metrics.get("view_count", 0) or 0)
    if impressions == 0:
        return 0.0

    likes = int(metrics.get("like_count", 0) or 0)
    replies = int(metrics.get("reply_count", 0) or 0)
    retweets = int(metrics.get("retweet_count", 0) or 0)
    bookmarks = int(metrics.get("bookmark_count", 0) or 0)
    quotes = int(metrics.get("quote_count", 0) or 0)

    total_engagements = likes + replies + retweets + bookmarks + quotes
    return round(total_engagements / impressions, 6)


def categorize_tweet(raw: dict) -> dict:
    """
    _tweet_to_dict() çıktısını alır ve yapılandırılmış style_memory girişi döner.
    """
    tweet_id = str(raw["id"])
    text = raw["text"] or ""
    created_at = raw["created_at"]

    metrics = {
        "view_count": raw["view_count"],        # impression_count'tan türetildi
        "like_count": raw["favorite_count"],
        "reply_count": raw["reply_count"],
        "retweet_count": raw["retweet_count"],
        "bookmark_count": raw["bookmark_count"],
        "quote_count": raw["quote_count"],
    }

    is_reply = raw["in_reply_to"]
    has_media = raw["has_media"]

    hook_type = detect_hook_type(text)
    tone = detect_tone(text)
    fmt = detect_format({"text": text}, is_reply)
    engagement_rate = compute_engagement_rate(metrics)

    return {
        "id": tweet_id,
        "text": text,
        "created_at": created_at,
        "hook_type": hook_type,
        "tone": tone,
        "format": fmt,
        "has_media": has_media,
        "is_reply": is_reply,
        "metrics": metrics,
        "engagement_rate": engagement_rate,
    }


# ---------------------------------------------------------------------------
# Yüksek performanslı tweet tespiti
# ---------------------------------------------------------------------------

def compute_avg_engagement_rate(tweet_archive: list[dict]) -> float:
    if not tweet_archive:
        return 0.0
    rates = [t.get("engagement_rate", 0.0) for t in tweet_archive]
    return sum(rates) / len(rates)


def identify_high_performers(
    tweet_archive: list[dict],
    threshold_multiplier: float = HIGH_PERFORMER_MULTIPLIER,
) -> list[dict]:
    if not tweet_archive:
        return []

    avg_rate = compute_avg_engagement_rate(tweet_archive)
    threshold = avg_rate * threshold_multiplier

    logger.info(
        "Yüksek performans eşiği: %.6f (Ort: %.6f × %.1f)",
        threshold, avg_rate, threshold_multiplier,
    )

    high_performers = [t for t in tweet_archive if t.get("engagement_rate", 0.0) >= threshold]
    high_performers.sort(key=lambda t: t["engagement_rate"], reverse=True)
    return high_performers


# ---------------------------------------------------------------------------
# Performans snapshot güncelleme
# ---------------------------------------------------------------------------

def update_performance_snapshot(style_memory: dict, tweet_archive: list[dict]) -> None:
    if not tweet_archive:
        return

    snapshot = style_memory.setdefault("performance_snapshot", {})

    total_likes = total_replies = total_retweets = total_bookmarks = 0
    total_quotes = total_impressions = total_engagements = 0

    for tweet in tweet_archive:
        m = tweet.get("metrics", {})
        likes = int(m.get("like_count", 0) or 0)
        replies = int(m.get("reply_count", 0) or 0)
        retweets = int(m.get("retweet_count", 0) or 0)
        bookmarks = int(m.get("bookmark_count", 0) or 0)
        quotes = int(m.get("quote_count", 0) or 0)
        impressions = int(m.get("view_count", 0) or 0)

        total_likes += likes
        total_replies += replies
        total_retweets += retweets
        total_bookmarks += bookmarks
        total_quotes += quotes
        total_impressions += impressions
        total_engagements += likes + replies + retweets + bookmarks + quotes

    snapshot["total_impressions"] = total_impressions
    snapshot["total_engagements"] = total_engagements
    snapshot["avg_engagement_rate"] = (
        round(total_engagements / total_impressions, 6) if total_impressions > 0 else 0.0
    )

    tsd = snapshot.setdefault("top_signal_breakdown", {})
    tsd["likes"] = total_likes
    tsd["replies"] = total_replies
    tsd["retweets"] = total_retweets
    tsd["bookmarks"] = total_bookmarks
    tsd["quotes"] = total_quotes

    snapshot["bookmark_to_like_ratio"] = (
        round(total_bookmarks / total_likes, 4) if total_likes > 0 else None
    )
    snapshot["retweet_to_like_ratio"] = (
        round(total_retweets / total_likes, 4) if total_likes > 0 else None
    )
    snapshot["reply_to_impression_ratio"] = (
        round(total_replies / total_impressions, 6) if total_impressions > 0 else None
    )


# ---------------------------------------------------------------------------
# Profil agregasyonu — hook/tone performansı + imza ifadeler
# ---------------------------------------------------------------------------

def compute_profile_aggregations(style_memory: dict, tweet_archive: list[dict]) -> None:
    """
    tweet_archive üzerinden hook_patterns, tone_profile ve signature_expressions
    alanlarını hesaplayarak style_memory'ye yazar.
    """
    if not tweet_archive:
        return

    # --- hook_patterns ---
    hook_buckets: dict[str, list[float]] = {}
    for tweet in tweet_archive:
        h = tweet.get("hook_type", "diger")
        hook_buckets.setdefault(h, []).append(tweet.get("engagement_rate", 0.0))

    hook_perf = {
        htype: {
            "avg_engagement_rate": round(sum(rates) / len(rates), 6),
            "sample_count": len(rates),
        }
        for htype, rates in hook_buckets.items()
    }
    best_hook = max(hook_perf, key=lambda k: hook_perf[k]["avg_engagement_rate"], default=None)
    style_memory["hook_patterns"] = {"hook_type_performance": hook_perf, "best_hook_type": best_hook}

    # --- tone_profile ---
    tone_buckets: dict[str, list[float]] = {}
    for tweet in tweet_archive:
        t = tweet.get("tone", "profesyonel")
        tone_buckets.setdefault(t, []).append(tweet.get("engagement_rate", 0.0))

    tone_counts = {t: len(r) for t, r in tone_buckets.items()}
    total_tweets = sum(tone_counts.values()) or 1

    tone_perf = {
        tone: {
            "avg_engagement_rate": round(sum(rates) / len(rates), 6),
            "distribution": round(tone_counts[tone] / total_tweets, 4),
            "sample_count": len(rates),
        }
        for tone, rates in tone_buckets.items()
    }
    dominant_tone = max(tone_counts, key=tone_counts.get, default=None)
    best_tone = max(tone_perf, key=lambda k: tone_perf[k]["avg_engagement_rate"], default=None)
    style_memory["tone_profile"] = {
        "tone_performance": tone_perf,
        "dominant_tone": dominant_tone,
        "highest_performing_tone": best_tone,
    }

    # --- signature_expressions ---
    high_performers = style_memory.get("high_performers", [])
    if len(high_performers) >= 2:
        from collections import Counter
        import re

        word_tweets: dict[str, int] = Counter()
        word_eng: dict[str, list[float]] = {}
        stopwords = {
            "bir", "bu", "ve", "de", "da", "ile", "için", "mi", "mu", "mı", "mü",
            "ben", "sen", "o", "biz", "siz", "onlar", "var", "yok", "gibi", "daha",
            "çok", "en", "ama", "ya", "ne", "nasıl", "ki", "bile", "kadar", "sonra",
            "the", "a", "an", "is", "are", "was", "in", "on", "at", "to", "of",
            "https", "co", "t", "s", "i", "rt",
        }

        for tweet in high_performers:
            text = tweet.get("text", "")
            words = re.findall(r"\b[a-zA-ZğüşıöçĞÜŞİÖÇ]{3,}\b", text.lower())
            unique_words = set(words) - stopwords
            eng = tweet.get("engagement_rate", 0.0)
            for w in unique_words:
                word_tweets[w] += 1
                word_eng.setdefault(w, []).append(eng)

        sig_terms = [
            {
                "term": w,
                "frequency": cnt,
                "avg_engagement_when_used": round(sum(word_eng[w]) / len(word_eng[w]), 6),
            }
            for w, cnt in word_tweets.items()
            if cnt >= 2
        ]
        sig_terms.sort(key=lambda x: x["avg_engagement_when_used"], reverse=True)
        style_memory["signature_expressions"] = {"terms": sig_terms[:15]}
    else:
        style_memory["signature_expressions"] = {"terms": []}


# ---------------------------------------------------------------------------
# Evolution log
# ---------------------------------------------------------------------------

def append_evolution_log(style_memory: dict, trigger: str, summary: str) -> None:
    style_memory["version"] = style_memory.get("version", 0) + 1
    entry = {
        "date": datetime.now(timezone.utc).isoformat(),
        "trigger": trigger,
        "change_summary": summary,
        "version": style_memory["version"],
    }
    style_memory.setdefault("evolution_log", []).append(entry)
    logger.debug("Evolution log güncellendi. Versiyon: %d", style_memory["version"])


# ---------------------------------------------------------------------------
# Ana sync akışı
# ---------------------------------------------------------------------------

def run_sync(dry_run: bool = False, since: str | None = None) -> None:
    """
    Ana sync fonksiyonu. Twitter API v2 ile tweetleri çeker ve style_memory'yi günceller.
    """
    logger.info("=" * 60)
    logger.info("The Mirror — Auto-Sync Başlatılıyor")
    if dry_run:
        logger.info("*** DRY-RUN MODU: Hiçbir değişiklik kaydedilmeyecek ***")
    logger.info("=" * 60)

    # Adım 1: Config yükle
    config = load_env()
    user_id = config["USER_ID"]
    username = config["USERNAME"]
    bearer_token = config["X_BEARER_TOKEN"]

    # Adım 2: style_memory oku
    style_memory = load_style_memory()

    if not style_memory.get("userId"):
        style_memory["userId"] = user_id
    if not style_memory.get("handle"):
        style_memory["handle"] = f"@{username.lstrip('@')}"

    # Adım 3: Cutoff belirle
    if since:
        try:
            cutoff = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
            logger.info("--since parametresi kullanılıyor: %s", cutoff.isoformat())
        except ValueError:
            logger.error(
                "Geçersiz tarih formatı: '%s'. ISO-8601 formatı kullan (örn: 2025-01-01)", since
            )
            sys.exit(1)
    elif style_memory.get("last_synced_at"):
        cutoff = datetime.fromisoformat(style_memory["last_synced_at"]).replace(tzinfo=timezone.utc)
        logger.info("Son sync zamanından devam ediliyor: %s", cutoff.isoformat())
    else:
        cutoff = None
        logger.info("İlk sync — cutoff yok, ilk %d tweet çekilecek.", TWEETS_PER_PAGE * MAX_INITIAL_PAGES)

    # Adım 4: Tweetleri çek (Twitter API v2)
    raw_tweets = fetch_tweets_since(bearer_token, user_id, cutoff)

    if not raw_tweets:
        logger.info("Yeni tweet bulunamadı. Profil agregasyonu mevcut arşivle güncelleniyor.")
        tweet_archive = style_memory.get("tweet_archive", [])
        update_performance_snapshot(style_memory, tweet_archive)
        compute_profile_aggregations(style_memory, tweet_archive)
        if not dry_run:
            save_style_memory(style_memory)
        _print_sync_report(
            username=username,
            new_count=0,
            total_archive=len(tweet_archive),
            high_performer_count=len(style_memory.get("high_performers", [])),
            avg_engagement=compute_avg_engagement_rate(tweet_archive),
            dry_run=dry_run,
        )
        return

    # Adım 5: Kategorize et
    logger.info("%d yeni tweet kategorize ediliyor...", len(raw_tweets))
    categorized_tweets = [categorize_tweet(t) for t in raw_tweets]

    # Adım 6: Arşive ekle (deduplicate)
    tweet_archive = style_memory.setdefault("tweet_archive", [])
    existing_ids = {t["id"] for t in tweet_archive}
    prev_hp_count = len(style_memory.get("high_performers", []))

    new_tweets = [t for t in categorized_tweets if t["id"] not in existing_ids]
    logger.info(
        "%d yeni tweet arşive eklenecek (%d zaten mevcut).",
        len(new_tweets),
        len(categorized_tweets) - len(new_tweets),
    )

    tweet_archive.extend(new_tweets)
    tweet_archive.sort(key=lambda t: t.get("created_at", ""), reverse=True)

    # Adım 7: Rolling window (max 1000)
    MAX_ARCHIVE_SIZE = 1000
    if len(tweet_archive) > MAX_ARCHIVE_SIZE:
        tweet_archive = tweet_archive[:MAX_ARCHIVE_SIZE]
        style_memory["tweet_archive"] = tweet_archive
        logger.info("Tweet arşivi %d'e kırpıldı (rolling window).", MAX_ARCHIVE_SIZE)

    # Adım 8: Yüksek performanslıları belirle
    high_performers = identify_high_performers(tweet_archive)
    new_high_performers = [
        hp for hp in high_performers
        if hp["id"] not in {t["id"] for t in style_memory.get("high_performers", [])}
    ]
    style_memory["high_performers"] = high_performers
    logger.info("%d yüksek performanslı tweet tespit edildi.", len(high_performers))

    # Adım 9: Snapshot ve profil güncelle
    update_performance_snapshot(style_memory, tweet_archive)
    compute_profile_aggregations(style_memory, tweet_archive)

    style_memory["last_synced_at"] = datetime.now(timezone.utc).isoformat()
    style_memory["last_sync_count"] = len(new_tweets)

    # Adım 10: Evolution log
    if not dry_run and new_tweets:
        hp_delta = len(new_high_performers) - prev_hp_count
        append_evolution_log(
            style_memory,
            trigger="sync" if not since else "--since override",
            summary=f"Added {len(new_tweets)} tweets. High_performers delta: {hp_delta:+d}.",
        )

    # Adım 11: Kaydet
    if not dry_run:
        save_style_memory(style_memory)
        logger.info("style_memory.json güncellendi.")
    else:
        logger.info("[DRY-RUN] style_memory.json DEĞİŞTİRİLMEDİ.")

    avg_engagement = compute_avg_engagement_rate(tweet_archive)
    _print_sync_report(
        username=username,
        new_count=len(new_tweets),
        total_archive=len(tweet_archive),
        high_performer_count=len(high_performers),
        avg_engagement=avg_engagement,
        dry_run=dry_run,
        sample_tweets=new_tweets[:3],
    )


def _print_sync_report(
    username: str,
    new_count: int,
    total_archive: int,
    high_performer_count: int,
    avg_engagement: float,
    dry_run: bool,
    sample_tweets: list[dict] | None = None,
) -> None:
    separator = "-" * 60
    print(f"\n{separator}")
    print("  THE MIRROR — SYNC RAPORU")
    print(separator)
    print(f"  Kullanıcı      : @{username.lstrip('@')}")
    print(f"  Tarih/Saat     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Mod            : {'DRY-RUN (kayıt yok)' if dry_run else 'Normal'}")
    print(separator)
    print(f"  Yeni tweet     : {new_count}")
    print(f"  Toplam arşiv   : {total_archive}")
    print(f"  Yüksek perf.   : {high_performer_count}")
    print(f"  Ort. eng. rate : {avg_engagement:.4%}")
    print(separator)

    if sample_tweets:
        print("  SON EKLENENLERden ÖRNEKLER:")
        for i, t in enumerate(sample_tweets, 1):
            preview = t["text"][:80].replace("\n", " ")
            print(f"  [{i}] {preview}...")
            print(
                f"      hook={t['hook_type']} | tone={t['tone']} | "
                f"format={t['format']} | eng={t['engagement_rate']:.4%}"
            )
        print(separator)

    if dry_run:
        print("  DRY-RUN: style_memory.json KAYDEDILMEDI.")
    else:
        print(f"  style_memory.json güncellendi: {STYLE_MEMORY_PATH}")
    print(f"{separator}\n")


# ---------------------------------------------------------------------------
# CLI giriş noktası
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="The Mirror — X (Twitter) tweet sync bileşeni (Twitter API v2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python mirror_sync.py                        Normal sync
  python mirror_sync.py --dry-run              Test modu (kayıt yok)
  python mirror_sync.py --since 2025-01-01     Belirli tarihten itibaren
  python mirror_sync.py --dry-run --since 2025-06-01
        """,
    )
    parser.add_argument("--dry-run", action="store_true", help="Gerçek kayıt yapmadan işlemi test eder.")
    parser.add_argument(
        "--since", type=str, default=None, metavar="YYYY-MM-DD",
        help="Bu tarihten itibaren tweetleri çeker. Format: YYYY-MM-DD",
    )
    parser.add_argument("--verbose", action="store_true", help="DEBUG log çıktısı.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("DEBUG modu etkin.")

    try:
        run_sync(dry_run=args.dry_run, since=args.since)
    except KeyboardInterrupt:
        logger.info("Kullanıcı tarafından iptal edildi.")
        sys.exit(0)
    except Exception as e:
        logger.exception("Beklenmeyen hata: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
