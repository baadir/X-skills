"""
TwitterYoldas — Performance Checker
Yayınlanan tweet'lerin ilk 3 gün metriklerini otomatik çeker.

Kullanım:
  python performance_checker.py                    # Normal (eksik günleri çek)
  python performance_checker.py --dry-run          # Test (DB'ye yazma)
  python performance_checker.py --draft-id <uuid>  # Tek draft için zorla
  python performance_checker.py --force-day 1      # Belirli gün numarasını zorla
"""

import sys, os, asyncio, argparse, json
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Windows terminal encoding fix
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

_HERE    = Path(__file__).resolve().parent
ROOT     = _HERE.parent
COOKIES  = ROOT / "skills" / "the-mirror" / "cookies.json"

sys.path.insert(0, str(_HERE))
import db_manager

# ── Argümanlar ───────────────────────────────────────────────
parser = argparse.ArgumentParser(description="TwitterYoldas Performance Checker")
parser.add_argument("--dry-run",   action="store_true", help="DB'ye yazma, sadece logla")
parser.add_argument("--draft-id",  default=None,        help="Tek bir draft UUID'si")
parser.add_argument("--force-day", type=int, default=None, help="Belirli gün numarasını zorla")
args = parser.parse_args()

DRY_RUN   = args.dry_run
TARGET_ID = args.draft_id
FORCE_DAY = args.force_day


def which_days_needed(posted_at_str: str, existing_days: set[int]) -> list[int]:
    """
    posted_at'den bu yana kaç tam gün geçtiğine bakarak
    eksik ve zamanı gelmiş snapshot günlerini döndürür.
    """
    try:
        if posted_at_str.endswith("Z"):
            posted_at_str = posted_at_str[:-1] + "+00:00"
        posted = datetime.fromisoformat(posted_at_str)
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)
    except Exception:
        return []

    now        = datetime.now(timezone.utc)
    days_since = (now - posted).total_seconds() / 86400  # float gün sayısı

    needed = []
    for d in range(4):   # day 0,1,2,3
        if d in existing_days:
            continue
        # day 0 → hemen (posted_at'den itibaren 2 saat içinde de olsa)
        # day 1 → 20+ saat geçmişse (erken okuma payı)
        threshold = max(0, d - 0.2)
        if days_since >= threshold:
            needed.append(d)

    return needed


# ── twikit ile metrik çekme ───────────────────────────────────
async def fetch_metrics_twikit(tweet_id: str) -> dict | None:
    if not COOKIES.exists():
        print(f"  [twikit] cookies.json bulunamadı: {COOKIES}")
        return None
    try:
        from twikit import Client
        client = Client(language="en-US")
        await client.load_cookies(str(COOKIES))
        tweet = await client.get_tweet_by_id(tweet_id)
        if not tweet:
            return None
        m = {
            "likes":       int(getattr(tweet, "favorite_count",  0) or 0),
            "retweets":    int(getattr(tweet, "retweet_count",   0) or 0),
            "replies":     int(getattr(tweet, "reply_count",     0) or 0),
            "quotes":      int(getattr(tweet, "quote_count",     0) or 0),
            "bookmarks":   int(getattr(tweet, "bookmark_count",  0) or 0),
            "impressions": int(getattr(tweet, "view_count",      0) or 0),
        }
        print(f"  [twikit] OK: {m}")
        return m
    except Exception as e:
        print(f"  [twikit] Hata: {type(e).__name__}: {e}")
        return None


# ── X API v2 fallback (Bearer Token) ─────────────────────────
def fetch_metrics_xapi(tweet_id: str) -> dict | None:
    bearer = os.getenv("X_BEARER_TOKEN")
    if not bearer:
        print("  [x_api] X_BEARER_TOKEN env değişkeni yok, atlanıyor.")
        return None
    try:
        import urllib.request
        url = f"https://api.twitter.com/2/tweets/{tweet_id}?tweet.fields=public_metrics"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {bearer}"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        pm = data.get("data", {}).get("public_metrics", {})
        if not pm:
            return None
        m = {
            "likes":       pm.get("like_count",      0),
            "retweets":    pm.get("retweet_count",   0),
            "replies":     pm.get("reply_count",     0),
            "quotes":      pm.get("quote_count",     0),
            "bookmarks":   pm.get("bookmark_count",  0),
            "impressions": pm.get("impression_count",0),
        }
        print(f"  [x_api] OK: {m}")
        return m
    except Exception as e:
        print(f"  [x_api] Hata: {e}")
        return None


async def fetch_metrics(tweet_id: str) -> tuple[dict | None, str]:
    """twikit → x_api fallback zinciri. (metrics, source) döndürür."""
    m = await fetch_metrics_twikit(tweet_id)
    if m:
        return m, "twikit"
    m = fetch_metrics_xapi(tweet_id)
    if m:
        return m, "x_api"
    return None, "none"


# ── Ana işlem ────────────────────────────────────────────────
async def process_draft(draft: dict):
    draft_id   = str(draft["id"])
    tweet_id   = draft.get("first_tweet_id") or ""
    posted_at  = draft.get("posted_at") or ""
    # TIMESTAMPTZ PostgreSQL'den datetime objesi olarak gelir — string'e çevir
    if hasattr(posted_at, 'isoformat'):
        posted_at = posted_at.isoformat()
    title      = draft.get("thread_title", "?")[:50]

    if not tweet_id or not posted_at:
        print(f"  [SKIP] tweet_id veya posted_at eksik")
        return

    snapshots     = db_manager.get_snapshots(draft_id)
    existing_days = {int(s["day_number"]) for s in snapshots}

    if FORCE_DAY is not None:
        days_needed = [FORCE_DAY]
    else:
        days_needed = which_days_needed(posted_at, existing_days)

    if not days_needed:
        print(f"  [OK] Tüm günler mevcut: {sorted(existing_days)}")
        return

    print(f"  Eksik günler: {days_needed} | Mevcut: {sorted(existing_days)}")

    metrics, source = await fetch_metrics(tweet_id)
    if not metrics:
        print(f"  [FAIL] Metrik çekilemedi, atlanıyor.")
        return

    for day in days_needed:
        if DRY_RUN:
            print(f"  [DRY-RUN] Gün {day} → {metrics}")
        else:
            result = db_manager.save_snapshot(draft_id, tweet_id, day, metrics, source)
            print(f"  [SAVED] Gün {day} → engagement={result.get('engagement_rate')}%")


async def main():
    print(f"\n{'='*56}")
    print(f"TwitterYoldas Performance Checker — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if DRY_RUN:
        print("[DRY-RUN modu — DB'ye yazılmayacak]")
    print(f"{'='*56}\n")

    if TARGET_ID:
        draft = db_manager.get_draft(TARGET_ID)
        if not draft:
            print(f"Draft bulunamadı: {TARGET_ID}")
            return
        print(f"Draft: {draft.get('thread_title','?')[:50]}")
        await process_draft(draft)
    else:
        drafts = db_manager.list_drafts(status="atılmış")
        if not drafts:
            print("'atılmış' durumunda draft bulunamadı.")
            return
        print(f"{len(drafts)} yayınlanan draft kontrol ediliyor...\n")
        for draft in drafts:
            title = draft.get("thread_title", "?")[:50]
            print(f">> {title} [{str(draft.get('id',''))[:8]}...]")
            await process_draft(draft)
            print()

    print("Tamamlandı.\n")


if __name__ == "__main__":
    asyncio.run(main())
