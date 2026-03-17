# Phase 1: Mirror Foundation - Research

**Researched:** 2026-03-17
**Domain:** twikit 2.3.3 cookie-auth scraping, async Python, atomic file writes, JSON schema validation
**Confidence:** MEDIUM (twikit is a third-party scraper targeting X internal APIs — behaviour can change; critical findings verified against official docs and multiple sources)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SYNC-01 | mirror_sync.py migrated from tweepy to twikit 2.3.3, cookie-based auth | twikit Client + cookies_file param fully documented |
| SYNC-02 | Fetch own tweets: text, created_at, view_count, like_count, reply_count, retweet_count, bookmark_count | All fields confirmed on Tweet object (view_count added in 2.x, bookmark_count in 2.2.2) |
| SYNC-03 | Incremental sync using last_synced_at as start boundary | twikit has NO start_time param — must paginate and stop when created_at < cutoff |
| SYNC-04 | Auto-categorize: hook_type, tone, format, is_reply, has_media | Existing regex heuristics in mirror_sync.py are reusable as-is |
| SYNC-05 | Atomic write to style_memory.json | tempfile + os.replace pattern with same-dir temp is the correct approach for Windows |
| SYNC-06 | 1000-tweet rolling window archive | Pure Python slice — no library needed |
| SYNC-07 | Rate limit protection: 429 backoff, daily max fetch | twikit raises TooManyRequests with rate_limit_reset attribute — use it |
| SYNC-08 | --dry-run and --since CLI flags | Already implemented in existing script — reuse argparse structure |
| SYNC-09 | Terminal summary report after sync | Already implemented in existing script — reuse _print_sync_report |
| MEM-01 | style_memory.json schema: performance_snapshot, hook_patterns, tone_profile, signature_expressions, high_performers, last_synced_at, version | Fully defined in SKILL.md; evolution_log also required |
| MEM-02 | high_performers auto-updated: engagement_rate > 1.5x average | Already implemented in identify_high_performers() — reusable |
| MEM-03 | performance_snapshot updated each sync | Already implemented in update_performance_snapshot() — reusable |
| MEM-04 | @ciftcibahadir initial values pre-filled | Values provided in SKILL.md; must be seeded on first run |
| MEM-05 | evolution_log tracks each update | Not yet in current mirror_sync.py — must be added |
| REFS-05 | .gitignore blocks cookies.json and .env | Simple two-line addition; no library needed |
</phase_requirements>

---

## Summary

Phase 1 migrates `mirror_sync.py` from the broken tweepy free tier (which returns null impression values) to twikit 2.3.3, a cookie-based scraper targeting X's internal GraphQL API. The migration is significant: twikit is fully async (asyncio), uses a different auth model (cookies.json instead of OAuth tokens), and has no `start_time` parameter on `get_user_tweets` — meaning incremental sync requires client-side date filtering during cursor pagination, not a server-side query parameter.

The existing `mirror_sync.py` is 830 lines and well-structured. Large sections — hook/tone/format detection heuristics, high-performer identification, performance snapshot computation, CLI argument handling, and the summary report printer — are **reusable without modification**. The core changes are: (1) replace the tweepy `Client` and `fetch_tweets_since` with twikit async equivalents, (2) wrap everything in `asyncio.run()`, (3) swap the `save_style_memory` function for an atomic-write version, (4) add `evolution_log` tracking, and (5) add a `.gitignore` file.

The primary technical risk is twikit's susceptibility to X bot detection (Error 226). The library's `enable_ui_metrics=True` flag reduces this risk. The recommendation is: do a single low-volume test run (fetch last 7 days) with `--dry-run` before committing to the full migration, and keep `twscrape 0.17.0` documented as the fallback.

