# Project Research Summary

**Project:** TwitterYoldas — Multi-Skill Twitter/X Growth Agent
**Domain:** AI-powered personal Twitter growth tool with style memory, algorithm-aware content suggestion, and multi-skill agent pipeline
**Researched:** 2026-03-17
**Confidence:** MEDIUM (stack HIGH, architecture HIGH, features MEDIUM, pitfalls MEDIUM)

---

## Executive Summary

TwitterYoldas is a local-first, CLI-based AI content assistant for a single Twitter/X user. It is built around four interconnected "skills" — The Miner (viral data collection), The Lab (pattern classification), The Mirror (personal style analysis), and The Creator (content generation) — that communicate exclusively through JSON files on disk. The correct mental model is a file-mediated pipeline, not a framework or platform: each skill is an independent Python script or prompt document that reads its upstream input file and writes its own output file. This architecture is appropriate for V1 because two of the four skills (Miner and Lab) are prompt-only in V1, with no code to couple. The pipeline's critical path runs through The Mirror: without a populated and accurate `style_memory.json`, The Creator produces generic content that destroys the product's core value proposition.

The highest-impact stack decision is migrating the existing `mirror_sync.py` from tweepy (official OAuth, pay-per-usage) to twikit 2.3.3 (cookie-based, free). The X API no longer has a free tier; `impression_count` and `bookmark_count` are paywalled behind the Basic tier ($100/month). twikit exposes `view_count` and `bookmark_count` on the Tweet object at no cost — these map directly to what X shows users as "impressions" in the UI, making them the correct metric for Mirror's purposes. The migration requires converting the current synchronous tweepy call pattern to async/await, but the functional scope is narrow: fetch own tweets, extract six engagement signals, write `style_memory.json`.

The dominant risk is not technical complexity — it is data quality. Cookie-based scraping can trigger account suspension (Pitfall C1), keyword-based hook classification systematically misfires on Turkish/English bilingual text (Pitfall M1), and the Creator will hallucinate personalized-sounding statistics when Mirror data is sparse (Pitfall M3). Every phase recommendation below is structured to catch these data quality failures early, before they propagate into Creator outputs that users will trust.

---

## Key Findings

### Recommended Stack

The X API free tier is gone. Cookie-based scraping via twikit 2.3.3 is the only zero-cost path to `view_count` (impressions) and `bookmark_count`. twikit is preferred over twscrape because it is designed for single-user own-data access rather than multi-account scraping at scale; it is async-native and actively maintained (Feb 2025). The fallback is twscrape 0.17.0, which uses GraphQL and is more resilient to X internal API changes but adds account pool management complexity.

The remaining stack is deliberately minimal: Python 3.11+, `json` and `pathlib` from stdlib for data storage, `argparse` for CLI (already implemented), and `python-dotenv` for credentials. For the Creator skill, the `anthropic` SDK (0.85.0) is the only LLM dependency needed in V1. No orchestration framework (LangChain, LlamaIndex, CrewAI) is recommended — the pipeline is sequential, the handoffs are file-based, and the prompts live in SKILL.md documents editable without code changes.

**Core technologies:**
- **twikit 2.3.3**: Primary Twitter data access — cookie-based, exposes `view_count` and `bookmark_count`, async-native, actively maintained; replaces tweepy which requires paid API for these fields
- **Python 3.11+**: Runtime — required for `str | None` union syntax already in codebase; 25% speed improvement over 3.10
- **python-dotenv 1.2.2**: Credential management — already in use for `.env` loading; handles cookie paths and any API keys
- **anthropic 0.85.0**: LLM integration — Claude SDK for Creator skill content generation; direct `messages.create()` calls, no framework wrapper
- **json + pathlib (stdlib)**: Data persistence — JSON is human-readable, git-diffable, editable; correct for V1 at single-user scale with tweet archives under 50K records
- **twscrape 0.17.0**: Fallback scraping library — GraphQL-based, more stable against X API structure changes; add only if twikit breaks

### Expected Features

The core differentiator of this product is that it is the only tool in the market that builds an engagement-weighted, negatively-reinforced, versioned style memory from the user's own published content. Commercial tools (Hypefury, TweetHunter, Taplio) do shallow style capture via text field or sample sentences. Mirror's `hook_type_performance` dict maps 8 hook archetypes to per-user engagement rates — evidence-based personalization, not vibes-based.

**Must have (table stakes):**
- Tweet analytics (impressions, engagement rate, likes, RTs, replies, bookmarks) — baseline user expectation; Mirror schema covers all six signals
- Best time to post recommendations — expected by every growth tool user; already in Mirror's `optimal_posting_times` schema
- Thread composition — Creator's Mod 2 covers this; absence would make the writing assistant feel incomplete
- Engagement metric breakdown per tweet — native X Analytics provides this; Mirror must match it
- Character count enforcement — Creator's rules enforce 280/250-character limits per tweet

