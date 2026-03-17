# Phase 2: Mirror + Creator Integration — Research

**Researched:** 2026-03-17
**Domain:** Prompt engineering — AI skill documents (SKILL.md), JSON schema design, LLM hallucination guards
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MSKILL-01 | `the-mirror/SKILL.md` fully defines and explains the `style_memory.json` schema | style_memory.json DEFAULT_STYLE_MEMORY confirmed; hook_patterns/tone_profile/signature_expressions are stored as empty `{}` by mirror_sync.py — Mirror AI prompt must populate them by analyzing tweet_archive |
| MSKILL-02 | Mirror SKILL activation checks `last_synced_at` first and warns if stale | Staleness threshold decision documented below; warning placement defined |
| MSKILL-03 | Mirror SKILL produces a DNA Report from style_memory.json and can pass it to The Creator | DNA report schema already drafted in Mirror SKILL.md lines 481-614; needs to be formalized as dna_report.json and linked to the actual style_memory.json schema from mirror_sync.py |
| MSKILL-04 | Mirror SKILL issues minimum-data warning: "tahmini" flags required for <20 tweets | Threshold is tweet count in tweet_archive; where to inject the check is documented below |
| CRTR-01 | Creator SKILL.md can accept DNA Report as input and run Mod 1 (Brainstorm) | Creator already has Mod 1 but doesn't reference dna_report.json by name; update needed |
| CRTR-02 | Creator SKILL.md can run Mod 3 (Analysis): analyze given tweet or metric | Creator already has Mod 3 with structure; needs algorithm-signal rationale explicitly required |
| CRTR-03 | Creator output uses at least 1-2 terms from `signature_expressions` | Currently a general rule; needs to be a hard checklist item tied to dna_report.json `voice_dna.signature_terms` field |
| CRTR-04 | Creator provides CTA guidance in every proposal (required due to RT weakness) | Already enforced in system prompt; needs to be explicitly tied to `cta_guidance` block in DNA report |
| CRTR-05 | Creator applies "authenticity check": output must feel like it came from this user | Already exists as "DNA Testi" in pre-flight checklist; needs data-confidence warning gate for <20 tweets |
</phase_requirements>

---

## Summary

Phase 2 is **pure prompt engineering**. No Python code will be written. The deliverables are updated versions of two SKILL.md files: `skills/the-mirror/SKILL.md` (785 lines, needs additions) and `skills/the-creator/SKILL.md` (740 lines, needs additions).

The critical finding is that `mirror_sync.py` writes `hook_patterns`, `tone_profile`, and `signature_expressions` as **empty dicts `{}`** into `style_memory.json`. These fields are intended to be populated by The Mirror AI prompt when it analyzes the `tweet_archive`. The Mirror AI prompt must: (1) read the actual schema that mirror_sync.py produces, (2) derive the richer analysis fields from `tweet_archive`, (3) produce a `dna_report.json`, and (4) gate everything behind a data-sufficiency check.

The `dna_report.json` schema is already drafted in the Mirror SKILL.md (lines 481-614) but it was written before mirror_sync.py was implemented. It must be reconciled with the actual file schema Phase 1 produced.

**Primary recommendation:** Update Mirror SKILL.md with three new sections — schema reconciliation block, staleness check protocol, and data-sufficiency gate — then update Creator SKILL.md to hard-wire signature_expressions and CTA guidance to the incoming DNA report fields.

---

## What Phase 1 Actually Delivered

This is the ground truth the Mirror AI prompt must work from.

### Actual style_memory.json Schema (from mirror_sync.py DEFAULT_STYLE_MEMORY)

