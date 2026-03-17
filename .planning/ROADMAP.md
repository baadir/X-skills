# Roadmap: TwitterYoldas — Multi-Skill Agent Ekosistemi

## Overview

Three phases deliver the V1 agent ecosystem. Phase 1 repairs the only existing code (`mirror_sync.py`) and hardens the data foundation that every downstream skill depends on. Phase 2 activates the Mirror AI layer and the Creator skill, completing the core product loop: tweet data in, voice-authentic content suggestions out. Phase 3 finalises the Miner and Lab prompt documents and populates the algorithm reference library, closing all 31 V1 requirements.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Mirror Foundation** - Migrate mirror_sync.py to twikit, harden style_memory.json, add .gitignore (completed 2026-03-17)
- [x] **Phase 2: Mirror + Creator Integration** - Finalise Mirror SKILL.md, build DNA report pipeline, activate Creator Mod 1 + Mod 3 (completed 2026-03-17)
- [x] **Phase 3: Miner, Lab + References** - Complete Miner and Lab SKILL.md documents, populate algorithm references and decision log (completed 2026-03-17)

## Phase Details

### Phase 1: Mirror Foundation
**Goal**: A working, crash-safe `mirror_sync.py` that fetches the user's own tweets with accurate impression and bookmark data via twikit, stores them in a validated `style_memory.json`, and is protected against data loss and accidental credential exposure
**Depends on**: Nothing (first phase)
**Requirements**: SYNC-01, SYNC-02, SYNC-03, SYNC-04, SYNC-05, SYNC-06, SYNC-07, SYNC-08, SYNC-09, MEM-01, MEM-02, MEM-03, MEM-04, MEM-05, REFS-05
**Success Criteria** (what must be TRUE):
  1. Running `python mirror_sync.py` against @ciftcibahadir fetches tweets with non-zero `view_count` and `bookmark_count` (twikit, not tweepy)
  2. `style_memory.json` is written atomically — interrupting the script mid-run leaves the previous file intact, not corrupted
  3. A second sync run fetches only tweets newer than `last_synced_at` — no full re-fetch
  4. `style_memory.json` contains `high_performers`, `hook_patterns`, `tone_profile`, `performance_snapshot`, and `evolution_log` fields populated with real data
  5. `cookies.json` and `.env` do not appear in `git status` (`.gitignore` blocks them)
**Plans**: 4 plans

Plans:
- [x] 01-01-PLAN.md — Test scaffold (Wave 0 stubs) + .gitignore — REFS-05
- [x] 01-02-PLAN.md — Async fetch layer rewrite (twikit auth, incremental pagination, rate limiting) — SYNC-01, SYNC-02, SYNC-03, SYNC-07
- [x] 01-03-PLAN.md — Memory management layer (atomic write, evolution_log, rolling window, seed data, categorization adaptation) — SYNC-04, SYNC-05, SYNC-06, MEM-01–MEM-05
- [x] 01-04-PLAN.md — Async orchestration wiring + CLI + live validation checkpoint — SYNC-08, SYNC-09

### Phase 2: Mirror + Creator Integration
**Goal**: The Mirror AI prompt produces a structured DNA report from `style_memory.json` and the Creator skill uses that report to generate voice-authentic content proposals via Mod 1 (Brainstorm) and Mod 3 (Analysis), with guards against LLM hallucination on sparse data
**Depends on**: Phase 1
**Requirements**: MSKILL-01, MSKILL-02, MSKILL-03, MSKILL-04, CRTR-01, CRTR-02, CRTR-03, CRTR-04, CRTR-05
**Success Criteria** (what must be TRUE):
  1. Activating the Mirror skill with `style_memory.json` present produces a `dna_report.json` with hook pattern performance and tone profile populated from real engagement data
  2. Activating the Mirror skill when `last_synced_at` is stale produces a visible sync warning before generating the DNA report
  3. Running Creator Mod 1 (Brainstorm) with the DNA report produces at least one content proposal that includes a term from `signature_expressions` and a CTA
  4. Running Creator Mod 3 (Analysis) on a provided tweet produces a structured critique with algorithm-signal rationale
  5. When `style_memory.json` contains fewer than 20 tweets, every Creator output is flagged with a data-confidence warning ("tahmini" / "insufficient data")
**Plans**: 3 plans

Plans:
- [ ] 02-01-PLAN.md — Wave 0 test stubs + fixtures (9 RED tests for MSKILL-01–04 + CRTR-01–05) — MSKILL-01, MSKILL-02, MSKILL-03, MSKILL-04, CRTR-01, CRTR-02, CRTR-03, CRTR-04, CRTR-05
- [ ] 02-02-PLAN.md — Mirror SKILL.md: schema reconciliation + staleness check + data-sufficiency gate + DNA report schema — MSKILL-01, MSKILL-02, MSKILL-03, MSKILL-04
- [ ] 02-03-PLAN.md — Creator SKILL.md: DNA report input protocol + Mod 3 algorithm signal + checklist hardening — CRTR-01, CRTR-02, CRTR-03, CRTR-04, CRTR-05

### Phase 3: Miner, Lab + References
**Goal**: All prompt-only skill documents (Miner and Lab) are complete and internally consistent, algorithm reference files are current and comprehensive, and the decision and strategy documents reflect all architectural choices made to date
**Depends on**: Phase 2
**Requirements**: MLSKILL-01, MLSKILL-02, MLSKILL-03, REFS-01, REFS-02, REFS-03, REFS-04
**Success Criteria** (what must be TRUE):
  1. `the-miner/SKILL.md` contains a named list of target accounts, the collection session JSON schema, and a priority score formula — no Python code present
  2. `the-lab/SKILL.md` contains the JSONL batch prompt schema, 6-dimension classification system, and S/A/B/C tier definitions — no Python code present
  3. `references/x_algorithm_signals.md` lists all 19 signal weights including the author diversity decay formula and Phoenix architecture notes
  4. `decision.md` and `strateji.md` are current: every key decision from Phases 1-3 is logged with date and rationale
**Plans**: 4 plans

Plans:
- [ ] 03-01-PLAN.md — the-miner/SKILL.md: Hedef Hesap Profili section (bookmark/like > 0.3, dinamik keşif) + prompt-only marker — MLSKILL-01, MLSKILL-03
- [ ] 03-02-PLAN.md — the-lab/SKILL.md: prompt-only marker (JSONL/6-dim/S-tier already present) — MLSKILL-02, MLSKILL-03
- [ ] 03-03-PLAN.md — tweet_datasets.md: twikit 2.3.3 section + tweepy deprecation; strateji.md: 6.3 Mirror storage decision closed — REFS-02, REFS-04
- [ ] 03-04-PLAN.md — decision.md: Phase 1 + Phase 2 decision blocks backfilled — REFS-03

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Mirror Foundation | 4/4 | Complete    | 2026-03-17 |
| 2. Mirror + Creator Integration | 3/3 | Complete    | 2026-03-17 |
| 3. Miner, Lab + References | 5/5 | Complete   | 2026-03-17 |
