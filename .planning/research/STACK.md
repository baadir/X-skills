# Technology Stack

**Project:** TwitterYoldas — Multi-Skill Twitter/X Growth Agent
**Researched:** 2026-03-17
**Scope:** V1 Mirror sync + skill prompt documents

---

## Executive Decision: Library Selection for Free Twitter Data Access

This is the most critical stack decision. The official X API has moved to pay-per-usage pricing with no free tier (confirmed March 2026). All free access requires unofficial/cookie-based scraping.

### Head-to-Head: Free Twitter Access Libraries

| Library | Version | Auth Method | bookmark_count | view_count | impression_count | Last Release | Maintenance |
|---------|---------|-------------|---------------|-----------|-----------------|-------------|-------------|
| twikit | 2.3.3 | Cookie-based | YES | YES (view_count) | NO | Feb 2025 | Active |
| twscrape | 0.17.0 | Account login (GraphQL) | YES (bookmarkedCount) | YES (viewCount) | NO | Apr 2025 | Active |
| twitter-api-client | 0.10.22 | Cookie-based + tweet_stats() | Unconfirmed | Unconfirmed | Unconfirmed | Apr 2024 | Stale |
| tweepy | 4.16.0 | Official OAuth2 | via non_public_metrics (paid) | via non_public_metrics (paid) | via non_public_metrics (paid) | Jun 2025 | Active |

**Critical finding:** "Impressions" in the X/Twitter context maps to `view_count` in cookie-based scrapers — NOT `impression_count`. The official `impression_count` field (from `non_public_metrics`) requires authenticated API calls at a paid tier. Cookie-based libraries return `view_count` which is the platform-visible impressions number seen in X Analytics and on tweet detail pages. For Mirror's purposes, `view_count` is the right metric — it is what X shows users as "impressions."

---

## Recommended Stack

### Core: Twitter Data Access

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **twikit** | 2.3.3 | Primary Twitter data access | Most straightforward cookie-based library; no API key needed; exposes `bookmark_count`, `view_count`, `favorite_count`, `retweet_count`, `reply_count`, `quote_count` on the Tweet object; async-native; actively maintained; clean API surface matching Mirror's needs |

**Why twikit over alternatives:**
- **Over twscrape:** twscrape is designed for scraping other accounts at scale (multi-account pool, GraphQL). twikit is simpler and better suited for single-user own-data access. twscrape's `bookmarkedCount` and `viewCount` are confirmed but the library adds complexity (account pool management, SQLite backend) that is unnecessary for Mirror's use case.
- **Over twitter-api-client:** Last release was April 2024 — 11+ months stale at time of research. The `tweet_stats()` method exists but its returned fields are unverified. Staleness is a disqualifying risk for a cookie-based library where X frequently changes internal APIs.
- **Over tweepy:** Tweepy with official OAuth requires paid API access to get impressions/bookmarks via `non_public_metrics`. The current mirror_sync.py already uses tweepy — this is the primary migration that V1 must complete.

**Confidence: MEDIUM** — twikit's impression/bookmark support is confirmed via official docs (readthedocs). Reliability against X's bot detection is a moving target for all cookie-based libraries; twikit 2.x has shown more stability than 1.x based on GitHub issue patterns.

### Fallback: twscrape

If twikit breaks (X API structure change), twscrape 0.17.0 is the fallback. It uses GraphQL which tends to be more stable than undocumented REST scraping. However it adds operational complexity (account pool management).

### What NOT to Use

| Library | Why Not |
|---------|---------|
| tweepy (official API) | Pay-per-usage; no free tier for impressions/bookmarks; current mirror_sync.py uses this and it is the root problem to solve |
| twitter-api-client | Last release April 2024, stale for cookie-based work; `tweet_stats()` fields unconfirmed |
| snscrape | Unmaintained since X blocked the free API in 2023; do not use |
| nitter | Public instances are mostly dead; unreliable for metric data |

---

### Python Runtime

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Python** | 3.11+ | Runtime | twikit requires 3.x; twscrape requires >=3.10; the existing codebase uses `str | None` union syntax and `list[dict]` which requires 3.10+. 3.11 is recommended for ~25% speed improvement over 3.10 and will be the standard until 3.13 stabilizes. |

### Local Data Storage

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **json (stdlib)** | Built-in | style_memory.json read/write | No dependency; already used in mirror_sync.py; `json.dump(..., ensure_ascii=False, indent=2)` handles Turkish characters correctly. Zero overhead. |
| **pathlib (stdlib)** | Built-in | File path management | Already used; cross-platform, handles Windows paths correctly |