**Primary recommendation:** Migrate to twikit 2.3.3. Use `asyncio.run()` as the sync entry point. Implement incremental sync by paginating through `get_user_tweets` and breaking when `tweet.created_at < last_synced_at`. Use `tempfile.NamedTemporaryFile(dir=same_dir) + os.replace()` for atomic writes.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| twikit | 2.3.3 | X internal API scraper — fetches own tweets with view_count and bookmark_count without an API key | Only free solution that returns view_count and bookmark_count; tweepy free tier returns null impressions |
| python-dotenv | >=1.0.0 | Load .env credentials at runtime | Already in project; standard pattern |
| asyncio | stdlib | Event loop for twikit async client | twikit 2.0+ is async-only; no sync version exists |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=8.0 | Test runner | All unit tests |
| pytest-asyncio | >=0.23 | Async test support | Testing twikit-calling async functions |
| Js2Py | (twikit dep) | Executes ui_metrics obfuscated JS | Installed automatically with twikit 2.3.1+; used when enable_ui_metrics=True |

### Fallback (if twikit fails bot-detection validation)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| twscrape | 0.17.0 | Alternative X scraper with SQLite account pool | Use if twikit triggers Error 226 on @ciftcibahadir's account; supports viewCount and bookmarkCount fields |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| twikit | tweepy v4 | tweepy free tier returns null impression_count — disqualified |
| twikit | twscrape | twscrape uses a multi-account pool model (more complex setup); twikit is simpler for single-account use |
| tempfile+os.replace | atomicwrites library | atomicwrites is unmaintained (last release 2020); stdlib pattern is equivalent and has no dependency |
| pydantic | jsonschema | Both work; pydantic is heavier for v1 scope; manual key-presence check is lightest option |

**Installation:**
```bash
pip install twikit python-dotenv pytest pytest-asyncio
```

---

## Architecture Patterns

### Recommended Project Structure
```
skills/the-mirror/
├── mirror_sync.py          # Main sync script (rewritten)
├── style_memory.json       # Output — local only, gitignored
├── cookies.json            # twikit session — gitignored
├── .env                    # Credentials — gitignored
├── .gitignore              # Blocks cookies.json, .env, style_memory.json
└── tests/
    ├── conftest.py         # Fixtures: sample tweets, mock twikit responses
    ├── test_categorize.py  # detect_hook_type, detect_tone, detect_format
    ├── test_memory.py      # high_performers, performance_snapshot, evolution_log
    └── test_atomic_write.py # Atomic write correctness on Windows
```

### Pattern 1: twikit Async Auth with Cookie Persistence
**What:** Login once, save cookies, reload on subsequent runs — avoids repeated login that triggers bot detection.
**When to use:** Every run of mirror_sync.py.
**Example:**
```python
# Source: twikit 2.3.3 official docs + PyPI README
import asyncio
from twikit import Client

client = Client('en-US')

async def get_authenticated_client() -> Client:
    cookies_file = 'cookies.json'
    try:
        client.load_cookies(cookies_file)
        # Validate session with lightweight call
        await client.user_id()
        return client
    except Exception:
        await client.login(
            auth_info_1=USERNAME,
            auth_info_2=EMAIL,
            password=PASSWORD,
            cookies_file=cookies_file,
            enable_ui_metrics=True,   # Reduces bot detection risk
        )
        return client
```

### Pattern 2: Incremental Sync via Client-Side Date Filter
**What:** twikit's `get_user_tweets` has NO `start_time` parameter. Pagination must be stopped manually when `tweet.created_at` falls before `last_synced_at`.
**When to use:** Every sync run except the initial full-fetch.
**Example:**
```python
# Source: twikit docs (get_user_tweets signature) + pagination pattern
async def fetch_tweets_since(client, user_id: str, cutoff: datetime) -> list:
    tweets = await client.get_user_tweets(user_id, 'Tweets', count=40)
    collected = []

    while tweets:
        new_batch = []
        stop = False
        for tweet in tweets:
            if tweet.created_at_datetime < cutoff:
                stop = True
                break
            new_batch.append(tweet)
        collected.extend(new_batch)
        if stop or not tweets:
            break
        try:
            tweets = await tweets.next()
        except Exception:
            break
    return collected
```

