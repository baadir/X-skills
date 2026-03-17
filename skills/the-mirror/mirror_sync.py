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
    pip install twikit python-dotenv
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from twikit import Client, TooManyRequests
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
ENV_PATH = SCRIPT_DIR / ".env"
COOKIES_FILE = SCRIPT_DIR / "cookies.json"

# Rate limit / pagination ayarları
BACKOFF_MAX_RETRIES = 5     # Maksimum yeniden deneme sayısı
HIGH_PERFORMER_MULTIPLIER = 1.5

# twikit'ten tek seferde çekilecek tweet sayısı
TWEETS_PER_PAGE = 40

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
# MEM-04: Applied ONLY when style_memory.json does not yet exist (first-run)
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

# Module-level twikit client (en-US locale)
client = Client("en-US")


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def load_env() -> dict:
    """
    .env dosyasından API yapılandırmasını yükler.
    Eksik değişken varsa hata verir.
    """
    load_dotenv(dotenv_path=ENV_PATH)

    required_vars = [
        "USERNAME",
        "EMAIL",
        "PASSWORD",
        "USER_ID",
    ]

    config = {}
    missing = []

    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
        else:
            config[var] = value

    if missing:
        logger.error(
            "Aşağıdaki ortam değişkenleri eksik: %s\n"
            ".env dosyasını kontrol et: %s",
            ", ".join(missing),
            ENV_PATH,
        )
        sys.exit(1)

    return config


def load_style_memory() -> dict:
    """
    style_memory.json dosyasını yükler.
    Dosya yoksa varsayılan şemayla yeni bir dosya oluşturur.
    İlk çalışmada (@ciftcibahadir için) seed değerleri uygulanır.
    """
    import copy

    if not STYLE_MEMORY_PATH.exists():
        logger.info(
            "style_memory.json bulunamadı. Yeni dosya oluşturuluyor: %s",
            STYLE_MEMORY_PATH,
        )
        data = copy.deepcopy(DEFAULT_STYLE_MEMORY)

        # MEM-04: Apply @ciftcibahadir seed values on first run
        # (last_synced_at is None and tweet_archive is empty)
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
    """style_memory.json dosyasına veriyi UTF-8 formatında atomik olarak yazar.

    Atomik yazma deseni (Windows uyumlu — same-dir temp + os.replace):
    Geçici dosya hedef dizinde oluşturulur, böylece os.replace aynı sürücü
    içinde rename olarak çalışır ve crash-safe olur.
    """
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
# twikit Auth — cookie-persistent, falls back to login
# ---------------------------------------------------------------------------

async def get_authenticated_client(
    cookies_file: str,
    username: str,
    email: str,
    password: str,
) -> Client:
    """Load cookies if available; fall back to login with enable_ui_metrics=True."""
    if Path(cookies_file).exists():
        try:
            client.load_cookies(cookies_file)
            await client.user_id()   # Lightweight validation call
            return client
        except Exception:
            pass  # Stale cookies — fall through to login
    await client.login(
        auth_info_1=username,
        auth_info_2=email,
        password=password,
        cookies_file=cookies_file,
        enable_ui_metrics=True,
    )
    return client


# ---------------------------------------------------------------------------
# Rate-limit-aware pagination helper
# ---------------------------------------------------------------------------

async def safe_next(result) -> object:
    """Call result.next() with exponential backoff on TooManyRequests.

    Retries up to BACKOFF_MAX_RETRIES times. Raises RuntimeError when all
    attempts are exhausted.
    """
    for attempt in range(BACKOFF_MAX_RETRIES):
        try:
            return await result.next()
        except TooManyRequests as e:
            reset_at = getattr(e, "rate_limit_reset", None)
            wait = (
                max(0, reset_at - int(time.time())) + 5
                if reset_at
                else 60 * (2 ** attempt)
            )
            logger.warning(
                "Rate limit aşıldı. Bekleniyor: %d saniye (Deneme %d/%d)...",
                wait,
                attempt + 1,
                BACKOFF_MAX_RETRIES,
            )
            await asyncio.sleep(wait)
    raise RuntimeError("Max rate limit retries exceeded")


# ---------------------------------------------------------------------------
# Tweet çekme — Incremental pagination with client-side cutoff
# ---------------------------------------------------------------------------