**Why NOT a database for V1:**
- SQLite adds migration complexity and tooling overhead with no benefit at single-user scale
- JSON is directly human-readable and editable — important for a tool the owner debugs manually
- style_memory.json is the canonical output format; changing it to a DB would break the SKILL.md schema contract
- The evolution_log pattern in the schema is append-only; JSON handles this trivially

### CLI Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **argparse (stdlib)** | Built-in | CLI argument parsing | Already implemented in mirror_sync.py (`--dry-run`, `--since`, `--verbose`); zero dependency; sufficient for V1's simple argument surface. Do not add typer unless the CLI grows to 5+ commands. |
| **rich** | 14.3.3 | Terminal output formatting | Optional but recommended for sync reports and error display; the current `_print_sync_report()` uses raw `print()` which works but rich Tables would make output scannable. Add in V2 if needed. |
| **python-dotenv** | 1.2.2 | .env credential loading | Already a dependency in mirror_sync.py; handles BEARER_TOKEN, API keys, USER_ID; required for credential management regardless of which Twitter library is used. |

**Why NOT typer for V1:**
- Current argparse implementation already works
- typer requires Click as a dependency; adds ~3 packages for no V1 benefit
- Mirror only has 3 CLI flags; argparse is sufficient

### LLM Integration (Creator Skill)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **anthropic** | 0.85.0 | Primary LLM API (Claude) | Project already uses Claude (ciftcibahadir is a Claude user); SDK is current and actively maintained; claude-sonnet-4-6 is the recommended model for content generation tasks at this complexity level; supports streaming. |
| **openai** | 2.28.0 | Secondary LLM API (GPT-4) | Optional; include only if multi-model comparison is needed. OpenAI 2.28.0 uses the Responses API and Chat Completions API. |
| **litellm** | 1.82.3 | Unified LLM router (future) | If the Creator skill needs to support multiple models with one interface, litellm routes to 100+ providers with OpenAI-compatible syntax. Do NOT add in V1 — adds complexity. Add when the skill architecture requires model-switching. |
| **ollama** | 0.6.1 | Local model inference (future) | For privacy-sensitive analysis or offline operation. Requires Ollama server running locally. Useful for tone analysis (mirror) where tweet text should not leave local machine. Defer to post-V1. |

**V1 recommendation:** `anthropic` only. The Creator prompt documents describe what to build; when code is added, anthropic SDK is the first dependency to add.

### Environment / Configuration

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **python-dotenv** | 1.2.2 | .env file loading | Already in use; handles cookie credentials and (if needed) API keys |

---

## Installation

### V1 Mirror Core Dependencies (minimal, operational)

```bash
# Core — what mirror_sync.py needs after migration from tweepy to twikit
pip install twikit==2.3.3
pip install python-dotenv==1.2.2

# Remove tweepy (current dependency to be replaced)
pip uninstall tweepy
```

### Full V1 Development Setup

```bash
pip install twikit==2.3.3 python-dotenv==1.2.2

# For Creator skill when implemented
pip install anthropic==0.85.0
```

### Optional / Future

```bash
# Better terminal output
pip install rich==14.3.3

# Fallback Twitter library if twikit breaks
pip install twscrape==0.17.0

# Multi-LLM routing (post-V1)
pip install litellm==1.82.3

# Local inference (post-V1)
pip install ollama==0.6.1

# CLI upgrade (post-V1)
pip install typer==0.24.1
```

### requirements.txt (V1)

```
twikit==2.3.3
python-dotenv==1.2.2
anthropic==0.85.0
```

---

## Critical Migration: tweepy → twikit

The current `mirror_sync.py` uses `tweepy.Client` with official OAuth. This is the core problem to solve in V1.

### What Changes

| Aspect | Current (tweepy) | Target (twikit) |
|--------|-----------------|-----------------|
| Auth | BEARER_TOKEN + OAuth keys (4 values) | cookies.json (browser cookie export) |
| .env vars needed | BEARER_TOKEN, API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET | TWITTER_COOKIES_PATH or inlined cookies |
| Tweet object | `tweet.public_metrics["impression_count"]` | `tweet.view_count` |
| Bookmark access | `tweet.public_metrics["bookmark_count"]` (paid API only) | `tweet.bookmark_count` (free, cookie) |
| Rate limits | Official API limits (15 req/15min free) | Informal scraping limits (more lenient) |
| API stability | Stable (official) | Fragile (X can change internals) |
| Cost | Pay-per-usage (no free tier) | Free |
| Async model | Sync (tweepy.Client) | Async (asyncio required) |