**Key detail:** `tweet.created_at_datetime` is a `datetime` object. `tweet.created_at` is an ISO string. Use `created_at_datetime` for comparisons.

### Pattern 3: Atomic Write on Windows
**What:** Write to temp file in the same directory, then `os.replace()` — guarantees the previous file survives a crash mid-write.
**When to use:** Every `save_style_memory()` call.
**Example:**
```python
# Source: https://code.activestate.com/recipes/579097-safely-and-atomically-write-to-a-file/
# Cross-verified: tempfile.NamedTemporaryFile same-dir + os.replace is the standard stdlib pattern
import tempfile, os, json

def save_style_memory_atomic(data: dict, path) -> None:
    path = str(path)
    dir_ = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        os.unlink(tmp_path)
        raise
```

**Windows caveat:** `os.replace()` calls `MoveFileEx` on Windows. When source and destination are on the same drive (which they will be — temp file written to same directory), this is effectively atomic. Cross-drive scenarios do NOT apply here because the temp file is explicitly created in `dir_` = the same folder as the target.

### Pattern 4: twikit Rate Limit Handling
**What:** Catch `TooManyRequests`, read `rate_limit_reset` attribute, sleep until reset.
**When to use:** Any twikit API call in the fetch loop.
**Example:**
```python
# Source: twikit.errors documentation + community pattern
from twikit import TooManyRequests
import time

async def safe_next(result):
    for attempt in range(5):
        try:
            return await result.next()
        except TooManyRequests as e:
            reset_at = getattr(e, 'rate_limit_reset', None)
            if reset_at:
                wait = max(0, reset_at - int(time.time())) + 5  # +5s buffer
            else:
                wait = 60 * (2 ** attempt)  # exponential fallback
            logger.warning("Rate limit hit. Sleeping %ds (attempt %d/5)", wait, attempt+1)
            await asyncio.sleep(wait)
    raise RuntimeError("Max rate limit retries exceeded")
```

### Anti-Patterns to Avoid
- **Re-login on every run:** Triggers bot detection. Always check if cookies are still valid first.
- **Using `asyncio.get_event_loop().run_until_complete()` on Windows:** Python 3.10+ on Windows uses `ProactorEventLoop` by default; use `asyncio.run()` which handles this correctly.
- **Tweepy's `start_time` assumption:** twikit does NOT support `start_time` as a query parameter. The incremental sync must be client-side.
- **Writing style_memory.json directly:** A crash mid-write corrupts the file. Always use the temp+replace pattern.
- **Cross-drive tempfile:** `tempfile.mkstemp()` without `dir=` argument creates temp in system's temp directory (often a different drive on Windows). Always pass `dir=os.path.dirname(target_path)`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cookie session persistence | Custom JSON serializer for cookies | `client.save_cookies()` / `client.load_cookies()` | twikit's built-in methods handle session format correctly |
| X internal API auth | Custom HTTP headers + session management | twikit Client | X's internal API requires specific headers that twikit maintains |
| Async event loop management | Manual loop creation | `asyncio.run(main())` | Handles loop creation, cleanup, and Windows ProactorEventLoop edge cases |
| Atomic file replace | Manual backup-and-swap logic | `tempfile.mkstemp + os.replace` in same dir | Windows `os.replace` is atomic on same-drive moves |

**Key insight:** twikit handles all X internal API complexity (GraphQL endpoint discovery, header obfuscation, CSRF tokens). Don't replicate this — just use the client.

---

## Common Pitfalls

