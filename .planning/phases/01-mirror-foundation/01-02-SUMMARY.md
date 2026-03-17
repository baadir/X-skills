---
phase: 01-mirror-foundation
plan: "02"
subsystem: fetch
tags: [twikit, async, auth, pagination, rate-limit, cookies]

# Dependency graph
requires:
  - phase: 01-01
    provides: "pytest test scaffold with MockTweet fixtures and RED stub tests"
provides:
  - "async get_authenticated_client: cookie-load with stale-cookie fallback to login (enable_ui_metrics=True)"
  - "async safe_next: TooManyRequests exponential backoff with up to 5 retries"
  - "async fetch_tweets_since: client-side cutoff pagination, converts twikit Tweet to plain dict"
  - "load_env updated for twikit: USERNAME/EMAIL/PASSWORD/USER_ID (tweepy tokens removed)"
  - "COOKIES_FILE constant pointing to cookies.json in script directory"
affects:
  - 01-03-PLAN
  - 01-04-PLAN

# Tech tracking
tech-stack:
  added: [twikit==2.3.3]
  patterns:
    - "cookie-persistent auth: load_cookies first, login fallback on exception"
    - "client-side cutoff: compare tweet.created_at_datetime < cutoff to stop pagination"
    - "first-run page cap: MAX_INITIAL_PAGES=5 (200 tweets) when cutoff is None"
    - "immediate dict conversion: _tweet_to_dict converts twikit Tweet at fetch time"
    - "module-level client singleton: client = Client('en-US') reused across calls"

key-files:
  created: []
  modified:
    - skills/the-mirror/mirror_sync.py
    - skills/the-mirror/tests/test_auth.py
    - skills/the-mirror/tests/test_fetch.py

key-decisions:
  - "Module-level twikit Client singleton — tests patch ms.client directly; avoids re-instantiation on each call"
  - "test_auth.py and test_fetch.py use direct `import mirror_sync` (not `skills.the_mirror.mirror_sync`) — tests run via pytest from project root with the-mirror on sys.path via __init__.py marker"
  - "MockTweet duplicated locally in test_fetch.py rather than importing from conftest — conftest is not a regular importable module, only pytest-injectable"
  - "categorize_tweet and detect_* functions left unchanged for Plan 03 — script intentionally does not run end-to-end after this plan"

patterns-established:
  - "Patch ms.client in auth tests to replace module-level singleton without touching Client constructor"
  - "patch.object(ms.asyncio, 'sleep') to eliminate actual wait in rate-limit backoff tests"

requirements-completed: [SYNC-01, SYNC-02, SYNC-03, SYNC-07]

# Metrics
duration: 6min
completed: 2026-03-17
---

# Phase 1 Plan 02: twikit Fetch Layer Summary

**Async twikit 2.3.3 auth (cookie-persistent + login fallback), incremental pagination with client-side cutoff, and TooManyRequests exponential backoff replacing the tweepy fetch layer in mirror_sync.py**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-03-17T08:25:44Z
- **Completed:** 2026-03-17T08:31:44Z
- **Tasks:** 1 of 1
- **Files modified:** 3

## Accomplishments

- Rewrote the top section of `mirror_sync.py`: replaced tweepy imports, `build_tweepy_client()`, and synchronous `fetch_tweets_since()` with twikit-based async equivalents
- `get_authenticated_client` loads cookies.json if it exists and falls back to `client.login` with `enable_ui_metrics=True` on stale/missing cookies
- `safe_next` retries pagination up to 5 times on `TooManyRequests`, using `rate_limit_reset` header or exponential backoff when not available
- `fetch_tweets_since` stops iteration the moment `tweet.created_at_datetime < cutoff`; on first run (cutoff=None) caps at 5 pages / 200 tweets
- Turned all 3 RED stub tests GREEN: `test_client_init`, `test_incremental_cutoff`, `test_rate_limit_backoff`

## Task Commits

1. **Task 1: Rewrite mirror_sync.py fetch layer — async auth, incremental pagination, rate limiting** - `25a594b` (feat)

**Plan metadata:** (pending final commit)

## Files Created/Modified

- `skills/the-mirror/mirror_sync.py` — Rewritten header: imports block (twikit, asyncio), constants (COOKIES_FILE, TWEETS_PER_PAGE=40), load_env (USERNAME/EMAIL/PASSWORD/USER_ID), get_authenticated_client, safe_next, fetch_tweets_since, _tweet_to_dict; everything from detect_hook_type onwards left intact
- `skills/the-mirror/tests/test_auth.py` — Implements test_client_init: mocks module-level client, verifies login called with correct kwargs when cookies file absent
- `skills/the-mirror/tests/test_fetch.py` — Implements test_incremental_cutoff (stops at T-1d boundary) and test_rate_limit_backoff (2 failures + success = call_count 3)

## Decisions Made

- **Module-level client singleton:** `client = Client("en-US")` declared at module level so tests can patch `ms.client` without touching the constructor. This matches how real twikit scripts are structured.
- **Direct `import mirror_sync`:** Tests in `skills/the-mirror/tests/` use plain `import mirror_sync` because pytest adds `skills/the-mirror/` to sys.path (the `tests/__init__.py` from Plan 01 causes pytest to walk up one level). The plan's `from skills.the_mirror import mirror_sync` criterion requires `__init__.py` files that don't exist yet — the import check was verified via syntax check + pytest run instead.
- **Local MockTweet in test_fetch.py:** `conftest.py` fixtures are injectable by pytest but conftest is not an importable module. Defined a minimal `MockTweet` locally in test_fetch.py rather than fighting the import path.
- **categorize_tweet left as-is:** The function still references tweepy-style `public_metrics` dict shape. Plan 03 will adapt it to consume the new `_tweet_to_dict` output. Intentional technical debt scoped to one plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed direct `from conftest import MockTweet` import in test_fetch.py**
- **Found during:** Task 1 (test verification run)
- **Issue:** `from conftest import MockTweet` raises `ModuleNotFoundError: No module named 'conftest'` — conftest.py is not on sys.path as a regular module; it is loaded by pytest as a plugin
- **Fix:** Defined a minimal `MockTweet` class directly in `test_fetch.py` with the attributes needed by the fetch tests
- **Files modified:** `skills/the-mirror/tests/test_fetch.py`
- **Verification:** `python -m pytest test_auth.py test_fetch.py -v` — 3 passed
- **Committed in:** `25a594b` (same task commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Fix was necessary to make tests importable. No scope change; MockTweet attributes are identical to conftest version.

## Issues Encountered

- `twikit` was not installed in the environment at test-run time — installed via `pip install twikit python-dotenv` as a blocking Rule 3 fix. Both packages now present.

## User Setup Required

None — no external service configuration required for this plan. The `.env` and `cookies.json` files needed for a real sync run are covered by Plan 01's `.gitignore` and will be created during first-run authentication.

## Next Phase Readiness

- `get_authenticated_client`, `safe_next`, `fetch_tweets_since` are implemented and tested
- Plan 03 (categorize_tweet rewrite) can import `mirror_sync` and use `fetch_tweets_since` output directly
- Plan 04 (orchestration) can call `asyncio.run(get_authenticated_client(...))` + `fetch_tweets_since` as its data source
- Remaining concern: twikit cookie-based auth has LOW confidence against X bot detection — validate with a real low-volume run before committing to production use (carry-over from STATE.md blocker)

---
*Phase: 01-mirror-foundation*
*Completed: 2026-03-17*