**Should have (differentiators):**
- Personal voice/style memory with engagement weighting — the core product; `style_memory.json` schema fully defined
- Hook pattern analysis by performance per user — maps 8 hook archetypes to actual per-user engagement rates, not global benchmarks
- Weak pattern diagnosis — proactive identification of what the user does that hurts them; rare in commercial tools
- Algorithm-signal-aware content scoring — Creator's 7-component output format with per-signal rationale (dwell time, DM share, RT likelihood)
- Author diversity enforcement — hard cap at 3 original tweets/day based on X's decay formula; almost no competitor does this explicitly
- Multi-mode generation (Brainstorm / Thread / Analysis / Weekly Plan / Compare) — Creator's 5 modes covering different content jobs
- Trend-to-voice compatibility filtering — global viral patterns filtered through the user's DNA before recommendation

**Defer (v2+):**
- Content scheduling and posting automation — adds X ToS risk and API complexity; out of V1 scope; must be stated upfront
- Follower count and growth tracking — expected for SaaS but not for CLI V1
- Creator Mod 4 (Weekly Plan) and Mod 5 (Compare) — useful but require established style_memory; build after Mod 1 proven
- Miner live data automation — Creator works without it; Lab/Mirror path is the V1 critical path
- Multi-user support — V1 is single-user (@ciftcibahadir); isolation architecture already designed for future expansion
- Multi-LLM routing (litellm) and local inference (ollama) — add post-V1 when privacy or model-switching is needed

**Anti-features to avoid at all costs:**
- Generic AI-generated content not filtered through Mirror DNA — destroys the product's core value
- Engagement bait prompts — algorithm deprioritizes; destroys professional credibility in technical niches
- Posting volume above 3 originals/day — X's author diversity decay formula actively penalizes this
- Any SaaS dashboard aesthetic — target user is technical, privacy-conscious, open-source oriented

### Architecture Approach

The system is a file-mediated pipeline where each skill is an independent unit (SKILL.md prompt document + optional Python script + owned data files) and skills communicate exclusively through timestamped JSON files written to disk. No skill imports another skill's code. The Mirror is the only hybrid skill (Python script + AI prompt layer) — its code layer writes `style_memory.json` and its prompt layer reads it to produce `dna_report.json`. The Creator is the synthesis node: it waits for `dna_report.json` from Mirror and `lab_output/*.json` from Lab, with Miner collection as optional enrichment. All V1 storage is JSON files; SQLite is deferred until `tweet_archive` exceeds 50K records or Lab produces 50+ session files.

**Major components:**
1. **The Mirror (hybrid: mirror_sync.py + prompt)** — Owns `style_memory.json` and `dna_report.json`; fetches user's own tweets via twikit; classifies hook types and tone; runs Mirror AI prompt to produce DNA report for Creator
2. **The Lab (prompt-only in V1)** — Classifies Miner's viral tweet collection across 6 dimensions; produces `lab_output/run_*.json` consumed by Creator (and optionally Mirror's trend filter)
3. **The Miner (prompt-only in V1)** — Collects raw viral tweets, arXiv papers, Kaggle datasets; produces `data/collections/session_*.json` as Lab's input
4. **The Creator (prompt-only)** — Synthesizes Lab patterns + Mirror DNA + optional Miner collection into voice-matched content proposals; 5 modes; outputs to `output/content_YYYYMMDD.md`

### Critical Pitfalls

1. **Cookie-based scraping triggers account ban (C1)** — The user's own Twitter account (@ciftcibahadir) is used for scraping; a ban destroys the audience the tool is supposed to grow. Mitigate: rate-limit aggressively (1 request per 3-5 minutes, never in loops without jitter), use `--since` flag for incremental syncs, maintain fallback to official X archive ZIP download.

2. **Tweepy free tier silently returns zero impressions (C2)** — The current `mirror_sync.py` uses tweepy; `impression_count` is unavailable on the free tier and returns null without error, making `engagement_rate = 0.0` for all tweets and corrupting Mirror's entire DNA. This is the root problem to solve in Phase 1: migrate to twikit before locking the `style_memory.json` schema.

3. **style_memory.json single point of failure (C3)** — A crash mid-write (power loss, Ctrl+C, disk full) corrupts the only copy of all accumulated style data. Mitigate: atomic writes via write-to-temp-then-`os.replace()`; rolling backup to `style_memory.backup.json`; cap `tweet_archive` at 500 recent tweets with annual archival.