### Pitfall 1: twikit is Async-Only Since 2.0.0
**What goes wrong:** Calling `client.login()` or `client.get_user_tweets()` without `await` silently returns a coroutine object, not data.
**Why it happens:** The existing `mirror_sync.py` is entirely synchronous (tweepy pattern). Developers forget to wrap twikit calls.
**How to avoid:** Wrap all twikit calls in `async def` functions. Entry point uses `asyncio.run(main())`.
**Warning signs:** `TypeError: 'coroutine' object is not subscriptable` or no tweets returned.

### Pitfall 2: No start_time Parameter in get_user_tweets
**What goes wrong:** Script attempts `client.get_user_tweets(user_id, 'Tweets', start_time=cutoff)` — this silently fails or raises `TypeError`.
**Why it happens:** Tweepy's `get_users_tweets` supports `start_time`. twikit's equivalent does not.
**How to avoid:** Implement client-side date filter: paginate and break when `tweet.created_at_datetime < cutoff`.
**Warning signs:** Full re-fetch on every run instead of incremental sync.

### Pitfall 3: Bot Detection (Error 226)
**What goes wrong:** X detects automated behaviour and suspends the account or returns Error 226 ("This request looks like it might be automated").
**Why it happens:** twikit calls X's internal API without official authorization. X actively fights scrapers.
**How to avoid:** (1) Always set `enable_ui_metrics=True` in login. (2) Reuse cookies — do NOT login on every run. (3) Keep request volume low: only fetch incremental tweets, not full history repeatedly. (4) Run at human-like intervals; do NOT run in a tight loop.
**Warning signs:** HTTP 403 with Error 226 message, sudden cookie expiry, account flagged.

### Pitfall 4: Stale Cookies Silently Fail
**What goes wrong:** `client.load_cookies()` loads the file successfully but the session is expired. Subsequent calls return empty results or auth errors instead of raising a clear exception.
**Why it happens:** Cookie sessions have a TTL. twikit doesn't always raise an explicit auth error on stale cookies.
**How to avoid:** After loading cookies, make a lightweight validation call (`await client.user_id()`) and catch exceptions to trigger re-login.
**Warning signs:** Empty tweet results despite the account having recent tweets.

### Pitfall 5: Windows Cross-Drive Atomic Write Failure
**What goes wrong:** `tempfile.mkstemp()` creates the temp file in `C:\Users\AppData\Local\Temp\` but the target is on `D:\`. `os.replace()` across drives is NOT atomic — it silently falls back to copy+delete.
**Why it happens:** Default `tempfile.mkstemp()` uses the system temp directory, which may be on a different drive.
**How to avoid:** Always pass `dir=os.path.dirname(os.path.abspath(target_path))` to `tempfile.mkstemp()`.
**Warning signs:** On D:\ installations, style_memory.json occasionally gets corrupted after interruption.

### Pitfall 6: view_count is 0 for Non-Authenticated Requests
**What goes wrong:** `tweet.view_count` returns 0 or None for all tweets.
**Why it happens:** X only returns view data for authenticated requests from the tweet's owner.
**How to avoid:** Ensure twikit is authenticated as @ciftcibahadir before calling `get_user_tweets`. The cookie session must be for the target account.
**Warning signs:** All view_count values are 0 or None after migration.

---

## Code Examples

Verified patterns from official sources and cross-referenced community usage:

### Full Auth + Fetch Flow (twikit 2.3.3)
```python
# Source: twikit PyPI README + readthedocs.io
import asyncio
from twikit import Client, TooManyRequests
from pathlib import Path

COOKIES_FILE = Path(__file__).parent / 'cookies.json'

async def main():
    client = Client('en-US')

    if COOKIES_FILE.exists():
        try:
            client.load_cookies(str(COOKIES_FILE))
            me = await client.user_id()  # Validate session
        except Exception:
            await client.login(
                auth_info_1=USERNAME,
                auth_info_2=EMAIL,
                password=PASSWORD,
                cookies_file=str(COOKIES_FILE),
                enable_ui_metrics=True,
            )
    else:
        await client.login(
            auth_info_1=USERNAME,
            auth_info_2=EMAIL,
            password=PASSWORD,
            cookies_file=str(COOKIES_FILE),
            enable_ui_metrics=True,
        )

    # Fetch own tweets
    tweets = await client.get_user_tweets(USER_ID, 'Tweets', count=40)
    for tweet in tweets:
        print(tweet.text, tweet.view_count, tweet.bookmark_count)