```json
{
  "userId": "string",
  "handle": "@string",
  "last_synced_at": "ISO-8601 or null",
  "last_sync_count": "integer",
  "version": "integer",
  "tweet_archive": [
    {
      "id": "string",
      "text": "string",
      "created_at": "ISO-8601",
      "hook_type": "enum: [soru, provokasyon, rakam_ile_bas, karsi_gorus, hikaye, liste_vaadi, cesur_iddia, diger]",
      "tone": "enum: [alaycı, heyecanli, egitici, samimi, profesyonel]",
      "format": "enum: [thread_basi, reply, tek_tweet]",
      "has_media": "boolean",
      "is_reply": "boolean",
      "metrics": {
        "view_count": "integer",
        "like_count": "integer",
        "reply_count": "integer",
        "retweet_count": "integer",
        "bookmark_count": "integer",
        "quote_count": "integer"
      },
      "engagement_rate": "float"
    }
  ],
  "high_performers": ["same shape as tweet_archive entries, engagement_rate >= 1.5x avg"],
  "performance_snapshot": {
    "total_impressions": "integer",
    "total_engagements": "integer",
    "avg_engagement_rate": "float",
    "verified_follower_ratio": "float or null",
    "top_signal_breakdown": {
      "likes": "integer",
      "replies": "integer",
      "retweets": "integer",
      "bookmarks": "integer",
      "quotes": "integer"
    },
    "bookmark_to_like_ratio": "float or null",
    "retweet_to_like_ratio": "float or null",
    "reply_to_impression_ratio": "float or null"
  },
  "hook_patterns": {},
  "tone_profile": {},
  "signature_expressions": {},
  "evolution_log": [
    {
      "date": "ISO-8601",
      "trigger": "string",
      "change_summary": "string",
      "version": "integer"
    }
  ]
}
```

**Critical gap:** `hook_patterns`, `tone_profile`, and `signature_expressions` are written as empty `{}` by mirror_sync.py. They are never populated by the Python script. The Mirror AI prompt must compute these by aggregating across `tweet_archive` at analysis time. This is a **fundamental design constraint** for MSKILL-01 and MSKILL-03.

### What mirror_sync.py Detects Per Tweet (Source for Mirror AI Analysis)

| Field | Values | Populated by |
|-------|--------|--------------|
| `hook_type` | soru, provokasyon, rakam_ile_bas, karsi_gorus, hikaye, liste_vaadi, cesur_iddia, diger | mirror_sync.py `detect_hook_type()` |
| `tone` | alaycı, heyecanli, egitici, samimi, profesyonel | mirror_sync.py `detect_tone()` |
| `format` | thread_basi, reply, tek_tweet | mirror_sync.py `detect_format()` |
| `engagement_rate` | float (engagements / view_count) | mirror_sync.py `compute_engagement_rate()` |

The Mirror AI prompt aggregates these to fill `hook_patterns` (avg engagement per hook_type), `tone_profile` (avg engagement per tone), and `signature_expressions` (term frequency + engagement correlation from text analysis).

---

## Architecture Patterns

### Pattern 1: The Mirror Activation Flow

When the Mirror AI skill is activated (user starts a conversation or requests a DNA report), it executes in this order:

```
Step 1: Check last_synced_at → staleness warning (if stale)
Step 2: Check tweet count in tweet_archive → data-sufficiency gate
Step 3: Aggregate hook_patterns from tweet_archive
Step 4: Aggregate tone_profile from tweet_archive
Step 5: Derive signature_expressions from text analysis of high_performers
Step 6: Produce dna_report.json
Step 7: Pass DNA report to The Creator
```

This flow must be explicit in the updated Mirror SKILL.md system prompt.

### Pattern 2: dna_report.json as Intermediary

`dna_report.json` is the **contract** between Mirror and Creator. It must:
- Be self-contained (Creator needs no other file)
- Include a `data_confidence` field (HIGH / LOW / TAHMINI) so Creator can gate its output
- Reference the `style_memory_version` so it is traceable
- Include the pre-computed `voice_dna.signature_terms` list so Creator can enforce CRTR-03 without reading style_memory.json

### Pattern 3: Creator DNA Report Input Protocol

The Creator must be updated so that when a DNA report is provided:
1. It reads `data_confidence` first — if LOW or TAHMINI, it prepends the insufficient-data warning to every output
2. It reads `voice_dna.signature_terms` — the pre-flight DNA Test checklist item becomes: "Did I use at least 1-2 terms from this exact list?"
3. It reads `cta_guidance.recommended_ctas` — instead of using generic CTAs, it pulls the user-specific ones from the report

---

## Standard Stack