4. **LLM hallucinates engagement data on sparse Mirror input (M3)** — When fewer than 20 tweets are synced, Creator fills statistical gaps with plausible-sounding but fabricated multipliers. User makes real posting decisions on invented personalization; trust collapses when they check actual analytics. Mitigate: include `sample_size` alongside every performance figure; add `data_confidence` summary block at top of every DNA report; Creator system prompt must say "fewer than 5 examples = 'insufficient data', not an estimate."

5. **Algorithm diversity penalty backfires (M2)** — Creator optimizes individual tweet quality but ignores that X's author diversity decay formula penalizes consecutive same-author appearances. Posting 3 threads in one day gets second and third threads near-zero reach. Mitigate: hardcode daily post limit guidance (max 2 original posts for accounts under 10K followers) into Creator system prompt from day one; one thread = one posting event.

---

## Implications for Roadmap

Based on the feature dependency graph, architecture build order, and pitfall phase mappings, three phases are recommended for V1.

### Phase 1: Mirror Foundation

**Rationale:** `mirror_sync.py` is the only existing code and is currently broken for its primary purpose (impression and bookmark data unavailable via tweepy free tier). Everything downstream — Mirror DNA, Creator content — depends on accurate engagement signal data in `style_memory.json`. This must be fixed and hardened before any other skill is built. Phase 1 is also where the two highest-severity pitfalls (C1 account ban, C2 silent data corruption) must be addressed.

**Delivers:** A working, hardened `mirror_sync.py` that fetches the user's real tweet data with accurate `view_count` and `bookmark_count` via twikit; a validated `style_memory.json` with engagement-weighted hook patterns and tone profiles; atomic write safety; rolling archive with size cap.

**Addresses:** Tweet analytics (table stakes), best time to post (table stakes), engagement metric breakdown (table stakes), style memory foundation (core differentiator), hook pattern analysis (core differentiator)

**Avoids:** C1 (account ban via cookie scraping), C2 (silent impression data corruption), C3 (style_memory data loss), M1 (keyword misclassification — implement confidence flags), M5 (unbounded archive growth), N2 (.env key exposure)

**Research flag:** Needs phase-level research — twikit async migration pattern and X cookie auth reliability need validation against live account before implementation.

---

### Phase 2: Mirror Analysis + Creator Integration

**Rationale:** With real engagement data in `style_memory.json`, the Mirror AI prompt layer (DNA report generation) and the Creator skill can be validated against actual performance data. This phase proves the core product loop: tweet data in, voice-authentic content suggestions out. It must come after Phase 1 because Creator quality is directly proportional to Mirror data richness — running Creator on a sparse or corrupted style_memory produces hallucinated personalization.

**Delivers:** A working Mirror AI prompt that produces a structured `dna_report.json`; Creator Mod 1 (Brainstorm) and Mod 3 (Analysis/Rewrite) producing voice-matched content; minimum sample size guards against LLM hallucination; data freshness warnings in Creator output.

**Uses:** anthropic SDK (0.85.0) for Creator generation; existing `style_memory.json` and `dna_report.json` schemas established in Phase 1

**Implements:** Mirror prompt layer (DNA report generation); Creator synthesis node (Mod 1 and Mod 3)

**Avoids:** M3 (LLM hallucination on sparse data), M2 (diversity penalty — hardcode daily limit in Creator from day one), N4 (voice loss under too many constraints — prioritize signature_expressions over structural constraints), C4 (stale data context mismatch — include `last_synced_at` in every Creator invocation)

**Research flag:** Standard patterns for anthropic SDK usage; no additional research needed. Creator prompt engineering for constraint prioritization may need iteration — plan 1-2 revision cycles.

---

### Phase 3: Miner + Lab Integration

**Rationale:** The Miner and Lab skills are prompt-only in V1 and are explicitly optional enrichment for the Creator (Creator works without them). They come last because their value depends on Creator baseline being proven first; feeding stale or low-quality Lab patterns into a Creator that isn't producing good output without them compounds the problem rather than solving it.

**Delivers:** Validated Miner collection schema (one session JSON per run); validated Lab classification schema (6-dimension analysis with timestamps); Creator Mod 4 (Weekly Plan) and Mod 2 (Thread) enabled with Lab pattern context; pipeline manifest tracking per-skill timestamps.

**Avoids:** M4 (pattern staleness — `valid_until` timestamps on every Lab pattern entry, 30-day TTL), C4 (context staleness across skills — pipeline manifest with per-skill last-run timestamps), Anti-Pattern 4 (Miner/Lab code never enters the open-source Mirror/Creator repository)

**Research flag:** Miner data sources (HuggingFace, arXiv, X viral content) may need research on rate limits and schema variance. Lab batch prompt calibration requires human review of classification accuracy before automation. Mark both as needing phase-level research.

---

### Phase Ordering Rationale