asyncio.run(main())
```

### Tweet Object Fields Available in twikit
```python
# Source: twikit.readthedocs.io/en/latest/twikit.html — Tweet class attributes
tweet.id                 # str
tweet.text               # str
tweet.created_at         # str (ISO-8601)
tweet.created_at_datetime # datetime
tweet.view_count         # int (requires auth as tweet owner)
tweet.bookmark_count     # int (added in twikit 2.2.2)
tweet.favorite_count     # int (likes)
tweet.retweet_count      # int
tweet.reply_count        # int
tweet.quote_count        # int
tweet.in_reply_to        # Tweet | None
tweet.media              # list[Photo | AnimatedGif | Video]
tweet.user               # User
tweet.lang               # str
```

### Atomic Write — Final Pattern
```python
# Source: Pattern derived from atomicwrites docs + ActiveState recipe
# Verified: os.replace atomic on same-drive Windows per Python docs
import tempfile, os, json

def save_style_memory(data: dict, path: str) -> None:
    abs_path = os.path.abspath(path)
    target_dir = os.path.dirname(abs_path)
    fd, tmp_path = tempfile.mkstemp(dir=target_dir, suffix='.json.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())  # Force to disk before rename
        os.replace(tmp_path, abs_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
```

### evolution_log Entry (New in Phase 1)
```python
# Not in current mirror_sync.py — must be added
from datetime import datetime, timezone

def append_evolution_log(style_memory: dict, trigger: str, summary: str) -> None:
    log = style_memory.setdefault('evolution_log', [])
    version = style_memory.get('version', 0) + 1
    style_memory['version'] = version
    log.append({
        'date': datetime.now(timezone.utc).isoformat(),
        'trigger': trigger,
        'change_summary': summary,
        'version': version,
    })
```

### .gitignore (REFS-05)
```
# Credentials — never commit
.env
cookies.json

# Local data — stays on user's machine
style_memory.json

# Python
__pycache__/
*.pyc
*.pyo
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| tweepy free tier with Bearer token | twikit 2.3.3 cookie-based internal API | 2023 (X API paywall), migration decision 2026-03-17 | view_count and bookmark_count now non-null |
| tweepy sync Client | twikit async Client (asyncio) | twikit 2.0.0 (2024) | All fetch code must be async; entry point uses asyncio.run() |
| tweepy start_time parameter | Manual cursor pagination with client-side date filter | Always the case with twikit | More code in fetch loop; no server-side time filter |
| tweepy OAuth 1.0a tokens in .env | twikit cookie session in cookies.json | twikit design | .gitignore must block cookies.json, not just .env |
| twikit sync client (1.x) | twikit async-only (2.x) | twikit 2.0.0 release | No sync wrapper available; must use asyncio |
| twikit node.js for ui_metrics | Js2Py for ui_metrics (twikit 2.3.1) | twikit 2.3.1 (Feb 6 2025) | No node.js dependency required |

**Deprecated/outdated:**
- `tweepy.Client.get_users_tweets()`: Returns null `impression_count` on free tier — cannot be used.
- `twikit` sync client (`from twikit.sync import Client`): Removed in 2.0.0.
- `Result.cursor` and `Result.token` on twikit Result objects: Removed in a recent version; use `.next()` method instead.

---

## Open Questions

1. **twikit `get_user_tweets` count limit per call**
   - What we know: Default count=40; parameter accepted up to some maximum.
   - What's unclear: What is the practical maximum per call before rate limiting? The ratelimits.md file could not be fetched (429 during research).
   - Recommendation: Start with count=40 (default). Test with count=100. If rate limit hits, drop to 20. Document empirically on first test run.

2. **view_count availability for all tweets vs. recent only**
   - What we know: view_count is a confirmed Tweet attribute. It requires owner-authenticated requests.
   - What's unclear: Does X return view_count for tweets older than a certain age? Some sources suggest older tweet stats may be incomplete.
   - Recommendation: Log a warning when view_count is 0 but do not fail; mark affected tweets with `"view_count_reliable": false`.

3. **twikit Bot Detection Threshold for @ciftcibahadir**
   - What we know: Error 226 is real; temp-mail accounts got suspended in testing. The `enable_ui_metrics=True` flag helps.
   - What's unclear: What volume/frequency is safe for an established account (@ciftcibahadir is 137 followers, real account)?
   - Recommendation: First run with `--dry-run` fetching only last 7 days (no write). Validate view_count is non-zero. Only proceed to full migration if no Error 226.

4. **twscrape fallback — does it return view_count for own tweets?**
   - What we know: twscrape Tweet model has `viewCount` field. It uses multi-account pool for rate resilience.
   - What's unclear: Whether `viewCount` is populated when fetching your own tweets (vs. fetching someone else's). The models.py source was inaccessible during research.
   - Recommendation: If twikit fails, test twscrape with: `await gather(api.user_tweets(user_id, limit=5))` and inspect the `viewCount` field on returned tweets.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23+ |
| Config file | `tests/conftest.py` — Wave 0 creates this |
| Quick run command | `pytest skills/the-mirror/tests/ -x -q` |
| Full suite command | `pytest skills/the-mirror/tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SYNC-01 | twikit Client initializes without error | unit | `pytest tests/test_auth.py::test_client_init -x` | Wave 0 |
| SYNC-02 | categorize_tweet returns view_count, bookmark_count fields | unit | `pytest tests/test_categorize.py::test_tweet_fields -x` | Wave 0 |
| SYNC-03 | fetch_tweets_since stops at cutoff date (mock) | unit | `pytest tests/test_fetch.py::test_incremental_cutoff -x` | Wave 0 |
| SYNC-04 | detect_hook_type returns correct enum for sample texts | unit | `pytest tests/test_categorize.py::test_hook_types -x` | Wave 0 |
| SYNC-05 | Atomic write leaves old file intact when interrupted | unit | `pytest tests/test_atomic_write.py::test_crash_safety -x` | Wave 0 |
| SYNC-06 | Archive truncated to 1000 tweets when over limit | unit | `pytest tests/test_memory.py::test_rolling_window -x` | Wave 0 |
| SYNC-07 | TooManyRequests exception triggers backoff (mock) | unit | `pytest tests/test_fetch.py::test_rate_limit_backoff -x` | Wave 0 |
| SYNC-08 | --dry-run exits without writing file | unit | `pytest tests/test_cli.py::test_dry_run -x` | Wave 0 |
| SYNC-09 | _print_sync_report outputs expected summary fields | unit | `pytest tests/test_report.py::test_summary_output -x` | Wave 0 |
| MEM-01 | style_memory.json contains all required top-level keys | unit | `pytest tests/test_memory.py::test_schema_keys -x` | Wave 0 |
| MEM-02 | identify_high_performers selects tweets >= 1.5x avg rate | unit | `pytest tests/test_memory.py::test_high_performers -x` | Wave 0 |
| MEM-03 | update_performance_snapshot computes correct ratios | unit | `pytest tests/test_memory.py::test_snapshot_ratios -x` | Wave 0 |
| MEM-04 | Initial seed data for @ciftcibahadir present on first run | unit | `pytest tests/test_memory.py::test_initial_seed -x` | Wave 0 |
| MEM-05 | evolution_log entry added after each sync | unit | `pytest tests/test_memory.py::test_evolution_log -x` | Wave 0 |
| REFS-05 | .gitignore contains cookies.json and .env entries | smoke | `pytest tests/test_gitignore.py::test_gitignore_blocks -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest skills/the-mirror/tests/ -x -q`
- **Per wave merge:** `pytest skills/the-mirror/tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `skills/the-mirror/tests/__init__.py` — empty init
- [ ] `skills/the-mirror/tests/conftest.py` — sample tweet fixtures, mock twikit client
- [ ] `skills/the-mirror/tests/test_categorize.py` — covers SYNC-02, SYNC-04
- [ ] `skills/the-mirror/tests/test_fetch.py` — covers SYNC-03, SYNC-07
- [ ] `skills/the-mirror/tests/test_atomic_write.py` — covers SYNC-05
- [ ] `skills/the-mirror/tests/test_memory.py` — covers SYNC-06, MEM-01 through MEM-05
- [ ] `skills/the-mirror/tests/test_cli.py` — covers SYNC-08
- [ ] `skills/the-mirror/tests/test_report.py` — covers SYNC-09
- [ ] `skills/the-mirror/tests/test_auth.py` — covers SYNC-01
- [ ] `skills/the-mirror/tests/test_gitignore.py` — covers REFS-05
- [ ] Framework install: `pip install pytest pytest-asyncio` — if not already installed

---

## Sources

### Primary (HIGH confidence)
- [twikit readthedocs](https://twikit.readthedocs.io/en/latest/twikit.html) — Tweet class attributes (view_count, bookmark_count confirmed), get_user_tweets signature, Client.login parameters
- [twikit PyPI](https://pypi.org/project/twikit/) — Latest version (2.3.3), installation
- [twikit GitHub releases](https://github.com/d60/twikit/releases) — bookmark_count added in 2.2.2, ui_metrics added in 2.3.0, Js2Py switch in 2.3.1
- [python-atomicwrites docs](https://python-atomicwrites.readthedocs.io/) — Windows atomic write behavior, MoveFileEx, same-dir temp requirement
- [ActiveState atomic write recipe](https://code.activestate.com/recipes/579097-safely-and-atomically-write-to-a-file/) — tempfile+os.replace canonical pattern

### Secondary (MEDIUM confidence)
- [jesuspaz.com twikit guide 2025](https://jesuspaz.com/articles/extract-tweets-python-twikit) — Cookie auth flow, load_cookies/save_cookies pattern
- [twikit GitHub repo README](https://github.com/d60/twikit) — General auth flow, async-only since 2.0.0
- [vladkens/twscrape GitHub](https://github.com/vladkens/twscrape) — twscrape fallback; user_tweets method, viewCount field mentioned in models.py
- [pytest-asyncio PyPI](https://pypi.org/project/pytest-asyncio/) — Version 1.3.0, Windows async test setup

### Tertiary (LOW confidence — flag for validation)
- Bot detection risk (Error 226) severity: reported by community users but not officially documented; real temp-mail account suspension is a single data point
- twikit rate limits per 15 minutes: ratelimits.md was inaccessible (429) during research — exact numbers unknown; treat as unknown until tested
- `tweet.view_count` for tweets older than 30-90 days: availability not confirmed — empirical test required

---

## Metadata

**Confidence breakdown:**
- Standard stack (twikit 2.3.3 as primary, twscrape as fallback): MEDIUM — twikit confirmed on PyPI and docs; behaviour against live X API subject to change
- Architecture (async pattern, incremental pagination, atomic write): HIGH — patterns are verified stdlib/official patterns
- Pitfalls (bot detection, Windows cross-drive, no start_time): MEDIUM — async/atomic confirmed; bot detection severity is LOW (community reports, not official docs)
- Tweet fields (view_count, bookmark_count): HIGH — confirmed in twikit readthedocs Tweet class

**Research date:** 2026-03-17
**Valid until:** 2026-04-17 (twikit moves fast; re-verify if X changes internal API endpoints)