This phase has no code dependencies. The "stack" is the existing file system.

| Artifact | Current State | Phase 2 Target |
|----------|--------------|----------------|
| `skills/the-mirror/SKILL.md` | 785 lines — full analysis prompt, DNA report schema draft, no staleness/data-gate logic | Add: schema reconciliation block, staleness check, data-sufficiency gate, dna_report.json output instructions |
| `skills/the-creator/SKILL.md` | 740 lines — 5 modes, quality checklist, system prompt — no reference to dna_report.json by name | Add: DNA report input protocol, hard signature_expressions enforcement, data-confidence warning passthrough |
| `skills/the-mirror/style_memory.json` | Written by mirror_sync.py — hook_patterns/tone_profile/signature_expressions are empty `{}` | Not changed by Phase 2; Mirror AI must work around this |
| `skills/the-mirror/dna_report.json` | Does not exist yet | Mirror SKILL produces this as output |

---

## Key Decisions Required

These are the **open questions that must be resolved in the PLAN** before writing begins.

### Decision 1: Staleness Threshold for last_synced_at

**Question:** How old does `last_synced_at` have to be before Mirror warns the user?

**Analysis:**
- The user (@ciftcibahadir) currently tweets with moderate frequency (AI content niche, ~3/day max by rule)
- Style drift is slow — tone and hook patterns change over weeks, not days
- But the CTA weakness analysis depends on fresh retweet data which changes with each tweet batch
- Excessively short threshold (1 day) creates warning fatigue
- Excessively long threshold (30 days) means stale data silently degrades quality

**Recommendation:** 7-day threshold. This aligns with the "weekly content planning" model and gives the data-freshness guarantee needed for engagement rate comparisons. The warning should be visible but non-blocking.

**Warning format:**
```
SYNC UYARISI: style_memory.json son {N} gün önce güncellendi ({last_synced_at}).
Daha doğru bir DNA raporu için önce mirror_sync.py çalıştırın:
  python skills/the-mirror/mirror_sync.py
DNA raporu mevcut veriyle üretilmeye devam ediliyor...
```

### Decision 2: Data-Sufficiency Threshold

**Requirement:** MSKILL-04 says <20 tweets triggers "tahmini" flags.

**How to count:** Use `len(tweet_archive)` from style_memory.json. This is the number of synced tweets, not total tweets ever. A user who just set up the mirror might have fewer than 20.

**Implementation in Mirror SKILL:**
- Count tweets in tweet_archive at the start of DNA report generation
- If count < 20: set `data_confidence: "TAHMINI"` in the DNA report header
- Add explicit field: `insufficient_data_warning: "Tweet arşivi {count} tweet içeriyor (<20). Tüm tahminler az veriyle yapılmıştır."`
- Every analysis section header gets `[TAHMINİ]` prefix when in this mode

**Implementation in Creator SKILL:**
- When DNA report contains `data_confidence: "TAHMINI"`, prepend this block to EVERY output:
```
⚠️ VERİ GÜVENİLİRLİĞİ DÜŞÜK
Bu analiz yetersiz tweet verisiyle (< 20 tweet) üretilmiştir.
Öneriler tahmine dayalıdır. Daha fazla veri için mirror_sync.py çalıştırın.
```
- The authenticity check (CRTR-05) in this mode must say: "Bu içerik yeterli veri olmadan üretilmiştir — kullanmadan önce kendi tarzınıza uygunluğunu gözden geçirin."

### Decision 3: dna_report.json Complete Schema

The Mirror SKILL.md already has a DNA report draft (lines 481-614). It needs to be updated to include:
- `data_confidence` field (required for CRTR-05 gate)
- `insufficient_data_warning` field (required for MSKILL-04)
- `sync_status` field (required for MSKILL-02)
- Reconciliation with the actual hook_type enum values from mirror_sync.py (the draft uses slightly different names)

**Reconciled hook_type enum** (from mirror_sync.py `detect_hook_type()`):
```
soru, provokasyon, rakam_ile_bas, karsi_gorus, hikaye, liste_vaadi, cesur_iddia, diger
```