### Async Migration Note

twikit is async-native. The current `mirror_sync.py` uses synchronous tweepy calls. Migration requires wrapping the sync flow in `asyncio.run()` and converting the main fetch function to `async def`.

---

## Prompt Engineering

No external framework is recommended for V1. The skill architecture is document-driven: each SKILL.md contains the system prompt directly. This is intentional — it keeps prompts editable without code changes and avoids framework lock-in.

**What NOT to adopt:**
- **LangChain**: Heavy dependency tree; prompt management via LCEL adds complexity for no V1 benefit. The pipeline (Miner → Lab → Mirror → Creator) is sequential and does not need an orchestration framework.
- **LlamaIndex**: Designed for RAG over document corpora; not relevant to this use case.
- **DSPy**: Prompt optimization framework; valuable in V2+ when optimizing for engagement rate outcomes, but premature in V1.
- **AutoGen / CrewAI**: Multi-agent orchestration; overkill when skills are prompt documents, not running agents.

**V1 pattern:** System prompt in SKILL.md → copy into Claude/GPT conversation → structured JSON output → saved to style_memory.json. No framework needed.

**V2 consideration:** When skills need to call each other programmatically (not manually), the lightweight pattern is direct `anthropic.Anthropic().messages.create()` calls with the system prompt loaded from the SKILL.md file. Still no framework.

---

## X API Situation (March 2026)

**The official X API no longer has a free tier.** As of early 2023, X deprecated the free API. The current model is pay-per-usage credits via console.x.com. Reading own tweet data (`non_public_metrics` which includes `impression_count`) requires paid access.

**What this means for Mirror:**
- Cookie-based scraping (twikit/twscrape) is the only zero-cost option
- `view_count` from twikit = what X shows as "impressions" in the UI — this is the right metric to use
- `impression_count` from `non_public_metrics` is slightly different (counts API-served impressions) but for the Mirror's purpose the difference is negligible
- Account ban risk: cookie-based scraping of your own account for your own data is low risk, but reading at high frequency could trigger bot detection

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|-----------|-------|
| twikit bookmark/view support | HIGH | Confirmed via official twikit readthedocs source code |
| twscrape bookmark/view support | HIGH | Confirmed via raw GitHub models.py source |
| twitter-api-client status | MEDIUM | PyPI shows April 2024 last release; stale but fields unverified |
| X API free tier status | HIGH | Official docs.x.com: pay-per-usage only, no free tier |
| anthropic/openai SDK versions | HIGH | Confirmed via PyPI |
| rich/typer/python-dotenv versions | HIGH | Confirmed via PyPI |
| twikit reliability against X bot detection | LOW | Moving target; community reports vary; no official data |

---

## Sources

- twikit Tweet class attributes: https://twikit.readthedocs.io/en/latest/twikit.html (confirmed `bookmark_count`, `view_count`)
- twikit PyPI: https://pypi.org/project/twikit/ (version 2.3.3, Feb 2025)
- twscrape models: https://raw.githubusercontent.com/vladkens/twscrape/main/twscrape/models.py (confirmed `bookmarkedCount`, `viewCount`)
- twscrape PyPI: https://pypi.org/project/twscrape/ (version 0.17.0, Apr 2025)
- twitter-api-client PyPI: https://pypi.org/project/twitter-api-client/ (version 0.10.22, Apr 2024)
- X API pricing: https://docs.x.com/ (pay-per-usage, no free tier confirmed)
- tweepy PyPI: https://pypi.org/project/tweepy/ (version 4.16.0)
- anthropic PyPI: https://pypi.org/project/anthropic/ (version 0.85.0, Mar 16 2026)
- openai PyPI: https://pypi.org/project/openai/ (version 2.28.0, Mar 13 2026)
- litellm PyPI: https://pypi.org/project/litellm/ (version 1.82.3, Mar 16 2026)
- ollama PyPI: https://pypi.org/project/ollama/ (version 0.6.1, Nov 2025)
- rich PyPI: https://pypi.org/project/rich/ (version 14.3.3, Feb 2026)
- typer PyPI: https://pypi.org/project/typer/ (version 0.24.1, Feb 2026)
- python-dotenv PyPI: https://pypi.org/project/python-dotenv/ (version 1.2.2, Mar 2026)