async def fetch_tweets_since(
    client: Client,
    user_id: str,
    cutoff: datetime | None,
) -> list[dict]:
    """Fetch tweets newer than cutoff using twikit pagination.

    When cutoff is None (first run), collect up to 200 tweets (5 pages of 40)
    without date filtering to limit initial fetch scope.

    Each twikit Tweet is immediately converted to a plain dict.
    """
    MAX_INITIAL_PAGES = 5

    tweets = await client.get_user_tweets(user_id, "Tweets", count=TWEETS_PER_PAGE)
    collected: list[dict] = []
    page_count = 0

    while tweets:
        page_count += 1
        stop = False

        for tweet in tweets:
            if cutoff is not None and tweet.created_at_datetime < cutoff:
                stop = True
                break
            collected.append(_tweet_to_dict(tweet))

        if stop:
            break

        # First-run page cap
        if cutoff is None and page_count >= MAX_INITIAL_PAGES:
            break

        try:
            tweets = await safe_next(tweets)
        except Exception:
            break

    return collected


def _tweet_to_dict(tweet) -> dict:
    """Convert a twikit Tweet object to a plain dict with all required fields."""
    return {
        "id": tweet.id,
        "text": tweet.text,
        "created_at": tweet.created_at,
        "created_at_datetime": tweet.created_at_datetime,
        "view_count": tweet.view_count or 0,
        "bookmark_count": tweet.bookmark_count or 0,
        "favorite_count": tweet.favorite_count or 0,
        "retweet_count": tweet.retweet_count or 0,
        "reply_count": tweet.reply_count or 0,
        "quote_count": tweet.quote_count or 0,
        "in_reply_to": tweet.in_reply_to is not None,
        "has_media": bool(tweet.media),
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
      liste_vaadi    — "Liste", "maddeler", "şunları..." gibi içerikler
      hikaye         — "Bugün", "Geçen", "Bir gün" gibi anlatı başlangıçları
      diger          — Yukarıdaki kategorilere uymayan
    """
    # Sadece ilk cümleyi al (nokta, ünlem, soru işaretine göre kes)
    first_sentence = text.split("\n")[0][:280]
    lower = first_sentence.lower().strip()

    # Rakamla başlama (Türkçe ve İngilizce sayılar)
    if first_sentence and (first_sentence[0].isdigit()):
        return "rakam_ile_bas"

    # Soru kalıpları
    soru_indicators = ["?", "nasıl", "neden", "ne zaman", "kim", "hangi", "nereye", "niçin", "kaç"]
    if any(ind in lower for ind in soru_indicators):
        return "soru"

    # Karşı görüş kalıpları
    karsi_indicators = [
        "yanlış", "aksine", "aslında değil", "herkes söylüyor", "çoğu kişi",
        "sanılanın aksine", "beklenmedik", "hayır,", "hayır.",
    ]
    if any(ind in lower for ind in karsi_indicators):
        return "karsi_gorus"

    # Hikaye kalıpları (liste_vaadi'den önce kontrol edilmeli —
    # "adım" listesi "yaşadım" gibi fiillerde yanlış eşleşme yapabilir)
    hikaye_indicators = [
        "bugün", "geçen", "bir gün", "geçenlerde", "dün", "bu sabah",
        "anlatayım", "paylaşayım", "story:",
    ]
    if any(ind in lower for ind in hikaye_indicators):
        return "hikaye"

    # Liste vaadi kalıpları
    liste_indicators = [
        "liste", "maddeler", "adım", "şunları", "şu ", "bunları",
        "ipuçları", "yol ", "neden ", "sebep",
    ]
    if any(ind in lower for ind in liste_indicators):
        return "liste_vaadi"

    # Cesur iddia kalıpları
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

    # Alaycı / eleştirel kalıplar
    alaycı_indicators = [
        ":)", ":D", "😄", "😂", "lol", "ironi", "tabii ki", "sanki",
        "güya", "sözde", "maşallah", "aferin", "bravo", "hadi be",
    ]
    if any(ind in lower for ind in alaycı_indicators):
        return "alaycı"

    # Heyecanlı kalıplar
    if text.count("!") >= 2 or text.count("🔥") >= 1 or text.count("🚀") >= 1:
        return "heyecanli"

    # Eğitici kalıplar
    egitici_indicators = [
        "nasıl", "adım", "öğrenin", "öğrendim", "açıklayayım", "kısaca",
        "ayrıntılı", "detay", "rehber", "guide", "tutorial", "how to",
        "tip:", "not:", "dikkat:",
    ]
    if any(ind in lower for ind in egitici_indicators):
        return "egitici"

    # Samimi kalıplar
    samimi_indicators = [
        "ben ", "benim", "düşünüyorum", "hissediyorum", "itiraf",
        "açıkçası", "dürüst olmak gerekirse", "kişisel", "deneyim",
    ]
    if any(ind in lower for ind in samimi_indicators):
        return "samimi"

    # Varsayılan: profesyonel
    return "profesyonel"


def detect_format(tweet_data: dict, is_reply: bool) -> str:
    """
    Tweet formatını tespit eder.

    Kategoriler:
      thread_basi  — Konuşmanın ilk tweeti ve uzun içerik (thread başlangıcı)
      reply        — Başka bir tweete verilen yanıt
      tek_tweet    — Bağımsız, tek tweet
    """
    if is_reply:
        return "reply"

    # Tweepy nesnesi veya dict olabilir
    text = tweet_data.get("text", "") if isinstance(tweet_data, dict) else str(tweet_data)

    # Thread işareti: "1/" veya "(1/n)" kalıpları
    if "1/" in text or "(1/" in text or text.strip().endswith("🧵"):
        return "thread_basi"

    return "tek_tweet"


def compute_engagement_rate(metrics: dict) -> float:
    """
    Engagement rate'i hesaplar.
    Formül: (likes + replies + retweets + bookmarks + quotes) / view_count

    # twikit: view_count replaces impression_count
    view_count 0 ise 0.0 döner.
    """
    # twikit: view_count replaces impression_count
    impressions = metrics.get("view_count", 0) or 0
    if impressions == 0:
        return 0.0

    likes = metrics.get("like_count", 0) or 0
    replies = metrics.get("reply_count", 0) or 0
    retweets = metrics.get("retweet_count", 0) or 0
    bookmarks = metrics.get("bookmark_count", 0) or 0
    quotes = metrics.get("quote_count", 0) or 0

    total_engagements = likes + replies + retweets + bookmarks + quotes
    return round(total_engagements / impressions, 6)


def categorize_tweet(raw: dict) -> dict:
    """
    twikit _tweet_to_dict() tarafından üretilen ham dict'i alır ve
    yapılandırılmış bir dict döner.

    raw dict shape (fetch_tweets_since / _tweet_to_dict çıktısı):
        id, text, created_at, created_at_datetime,
        view_count, bookmark_count, favorite_count,
        retweet_count, reply_count, quote_count,
        in_reply_to (bool), has_media (bool)

    Returns:
        {
            "id": str,
            "text": str,
            "created_at": str (ISO-8601),
            "hook_type": str,
            "tone": str,
            "format": str,
            "has_media": bool,
            "is_reply": bool,
            "metrics": dict,
            "engagement_rate": float,
        }
    """
    # Dict key access — no tweepy attribute access
    tweet_id = str(raw["id"])
    text = raw["text"] or ""
    created_at = raw["created_at"]  # already an ISO-8601 string from _tweet_to_dict

    # Metrikler — twikit field names
    metrics = {
        "view_count": raw["view_count"],          # twikit: view_count replaces impression_count
        "like_count": raw["favorite_count"],
        "reply_count": raw["reply_count"],
        "retweet_count": raw["retweet_count"],
        "bookmark_count": raw["bookmark_count"],
        "quote_count": raw["quote_count"],
    }

    # Reply ve medya kontrolü — already booleans from _tweet_to_dict
    is_reply = raw["in_reply_to"]
    has_media = raw["has_media"]

    # Kategorize
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
    """
    Tüm tweet arşivinin ortalama engagement rate'ini hesaplar.
    """
    if not tweet_archive:
        return 0.0

    rates = [t.get("engagement_rate", 0.0) for t in tweet_archive]
    return sum(rates) / len(rates)


def identify_high_performers(
    tweet_archive: list[dict],
    threshold_multiplier: float = HIGH_PERFORMER_MULTIPLIER,
) -> list[dict]:
    """
    Tweet arşivinden yüksek performanslı tweetleri belirler.
    Threshold: ortalama engagement rate * threshold_multiplier

    Returns:
        Yüksek performanslı tweet listesi (engagement_rate'e göre azalan sırada)
    """
    if not tweet_archive:
        return []

    avg_rate = compute_avg_engagement_rate(tweet_archive)
    threshold = avg_rate * threshold_multiplier

    logger.info(
        "Yüksek performans eşiği: %.6f (Ort: %.6f × %.1f)",
        threshold,
        avg_rate,
        threshold_multiplier,
    )

    high_performers = [
        t for t in tweet_archive if t.get("engagement_rate", 0.0) >= threshold
    ]
    high_performers.sort(key=lambda t: t["engagement_rate"], reverse=True)

    return high_performers


# ---------------------------------------------------------------------------
# Performans snapshot güncelleme
# ---------------------------------------------------------------------------

def update_performance_snapshot(style_memory: dict, tweet_archive: list[dict]) -> None:
    """
    style_memory içindeki performance_snapshot alanını arşiv verisiyle günceller.
    """
    if not tweet_archive:
        return

    snapshot = style_memory.setdefault("performance_snapshot", {})

    total_likes = 0
    total_replies = 0
    total_retweets = 0
    total_bookmarks = 0
    total_quotes = 0
    total_impressions = 0
    total_engagements = 0

    for tweet in tweet_archive:
        m = tweet.get("metrics", {})
        likes = m.get("like_count", 0) or 0
        replies = m.get("reply_count", 0) or 0
        retweets = m.get("retweet_count", 0) or 0
        bookmarks = m.get("bookmark_count", 0) or 0
        quotes = m.get("quote_count", 0) or 0
        # twikit: view_count replaces impression_count
        impressions = m.get("view_count", 0) or 0

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

    # Oran hesaplamaları (sıfıra bölme koruması)
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
# Evolution log — sürüm takibi
# ---------------------------------------------------------------------------

def append_evolution_log(style_memory: dict, trigger: str, summary: str) -> None:
    """
    style_memory'ye bir evolution_log girişi ekler ve version'ı artırır.

    Giriş formatı (RESEARCH.md):
        {
            "date": ISO-8601 UTC timestamp,
            "trigger": str,       # örn: "sync", "--since override", "manual"
            "change_summary": str, # örn: "Added 12 tweets. 3 new high_performers."
            "version": int,       # artırılmış sürüm numarası
        }
    """
    style_memory["version"] = style_memory.get("version", 0) + 1
    entry = {
        "date": datetime.now(timezone.utc).isoformat(),
        "trigger": trigger,
        "change_summary": summary,
        "version": style_memory["version"],
    }
    style_memory.setdefault("evolution_log", []).append(entry)
    logger.debug(
        "Evolution log güncellendi. Versiyon: %d, Tetikleyici: %s",
        style_memory["version"],
        trigger,
    )


# ---------------------------------------------------------------------------
# Ana sync akışı
# ---------------------------------------------------------------------------

async def run_sync(dry_run: bool = False, since: str | None = None) -> None:
    """
    Ana sync fonksiyonu. Tüm adımları sırasıyla çalıştırır:
      1. Config yükle
      2. style_memory oku
      3. Cutoff belirle
      4. Auth client al
      5. Tweetleri çek
      6. Kategorize et
      7. Arşive ekle (deduplicate)
      8. Rolling window uygula
      9. Yüksek performanslıları belirle
      10. Snapshot'ı güncelle
      11. evolution_log ekle (dry-run değilse ve yeni tweet varsa)
      12. Dosyayı kaydet (dry-run değilse)
      13. Raporu terminale yaz
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

    # Adım 2: style_memory oku
    style_memory = load_style_memory()

    # Kullanıcı bilgilerini güncelle (boşsa)
    if not style_memory.get("userId"):
        style_memory["userId"] = user_id
    if not style_memory.get("handle"):
        style_memory["handle"] = f"@{username.lstrip('@')}"

    # Adım 3: Cutoff belirle
    if since:
        # --since parametresi öncelikli
        try:
            cutoff = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
            logger.info("--since parametresi kullanılıyor: %s", cutoff.isoformat())
        except ValueError:
            logger.error(
                "Geçersiz tarih formatı: '%s'. ISO-8601 formatı kullan (örn: 2025-01-01 veya 2025-01-01T00:00:00)",
                since,
            )
            sys.exit(1)
    elif style_memory.get("last_synced_at"):
        # Önceki sync zamanından devam et
        cutoff = datetime.fromisoformat(style_memory["last_synced_at"]).replace(
            tzinfo=timezone.utc
        )
        logger.info("Son sync zamanından devam ediliyor: %s", cutoff.isoformat())
    else:
        # İlk kez çalışıyor — cutoff yok, ilk 200 tweet çekilir
        cutoff = None
        logger.info("İlk sync — cutoff yok, ilk 200 tweet çekilecek.")

    # Adım 4: Auth client al
    auth_client = await get_authenticated_client(
        cookies_file=str(COOKIES_FILE),
        username=config["USERNAME"],
        email=config["EMAIL"],
        password=config["PASSWORD"],
    )

    # Adım 5: Tweetleri çek
    raw_tweets = await fetch_tweets_since(auth_client, user_id, cutoff)

    if not raw_tweets:
        logger.info("Yeni tweet bulunamadı. Sync tamamlandı.")
        _print_sync_report(
            username=username,
            new_count=0,
            total_archive=len(style_memory.get("tweet_archive", [])),
            high_performer_count=len(style_memory.get("high_performers", [])),
            avg_engagement=compute_avg_engagement_rate(style_memory.get("tweet_archive", [])),
            dry_run=dry_run,
        )
        return

    # Adım 6: Her tweeti kategorize et
    logger.info("%d yeni tweet kategorize ediliyor...", len(raw_tweets))
    categorized_tweets = [categorize_tweet(t) for t in raw_tweets]

    # Adım 7: Arşive ekle (tekrar eklememek için id kontrolü yap)
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

    # Arşivi created_at'e göre azalan sırayla (en yeni önce) düzenle
    tweet_archive.sort(key=lambda t: t.get("created_at", ""), reverse=True)

    # Adım 8: Rolling window: arşiv 1000 tweet'i aşarsa en eski olanları at
    MAX_ARCHIVE_SIZE = 1000
    if len(tweet_archive) > MAX_ARCHIVE_SIZE:
        tweet_archive = tweet_archive[:MAX_ARCHIVE_SIZE]
        style_memory["tweet_archive"] = tweet_archive
        logger.info(
            "Tweet arşivi %d'e kırpıldı (rolling window).", MAX_ARCHIVE_SIZE
        )

    # Adım 9: Yüksek performanslıları belirle (tüm arşiv üzerinde)
    high_performers = identify_high_performers(tweet_archive)
    new_high_performers = [hp for hp in high_performers
                           if hp["id"] not in {t["id"] for t in style_memory.get("high_performers", [])}]
    style_memory["high_performers"] = high_performers
    logger.info("%d yüksek performanslı tweet tespit edildi.", len(high_performers))

    # Adım 10: Performance snapshot güncelle
    update_performance_snapshot(style_memory, tweet_archive)

    # last_synced_at ve last_sync_count güncelle
    style_memory["last_synced_at"] = datetime.now(timezone.utc).isoformat()
    style_memory["last_sync_count"] = len(new_tweets)

    # Adım 11: evolution_log ekle (dry-run değilse ve yeni tweet varsa)
    if not dry_run and new_tweets:
        hp_delta = len(new_high_performers) - prev_hp_count
        append_evolution_log(
            style_memory,
            trigger="sync" if not since else "--since override",
            summary=f"Added {len(new_tweets)} tweets. High_performers delta: {hp_delta:+d}.",
        )

    # Adım 12: Kaydet (dry-run değilse)
    if not dry_run:
        save_style_memory(style_memory)
        logger.info("style_memory.json güncellendi.")
    else:
        logger.info("[DRY-RUN] style_memory.json DEĞİŞTİRİLMEDİ.")

    # Adım 13: Raporu terminale yaz
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
    """
    Sync işlemi tamamlandıktan sonra terminale okunabilir bir özet rapor yazar.
    """
    separator = "─" * 60
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
    """Komut satırı argümanlarını ayrıştırır."""
    parser = argparse.ArgumentParser(
        description="The Mirror — X (Twitter) tweet sync bileşeni",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python mirror_sync.py                        Normal sync
  python mirror_sync.py --dry-run              Test modu (kayıt yok)
  python mirror_sync.py --since 2025-01-01     Belirli tarihten itibaren
  python mirror_sync.py --dry-run --since 2025-06-01
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Gerçek kayıt yapmadan işlemi test eder.",
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help=(
            "Bu tarihten itibaren tweetleri çeker. "
            "Belirtilmezse last_synced_at kullanılır. "
            "Format: YYYY-MM-DD veya YYYY-MM-DDTHH:MM:SS"
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Ayrıntılı log çıktısı için DEBUG seviyesini etkinleştirir.",
    )
    return parser.parse_args()


def main() -> None:
    """Script giriş noktası."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("DEBUG modu etkin.")

    try:
        asyncio.run(run_sync(dry_run=args.dry_run, since=args.since))
    except KeyboardInterrupt:
        logger.info("Kullanıcı tarafından iptal edildi.")
        sys.exit(0)
    except Exception as e:
        logger.exception("Beklenmeyen hata: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