The SKILL.md draft uses `kisisel_itiraf` and `provokasyon` — `kisisel_itiraf` is not in mirror_sync.py. The Mirror AI must use the enum values mirror_sync.py actually writes.

**Reconciled tone enum** (from mirror_sync.py `detect_tone()`):
```
alaycı, heyecanli, egitici, samimi, profesyonel
```

The SKILL.md draft uses `alaycı_satirik`, `profesyonel_analitik`, `samimi_kisisel`, `eğitici_açıklayıcı`, `motivasyonel`. These do not match. The Mirror AI must use the values mirror_sync.py writes — it is reading `tweet_archive` entries with these exact strings.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Aggregating hook_type performance | A separate Python script to compute hook averages | Mirror AI reads tweet_archive directly and computes averages inline in the prompt | This is a prompt-only phase; the AI can aggregate small JSON lists |
| Signature expression extraction | A TF-IDF or NLP pipeline | Mirror AI uses the `high_performers` list (already computed by mirror_sync.py) to identify recurring terms in high-engagement tweets | mirror_sync.py already identifies high_performers; AI can do frequency analysis on their text fields |
| Staleness check logic | Python code comparing datetime | A natural language instruction in the system prompt: "read last_synced_at, compare to today's date, warn if > 7 days" | This is executed by the AI at conversation start, not as code |
| Data confidence gate | A schema validator | A conditional block in the SKILL.md system prompt: "count tweet_archive length; if < 20, set tahmini mode" | Same reasoning — prompt-level logic, not code |

---

## Common Pitfalls

### Pitfall 1: Mirror AI Hallucinating Signature Expressions

**What goes wrong:** When the Mirror AI doesn't have enough tweet data, it may invent signature expressions that sound plausible ("pipeline", "agent") but don't appear in the user's actual tweets.

**Why it happens:** The AI fills silence with plausible content. Without the `<20 tweet` gate, it has no instruction to flag uncertainty.

**How to avoid:** The MSKILL-04 "tahmini" gate must be the FIRST check in the Mirror AI flow, before any analysis. If triggered, every expression must be annotated with `[TAHMINİ]`.

**Warning signs:** DNA report shows "signature_expressions" but tweet_archive has very few entries or entries are all from the same day.

### Pitfall 2: Creator Ignoring DNA Report Data_Confidence

**What goes wrong:** Creator generates content confidently even when DNA report has `data_confidence: "TAHMINI"`, omitting the warning that the user needs to see.

**How to avoid:** The `data_confidence` check must be the FIRST step in the Creator's DNA report processing block, with the warning prepended unconditionally before any content.

### Pitfall 3: Hook Type Enum Mismatch

**What goes wrong:** Mirror AI generates a DNA report that references hook types like `kisisel_itiraf` or `motivasyonel` (from the old SKILL.md draft), but tweet_archive entries have `cesur_iddia` and `egitici` (from mirror_sync.py). The aggregation produces zero results for most categories.

**How to avoid:** The updated Mirror SKILL.md must document the exact enum values from mirror_sync.py and tell the AI to use these values when reading tweet_archive. Old SKILL.md draft values must be removed.

### Pitfall 4: signature_expressions as Empty Dict

**What goes wrong:** Mirror AI is told to use `style_memory.signature_expressions` to find recurring terms, but this field is `{}` (empty) because mirror_sync.py never populates it. The AI gets no terms.

**How to avoid:** The Mirror SKILL.md must tell the AI to **compute** signature_expressions by reading the `text` fields of `high_performers` entries (not from the empty `signature_expressions` field). The pattern: find terms that recur across 3+ high-performer tweets.

### Pitfall 5: CTA Guidance Disconnected from DNA Report

**What goes wrong:** Creator generates CTAs that are generic ("RT edersen daha fazla kişiye ulaşır") rather than pulling the user-specific CTAs from `cta_guidance.recommended_ctas` in the DNA report.

**How to avoid:** The Creator DNA report processing block must explicitly pull `cta_guidance.recommended_ctas` and use those exact texts, with a fallback to generic CTAs only if the field is empty.

---

## dna_report.json Complete Field Specification