- **Data dependency drives order:** Nothing works without accurate `style_memory.json`. Fixing the tweepy→twikit migration is Phase 1 by necessity, not preference.
- **Validation before integration:** Each skill is validated with real data before the next skill depends on it. This prevents compounding errors (bad Lab data + bad Mirror data = Creator failure with no clear root cause).
- **Pitfall front-loading:** The two critical pitfalls (account ban, silent data corruption) are in Phase 1 because they are irreversible — a corrupted style_memory or a banned account cannot be fixed by later phases.
- **Open-source boundary enforced from the start:** Miner/Lab code stays prompt-only (V1) and in a separate conceptual track from Mirror/Creator. The open-source release boundary (Mirror + Creator only) is never violated.

### Research Flags

Phases needing deeper research during planning:
- **Phase 1:** twikit async migration specifics; X cookie auth rate limit behavior; atomic write patterns on Windows (target platform is Windows 11 per env context)
- **Phase 3:** Miner data source API limits (arXiv, HuggingFace); Lab classification calibration methodology; pipeline orchestration manifest schema design

Phases with standard patterns (skip additional research):
- **Phase 2:** anthropic SDK usage is well-documented; Creator prompt engineering follows established few-shot patterns; file I/O handoff between Mirror and Creator is straightforward JSON read

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | twikit bookmark/view support confirmed via official readthedocs; X API paid-only status confirmed via docs.x.com; all library versions confirmed via PyPI |
| Features | MEDIUM | Project-internal features (SKILL.md schemas) are HIGH confidence; competitive landscape analysis (Hypefury, TweetHunter, etc.) is MEDIUM — derived from training data through August 2025, not live verification |
| Architecture | HIGH | Derived from actual project documents and existing `mirror_sync.py` code; file-mediated pattern follows from project constraints (prompt-only skills cannot call functions) |
| Pitfalls | MEDIUM | Code-analysis-based pitfalls (C2, C3, M1) are HIGH confidence — identified from direct `mirror_sync.py` review; cookie scraping ban risk (C1) is MEDIUM — community reports, no official X data; LLM hallucination behavior (M3, N4) is HIGH confidence from prompt engineering literature |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **twikit reliability against X bot detection:** LOW confidence. No official data; community reports vary. Validate with a low-volume test run against @ciftcibahadir before committing to the twikit migration. Document fallback path to twscrape explicitly in Phase 1 implementation.
- **X API free tier field availability (current state):** MEDIUM confidence. X API policy changes frequently. Verify current field availability at developer.twitter.com before Phase 1 implementation — the research reflects state as of March 2026 but confirmation during implementation is required.
- **Mirror keyword classification accuracy on @ciftcibahadir's actual tweet corpus:** Cannot be assessed without running the existing `mirror_sync.py` on real data. Run a sample of 50 tweets through the classifier and manually validate output before trusting `hook_type_performance` as Creator input.
- **Creator constraint saturation threshold:** The research documents the risk (Pitfall N4) but the optimal constraint count per Creator invocation cannot be determined without empirical testing. Plan 2-3 prompt revision cycles in Phase 2 budget.

---

## Sources

### Primary (HIGH confidence)
- `skills/the-mirror/mirror_sync.py` — Direct code review; basis for Pitfalls C2, C3, M1, N1, N2, N3
- `skills/the-mirror/SKILL.md`, `skills/the-creator/SKILL.md`, `skills/the-lab/SKILL.md`, `skills/the-miner/SKILL.md` — Project feature definitions, schema contracts, build order
- `references/x_algorithm_signals.md` — Author diversity penalty formula, 19 signal weights
- twikit readthedocs (https://twikit.readthedocs.io/en/latest/twikit.html) — `bookmark_count`, `view_count` field confirmation
- X API docs (https://docs.x.com/) — Pay-per-usage, no free tier for `impression_count`/`bookmark_count`
- PyPI: twikit 2.3.3, twscrape 0.17.0, anthropic 0.85.0, python-dotenv 1.2.2, rich 14.3.3 — version confirmations

### Secondary (MEDIUM confidence)
- `.planning/PROJECT.md`, `strateji.md`, `decision.md` — Project scope, V1 constraints, business rationale
- twscrape GitHub (https://raw.githubusercontent.com/vladkens/twscrape/main/twscrape/models.py) — `bookmarkedCount`, `viewCount` field confirmation
- Competitive landscape (Hypefury, TweetHunter, Taplio, Typefully, Postwise, Buffer, FeedHive) — Training data through August 2025; not live-verified

### Tertiary (LOW confidence)
- Cookie-based scraping account ban patterns — Community reports from twikit/twitter-api-client GitHub issues; behavior is a moving target; validate during Phase 1 implementation

---

*Research completed: 2026-03-17*
*Ready for roadmap: yes*