This is the authoritative schema the planner should use when writing SKILL.md updates.

```json
{
  "report_id": "string (e.g. mirror-ciftcibahadir-{yyyymmdd})",
  "generated_at": "ISO-8601 timestamp",
  "user_handle": "@string",
  "style_memory_version": "integer",
  "report_type": "enum: [full_dna, quick_summary, trend_filtered]",

  "sync_status": {
    "last_synced_at": "ISO-8601 or null",
    "days_since_sync": "integer or null",
    "is_stale": "boolean (true if days_since_sync > 7)",
    "stale_warning": "string or null (human-readable warning message)"
  },

  "data_confidence": "enum: [HIGH, LOW, TAHMINI]",
  "tweet_count": "integer (len(tweet_archive))",
  "insufficient_data_warning": "string or null (populated when data_confidence == TAHMINI)",

  "identity_summary": {
    "one_line_voice": "string",
    "core_niches": ["string"],
    "audience_type": "string",
    "creator_archetype": "string"
  },

  "performance_context": {
    "current_avg_engagement_rate": "float",
    "benchmark_comparison": "string",
    "strongest_content_signal": "string",
    "growth_bottleneck": "string",
    "quick_win_opportunity": "string"
  },

  "voice_dna": {
    "signature_terms": ["string (computed from high_performers text, 10-15 terms)"],
    "avoid_terms": ["string"],
    "sentence_rhythm": "string",
    "punctuation_style": "string",
    "opening_formula": "string",
    "closing_formula": "string",
    "sample_authentic_sentences": ["string (3-5 from real high-performer tweets)"]
  },

  "hook_arsenal": {
    "best_hook_type": "string (hook_type with highest avg engagement_rate in tweet_archive)",
    "hook_type_performance": {
      "soru": "float (avg engagement_rate across tweets with hook_type=soru)",
      "provokasyon": "float",
      "rakam_ile_bas": "float",
      "karsi_gorus": "float",
      "hikaye": "float",
      "liste_vaadi": "float",
      "cesur_iddia": "float",
      "diger": "float"
    },
    "top_performing_hooks": [
      {
        "hook_text": "string (first sentence of tweet)",
        "hook_type": "string",
        "engagement_rate": "float",
        "reusable_pattern": "string"
      }
    ],
    "hook_templates_for_creator": ["string"]
  },

  "tone_profile": {
    "dominant_tone": "string (tone enum value with highest tweet count)",
    "highest_performing_tone": "string (tone with highest avg engagement_rate)",
    "tone_performance": {
      "alaycı": "float",
      "heyecanli": "float",
      "egitici": "float",
      "samimi": "float",
      "profesyonel": "float"
    }
  },

  "format_playbook": {
    "go_to_format": "string",
    "bookmark_format": "string",
    "viral_format": "string",
    "reply_magnet_format": "string",
    "formats_to_avoid": ["string"],
    "format_recommendations": [
      {
        "format": "string",
        "use_case": "string",
        "expected_primary_signal": "string"
      }
    ]
  },

  "cta_guidance": {
    "current_cta_deficit": "boolean",
    "retweet_rate_problem": "boolean",
    "recommended_ctas": [
      {
        "cta_text": "string",
        "best_placement": "string",
        "target_signal": "string"
      }
    ],
    "cta_frequency_guide": "string"
  },

  "weak_points_briefing": {
    "critical_weaknesses": [
      {
        "issue": "string",
        "diagnosis": "string",
        "fix_for_creator": "string"
      }
    ]
  },

  "creator_instructions": {
    "must_do": ["string"],
    "must_avoid": ["string"],
    "tone_calibration": "string",
    "authenticity_check": "string"
  }
}
```

Note: `trend_integration_guide`, `optimal_timing`, `length_preference`, `niche_connections`, `successful_formats` fields from the original draft are omitted from the Phase 2 schema. They are useful but not required for MSKILL-01 through CRTR-05 and add complexity without covering a requirement. The planner can include them as optional enhancements but should not block any plan on them.

---

## Verification Strategy for Prompt-Based Skills

Since these are SKILL.md prompt documents (not Python code), standard pytest-based testing does not apply. The verification strategy must be **snapshot-based + manual conversation testing**.

### Verification Approach

| Requirement | Test Type | Method | Pass Criterion |
|-------------|-----------|--------|----------------|
| MSKILL-01 | Structural | Read SKILL.md: find section "style_memory.json Şeması" that documents the actual fields from mirror_sync.py DEFAULT_STYLE_MEMORY | Section exists and contains `tweet_archive`, `hook_patterns`, `tone_profile`, `signature_expressions`, `last_synced_at` with correct types |
| MSKILL-02 | Structural | Read SKILL.md: find staleness check instructions that reference `last_synced_at` and a day threshold | Section exists, threshold is 7 days, warning text format is present |
| MSKILL-03 | Structural + Manual | Read SKILL.md: dna_report.json output section exists with all required fields. Manual: feed a sample style_memory.json to the Mirror AI, verify the DNA report is produced | SKILL.md has output section; manual run produces report with hook_arsenal and tone_profile populated |
| MSKILL-04 | Structural + Manual | Read SKILL.md: find data-sufficiency gate (<20 tweet check). Manual: feed a style_memory with 5 tweets, verify all sections labeled [TAHMINİ] | Gate logic present in SKILL.md; manual run produces warnings |
| CRTR-01 | Structural + Manual | Read Creator SKILL.md: DNA report input protocol section exists. Manual: provide DNA report, request Mod 1, verify output contains at least 1 term from voice_dna.signature_terms | DNA report input section present; manual output contains signature term |
| CRTR-02 | Structural + Manual | Read Creator SKILL.md: Mod 3 analysis output format requires "algorithm-signal rationale" section. Manual: provide a tweet, verify analysis output contains X algorithm signal name | Mod 3 output template has algorithm signal field; manual run produces signal names |
| CRTR-03 | Structural | Read Creator SKILL.md: pre-flight DNA Test checklist item explicitly references `voice_dna.signature_terms` from the DNA report | Checklist item says: "At least 1-2 terms from `voice_dna.signature_terms` used?" |
| CRTR-04 | Structural | Read Creator SKILL.md: pre-flight algorithm test includes CTA check tied to `cta_guidance.recommended_ctas` | Checklist references the CTA field by name |
| CRTR-05 | Structural + Manual | Read Creator SKILL.md: `data_confidence: TAHMINI` branch in DNA report processing produces warning on every output. Manual: provide DNA report with data_confidence=TAHMINI, verify warning appears | Warning logic present in SKILL.md; manual run shows warning prefix on all outputs |

### Test Fixtures for Manual Verification

The planner should specify two fixture files to be created as part of Phase 2:

**Fixture A: `tests/fixtures/sample_style_memory_full.json`**
A style_memory.json with 25+ tweet_archive entries, populated performance_snapshot, varied hook_types and tones. Used to verify normal (HIGH confidence) flow.

**Fixture B: `tests/fixtures/sample_style_memory_sparse.json`**
A style_memory.json with 5 tweet_archive entries (below the 20 threshold). Used to verify MSKILL-04 and CRTR-05 warning gates.

These fixtures live under `skills/the-mirror/tests/fixtures/` to match the existing test directory structure from Phase 1.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already installed from Phase 1) |
| Config file | `skills/the-mirror/tests/` (existing directory) |
| Quick run command | `pytest skills/the-mirror/tests/ -v` (existing 15 tests — Phase 2 adds prompt structure tests) |
| Full suite command | `pytest skills/the-mirror/tests/ skills/the-creator/tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MSKILL-01 | SKILL.md documents actual style_memory schema | structural/snapshot | `pytest skills/the-mirror/tests/test_skill_structure.py::test_schema_documented -x` | ❌ Wave 0 |
| MSKILL-02 | SKILL.md contains staleness check with 7-day threshold | structural/snapshot | `pytest skills/the-mirror/tests/test_skill_structure.py::test_staleness_check_present -x` | ❌ Wave 0 |
| MSKILL-03 | SKILL.md dna_report output section exists with required fields | structural/snapshot | `pytest skills/the-mirror/tests/test_skill_structure.py::test_dna_report_fields -x` | ❌ Wave 0 |
| MSKILL-04 | SKILL.md data-sufficiency gate (<20 tweet) present | structural/snapshot | `pytest skills/the-mirror/tests/test_skill_structure.py::test_data_sufficiency_gate -x` | ❌ Wave 0 |
| CRTR-01 | Creator SKILL.md DNA report input protocol section present | structural/snapshot | `pytest skills/the-creator/tests/test_skill_structure.py::test_dna_input_protocol -x` | ❌ Wave 0 |
| CRTR-02 | Creator Mod 3 output format includes algorithm-signal rationale field | structural/snapshot | `pytest skills/the-creator/tests/test_skill_structure.py::test_mod3_algorithm_signal -x` | ❌ Wave 0 |
| CRTR-03 | Creator pre-flight checklist references signature_terms by name | structural/snapshot | `pytest skills/the-creator/tests/test_skill_structure.py::test_signature_terms_enforcement -x` | ❌ Wave 0 |
| CRTR-04 | Creator pre-flight checklist references cta_guidance field by name | structural/snapshot | `pytest skills/the-creator/tests/test_skill_structure.py::test_cta_guidance_reference -x` | ❌ Wave 0 |
| CRTR-05 | Creator SKILL.md has TAHMINI/data_confidence warning gate | structural/snapshot | `pytest skills/the-creator/tests/test_skill_structure.py::test_data_confidence_gate -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest skills/the-mirror/tests/ skills/the-creator/tests/ -v`
- **Per wave merge:** Full suite above
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `skills/the-mirror/tests/test_skill_structure.py` — covers MSKILL-01, 02, 03, 04
- [ ] `skills/the-creator/tests/__init__.py` — package marker for new test directory
- [ ] `skills/the-creator/tests/test_skill_structure.py` — covers CRTR-01, 02, 03, 04, 05
- [ ] `skills/the-mirror/tests/fixtures/sample_style_memory_full.json` — manual verification fixture
- [ ] `skills/the-mirror/tests/fixtures/sample_style_memory_sparse.json` — sparse data fixture

Note: The test approach for prompt-structure tests is string-search (grep) against the SKILL.md file content. Tests read the SKILL.md file and assert that specific strings or sections are present. This is fast (< 1 second), deterministic, and requires no LLM calls. It verifies that the plan was executed (the prompt was written) without testing LLM behavior.

---

## What Already Exists vs What Needs to Change

### Mirror SKILL.md (785 lines) — Existing Strengths

The file already contains:
- A full `Analiz Promptu` section that tells the AI how to analyze tweets (lines 244-284)
- A draft DNA report format in `Çıktı: DNA Raporu` (lines 481-614)
- A `@ciftcibahadir için Örnek DNA Raporu` (partial) (lines 616-690)
- A `Sistem Promptu` (lines 694-728)
- Update protocols, global trend filter, example scenarios

**What it does NOT have:**
1. A section that documents the actual `style_memory.json` schema as produced by mirror_sync.py (with `tweet_archive` per-tweet structure, actual hook_type/tone enum values)
2. `last_synced_at` staleness check with a defined threshold and warning format
3. `tweet_count < 20` data-sufficiency gate with `[TAHMINİ]` flagging
4. Instructions to compute `hook_patterns` and `tone_profile` by aggregating `tweet_archive` entries (since the fields are empty `{}` in the actual file)
5. Instructions to compute `signature_expressions` from `high_performers` text (not from the empty field)

### Creator SKILL.md (740 lines) — Existing Strengths

The file already contains:
- All 5 production modes (Brainstorm, Thread, Analysis, Suggestion, Comparison)
- A pre-flight checklist with DNA Test and Algorithm Test
- System prompt with detailed CTA rules and anti-pattern list
- A complete example pipeline output

**What it does NOT have:**
1. A `DNA Report Input Protocol` section: named steps for how to process an incoming `dna_report.json`
2. A `data_confidence` check at the start of processing
3. Explicit reference to `voice_dna.signature_terms` in the DNA Test checklist (currently says "İmza ifadelerden en az biri kullanıldı mı? (Mirror raporuna göre)" — needs to reference the exact field name)
4. Explicit reference to `cta_guidance.recommended_ctas` in the Retweet CTA checklist
5. A `TAHMINI / insufficient data` warning block for low-confidence DNA reports
6. Mod 3 output format that explicitly requires an "X Algoritması Sinyal Gerekçesi" section

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Mirror AI received tweet list from user manually | Mirror AI reads structured `style_memory.json` produced by mirror_sync.py | Removes manual copy-paste; DNA analysis is deterministic from real engagement data |
| Creator received general "Mirror DNA" conceptually | Creator receives `dna_report.json` with specific fields | Removes ambiguity; signature_terms and cta_guidance become hard checklist items |
| No data-quality gate | `data_confidence: TAHMINI` flag when < 20 tweets | Prevents hallucinated confident analysis on sparse data |
| Staleness handled implicitly | Explicit `last_synced_at` check with 7-day threshold and warning text | User always knows when to re-sync before running analysis |

---

## Open Questions

1. **Who writes `dna_report.json` to disk?**
   - What we know: The Mirror AI skill produces the DNA report as a JSON block in its output
   - What's unclear: Does the user save it manually, or is there a convention for where it lives?
   - Recommendation: For Phase 2, the DNA report is produced as a formatted JSON code block in the conversation. The user copies it to `skills/the-mirror/dna_report.json` if they want to persist it. The Creator can receive it inline in the conversation or as a pasted file. This keeps Phase 2 entirely prompt-based.

2. **What happens when style_memory.json doesn't exist yet?**
   - What we know: mirror_sync.py creates it on first run
   - What's unclear: What should Mirror AI say if the user hasn't run mirror_sync.py yet?
   - Recommendation: Mirror SKILL.md must include a branch: "If style_memory.json is not provided, prompt the user to run mirror_sync.py first and provide the output."

3. **Exact tweet count for the data-confidence threshold**
   - What we know: MSKILL-04 says < 20 tweets = "tahmini"
   - What's unclear: Is 20 the right number? The current @ciftcibahadir seed has 48 verified tweets.
   - Recommendation: Use 20 as specified. It covers the "Seçenek C: Hızlı başlangıç (5-10 tweet)" scenario in the existing SKILL.md and provides a clear threshold.

---

## Sources

### Primary (HIGH confidence)
- `skills/the-mirror/mirror_sync.py` — lines 58-100 (DEFAULT_STYLE_MEMORY schema), lines 395-484 (actual enum values for hook_type/tone/format), lines 601-658 (performance_snapshot computation) — read directly
- `skills/the-mirror/SKILL.md` — lines 1-785 (full content, existing DNA report draft) — read directly
- `skills/the-creator/SKILL.md` — lines 1-740 (full content) — read directly
- `.planning/REQUIREMENTS.md` — MSKILL-01 through CRTR-05 requirement definitions — read directly
- `.planning/phases/01-mirror-foundation/01-VERIFICATION.md` — Phase 1 completion evidence — read directly

### Secondary (MEDIUM confidence)
- `decision.md` — architectural decisions (multi-skill pipeline, Mirror data isolation) — read directly
- `.planning/ROADMAP.md` — Phase 2 success criteria — read directly

---

## Metadata

**Confidence breakdown:**
- Actual style_memory.json schema: HIGH — read directly from mirror_sync.py DEFAULT_STYLE_MEMORY and run_sync() function
- Hook_type/tone/format enum values: HIGH — read directly from detect_hook_type(), detect_tone(), detect_format() in mirror_sync.py
- dna_report.json schema design: HIGH — synthesized from existing Mirror SKILL.md draft + Phase 1 schema gaps
- Staleness threshold (7 days): MEDIUM — reasonable recommendation, no user preference stated; can be changed in planning
- Verification approach (structural tests): HIGH — consistent with Phase 1 test patterns
- Empty hook_patterns/tone_profile/signature_expressions gap: HIGH — confirmed by reading DEFAULT_STYLE_MEMORY

**Research date:** 2026-03-17
**Valid until:** 2026-04-17 (stable domain — prompt engineering on fixed schema)
