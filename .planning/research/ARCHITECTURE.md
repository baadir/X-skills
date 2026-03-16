# Architecture Patterns

**Project:** TwitterYoldas — Multi-Skill Agent Ecosystem
**Researched:** 2026-03-17
**Confidence:** HIGH (derived from actual skill documents, existing code, and established Python/CLI patterns)

---

## Recommended Architecture

### Mental Model: File-Mediated Pipeline

Each skill is an independent Python module (or a prompt document with no code). Skills communicate exclusively through JSON files written to disk. No skill calls another skill's code directly. The pipeline is pull-based at each stage: every skill reads its upstream input file and writes its own output file.

```
[Global Sources]
  HuggingFace / X API / arXiv / Kaggle
        |
        v
  [ THE MINER ]  (prompt-only in V1, Python script in V2)
  Writes: data/collections/session_YYYYMMDD_NNN.json
        |
        v
  [ THE LAB ]    (prompt-only in V1, Python + Batch API in V2)
  Reads:  data/collections/session_YYYYMMDD_NNN.json
  Writes: data/lab_output/run_YYYYMMDD_NNN.json
        |
        +------------------------------+
        |                              |
        v                              v
  [ THE MIRROR ]               [ THE CREATOR ]
  Reads: lab_output (optional)  Reads: lab_output (primary)
  Reads: user's own tweets       Reads: mirror/style_memory.json
  Writes: mirror/style_memory.json   Reads: miner collection (optional)
          mirror/dna_report.json  Writes: output/content_YYYYMMDD.md
        |
        v
  [ THE CREATOR ] <-- also reads dna_report.json from Mirror
  (synthesizes Lab + Mirror + optional Miner)
```

### Clarification on The Creator's Position

The SKILL.md files show The Creator receives from three sources: The Lab, The Mirror, and The Miner. The Creator is not strictly "after" The Mirror in a linear chain — it is the synthesis node. The correct mental model is:

```
Miner  ──► (collection JSON)  ──►┐
Lab    ──► (lab_output JSON)  ──►┤──► Creator ──► content output
Mirror ──► (dna_report JSON)  ──►┘
```

Mirror and Lab run independently and in parallel. Creator waits for both.

---

## Component Boundaries

| Component | Type | Responsibility | Reads | Writes | Communicates With |
|-----------|------|---------------|-------|--------|-------------------|
| The Miner | Prompt-only (V1) / Python (V2) | Collect raw viral tweet data, arXiv papers, Kaggle datasets | X API, arXiv, Kaggle | `data/collections/session_*.json` | The Lab (downstream) |
| The Lab | Prompt-only (V1) / Python + Batch API (V2) | Classify tweets across 6 dimensions, produce pattern report | `data/collections/session_*.json` | `data/lab_output/run_*.json` | The Mirror (optional), The Creator (primary) |
| The Mirror | Prompt + Python (`mirror_sync.py`) | Sync user's own tweets, build `style_memory`, produce DNA report | X API (own tweets), `lab_output` (trend filter) | `mirror/style_memory.json`, `mirror/dna_report.json` | The Creator (downstream) |
| The Creator | Prompt-only | Synthesize Lab + Mirror + Miner into content proposals | `lab_output/*.json`, `mirror/dna_report.json`, `collections/*.json` (optional) | `output/content_YYYYMMDD.md` | User (terminal output) |

### Strict Boundary Rules

- Skills never import or call each other's Python code. A skill boundary is a file boundary.
- The Miner produces one JSON file per session. The Lab consumes it. No direct function call between them.
- The Mirror's `mirror_sync.py` writes `style_memory.json` independently of Lab. The Mirror's AI prompt layer reads both its own `style_memory.json` and Lab's `lab_output` as separate reads.
- The Creator is pure prompt in V1 — it reads files given to it by the user in the conversation context. No automation layer yet.

---

## Data Flow

### V1 (Current State — Prompt-Driven, Manual Handoffs)

```
Step 1 (Manual): User runs The Miner prompt → pastes output → saves to
                 data/collections/session_YYYYMMDD_001.json

Step 2 (Manual): User pastes collection JSON into The Lab prompt →
                 Lab produces classified JSON → saves to
                 data/lab_output/run_YYYYMMDD_001.json

Step 3 (Automated): mirror_sync.py runs automatically (cronjob or manual):
                    python skills/the-mirror/mirror_sync.py
                    → reads X API → writes
                    skills/the-mirror/style_memory.json

Step 3b (Manual): User runs The Mirror prompt with style_memory.json context →
                  Mirror produces dna_report.json →
                  skills/the-mirror/dna_report.json

Step 4 (Manual): User runs The Creator prompt with:
                 - lab_output JSON pasted in
                 - dna_report.json pasted in
                 - (optional) collection JSON for recency
                 → Creator produces content proposals in markdown
```

### V2 (Target — Automated Orchestration)

```
$ python twitter_yoldas.py --mode daily

1. Miner.run(mode="quick") → data/collections/session_today.json
2. Lab.run(session_today.json) → data/lab_output/run_today.json
3. mirror_sync.py --incremental → mirror/style_memory.json (updated)
4. Mirror.generate_dna_report(style_memory, lab_output) → mirror/dna_report.json
5. Creator.synthesize(lab_output, dna_report, [collection]) → output/content_today.md
6. print summary to terminal
```

### Data Schemas (What Flows Between Skills)

| File | Schema Owner | Key Fields | Consumer |
|------|-------------|-----------|---------|
| `collections/session_*.json` | Miner | `session_id`, `tweets[]`, `arxiv_papers[]`, `kaggle_datasets[]`, `collection_stats` | Lab |
| `lab_output/run_*.json` | Lab | `pipeline_run_id`, `tweets[].lab_analysis`, `stats`, pattern report sections | Mirror (trend filter), Creator |
| `mirror/style_memory.json` | Mirror sync (`mirror_sync.py`) | `tweet_archive[]`, `high_performers[]`, `performance_snapshot`, `hook_patterns`, `tone_profile` | Mirror prompt, Creator (via dna_report) |
| `mirror/dna_report.json` | Mirror prompt | `identity_summary`, `voice_dna`, `format_playbook`, `hook_arsenal`, `cta_guidance`, `creator_instructions` | Creator |
| `output/content_YYYYMMDD.md` | Creator | Markdown with multiple content versions, engagement analysis, posting schedule | User |

---

## "Skill" Abstraction in a Local Python CLI Context

### What a Skill Is

In this project, a "skill" is not a Python class or module — it is a named capability with three layers:

```
Skill = [SKILL.md] + [optional Python script(s)] + [data files it owns]
```

| Layer | Purpose | Example |
|-------|---------|---------|
| `SKILL.md` | The system prompt + schema documentation + usage contract | The Lab's 6-dimension classification schema |
| Python script(s) | Automated data I/O that cannot be done via prompt alone | `mirror_sync.py` for tweet fetching |
| Owned data files | The skill's output that downstream skills consume | `style_memory.json`, `lab_output/*.json` |

### Prompt-Only vs Code-Based Skills

| Skill | V1 Implementation | Rationale |
|-------|-------------------|-----------|
| The Miner | Prompt-only | Data collection is semi-manual; API key management is separate; V1 validates the schema first |
| The Lab | Prompt-only | Batch API calls are expensive to automate without validation; quality score calibration needs human review first |
| The Mirror | Hybrid: Python (`mirror_sync.py`) + Prompt | Tweet fetching requires code (rate limits, pagination, auth); the analysis/DNA generation layer remains AI prompt |
| The Creator | Prompt-only | Output is a creative judgment call; automation here adds no value in V1 |

### How Prompt Skills Interface with Code Skills

The Mirror is the only hybrid skill. Its interface contract:

```
mirror_sync.py OUTPUT (code layer) ──► style_memory.json
                                            │
                                            ▼
                            The Mirror PROMPT reads style_memory.json
                            as context, produces dna_report.json
                                            │
                                            ▼
                            The Creator reads dna_report.json
```

The code layer and the prompt layer do not call each other. They share the file `style_memory.json` as the handoff artifact. This is clean: the Python script has no AI dependency; the prompt has no code dependency.

---

## Storage Decision: JSON Files vs SQLite

### Recommendation: JSON Files for V1, SQLite Optional for V2+

**Use JSON files throughout V1.** The reasoning is evidence-based from the project's actual constraints:

| Criterion | JSON Files | SQLite |
|-----------|-----------|--------|
| Complexity for V1 | None — already working (`style_memory.json` exists) | Requires schema migrations, ORM or raw SQL, connection management |
| Open-source friendliness | Files are human-readable, git-diffable, editable by users | Binary format; requires tooling to inspect |
| Query needs (V1) | None — full file load is fine at <10K tweets | Needed at >100K tweets or for complex cross-session queries |
| Concurrency | Not needed — single-user, single-process | SQLite handles it but adds unnecessary surface area |
| Backup/portability | `cp style_memory.json backup/` | Requires `sqlite3 .dump` or file copy |
| Privacy (open-source users) | Users know exactly what is stored | Black box to non-technical users |
| Migration path | Easy: add fields to JSON, update reader | Requires ALTER TABLE or migration scripts |

**When to switch to SQLite:** When `tweet_archive` in `style_memory.json` exceeds ~50K records (file load becomes slow) or when cross-session Lab output queries are needed (e.g., "find all tweets labeled FOMO + Thread across 30 sessions").

**Concrete rule:** V1 stays JSON. V2 milestone evaluation: if `tweet_archive` >10K entries OR if Lab produces >50 session files, introduce SQLite for Miner/Lab data only. Keep `style_memory.json` as JSON always (it is user-facing, open-source contract).

### Storage Layout Decision

The `mirror_sync.py` already establishes the correct pattern — `style_memory.json` lives next to the script. Generalizing this:

```
skills/
  the-mirror/
    style_memory.json       # Mirror owns this
    dna_report.json         # Mirror produces this for Creator
    mirror_sync.py
    .env                    # API keys, never committed

data/                       # Shared pipeline data, NOT committed (gitignore)
  collections/
    session_20260317_001.json
    session_20260318_001.json
  lab_output/
    run_20260317_001.json
    run_20260318_001.json

output/                     # Final content proposals
  content_20260317.md
  content_20260318.md
```

---

## Skill-to-Skill Communication: JSON Files vs Direct API Calls vs Message Queue

### Recommendation: JSON Files (Filesystem-Mediated)

For this specific project, the choice is clear. Evaluate each option:

**Direct API calls (one skill calls another's HTTP endpoint):**
- Requires running servers, port management, networking
- V1 has no servers — Miner and Lab are prompts, Mirror is a CLI script
- Eliminated: adds infrastructure complexity with zero benefit for a local single-user tool

**Message queue (Redis, RabbitMQ, Kafka):**
- Appropriate when skills run as persistent daemons handling real-time streams
- V1 runs skills on demand (user triggers them)
- Eliminated: massive operational overhead for a tool that runs a few times per day

**JSON files (filesystem mediated):**
- Zero infrastructure: files are always available
- Inspectable: user can read any intermediate result
- Debuggable: if Creator produces wrong output, open `dna_report.json` and inspect
- Compatible with prompt-only skills: an LLM conversation can "read" a JSON file pasted in
- Resume-able: each skill writes its output before the next reads; a failure mid-pipeline can be resumed from the last successful file
- Auditable: `git add data/lab_output/run_*.json` gives a history of what data drove what content

**Verdict:** JSON files are the correct choice for V1 and likely V2. Revisit only if skills become real-time services (V3+, SaaS context).

---

## Build Order (Dependency Graph)

The build order follows the data dependency, not the pipeline execution order:

```
Layer 0 — Foundation (no dependencies)
  [A] mirror_sync.py API integration
      → Establishes: tweet fetching, style_memory.json schema, incremental sync

Layer 1 — Skill Schemas (depend on Layer 0 for data shape)
  [B] The Miner SKILL.md
      Depends on: knowledge of what Lab needs (schema contract)
  [C] The Lab SKILL.md
      Depends on: Miner output schema (already defined)
  [D] The Mirror SKILL.md
      Depends on: style_memory.json schema (written by mirror_sync.py)

Layer 2 — Integration (depend on Layer 1)
  [E] The Creator SKILL.md
      Depends on: Lab output schema, Mirror DNA report schema

Layer 3 — Automation (depend on Layer 2)
  [F] Orchestration script (V2): twitter_yoldas.py
      Depends on: all schemas stabilized, all skills validated manually
```

### Concrete Build Order for V1

1. **mirror_sync.py** — Build and validate first. This is the only code that exists. Get it working with the real API. Validate `style_memory.json` output shape matches what Mirror SKILL.md expects.

2. **The Mirror SKILL.md** — Finalize (already written). Use the real `style_memory.json` from step 1 to validate the prompt produces a correct `dna_report.json`.

3. **The Miner SKILL.md** — Finalize the output schema (collection JSON). Run the prompt manually, save the output. This is the input for Lab.

4. **The Lab SKILL.md** — Finalize. Run against a real Miner collection. Validate that `lab_analysis` fields and pattern report match what Creator expects.

5. **The Creator SKILL.md** — Finalize. Run with real Lab output + real Mirror DNA report. Validate all 5 modes work.

6. **End-to-end test** — Run full pipeline once, manually, with real data for @ciftcibahadir.

---

## Folder Structure Recommendation

```
twitter-yoldas/                     # project root
│
├── skills/
│   ├── the-miner/
│   │   ├── SKILL.md                # Prompt + schema doc
│   │   └── .env.example            # env var template
│   │
│   ├── the-lab/
│   │   └── SKILL.md                # Prompt + batch schema
│   │
│   ├── the-mirror/
│   │   ├── SKILL.md                # Prompt + DNA report schema
│   │   ├── mirror_sync.py          # Code layer (tweet fetching)
│   │   ├── style_memory.json       # Mirror's owned data (gitignored)
│   │   ├── dna_report.json         # Mirror's output for Creator (gitignored)
│   │   └── .env                    # API keys (gitignored)
│   │
│   └── the-creator/
│       └── SKILL.md                # Prompt + 5 modes
│
├── data/                           # Pipeline intermediates (gitignored)
│   ├── collections/                # Miner output
│   │   └── session_YYYYMMDD_NNN.json
│   └── lab_output/                 # Lab output
│       └── run_YYYYMMDD_NNN.json
│
├── output/                         # Creator output (gitignored or committed)
│   └── content_YYYYMMDD.md
│
├── references/
│   ├── x_algorithm_signals.md
│   └── tweet_datasets.md
│
├── .planning/
│   └── research/
│
├── .gitignore                      # Must exclude: .env, style_memory.json,
│                                   # data/, output/ (personal data)
├── strateji.md
└── decision.md
```

### Gitignore Rules (Critical for Open-Source Layer)

```gitignore
# Personal data — never commit
skills/the-mirror/style_memory.json
skills/the-mirror/dna_report.json
skills/the-mirror/.env
data/
output/

# API keys
.env
*.env

# Python
__pycache__/
*.pyc
.venv/
```

The SKILL.md files ARE committed — they are the open-source product. The data files are NOT committed — they contain personal tweet history.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Skills Calling Each Other's Code Directly

**What:** `from the_lab import process_collection` inside Creator code.
**Why bad:** Creates a hard dependency chain. If Lab changes its interface, Creator breaks. In V1, Lab has no importable code anyway.
**Instead:** Always mediate through JSON files. Each skill reads its input from disk.

### Anti-Pattern 2: Monolithic "Pipeline" Class

**What:** One Python class that instantiates all four skills and orchestrates them internally.
**Why bad:** Merges the closed-source Miner/Lab with the open-source Mirror/Creator. Cannot publish Mirror without publishing Miner.
**Instead:** Keep skills as independent modules/directories. The open-source release is `skills/the-mirror/` and `skills/the-creator/` — nothing else.

### Anti-Pattern 3: Storing style_memory in a Shared Database

**What:** Mirror writes to a central SQLite or Postgres that Creator reads directly.
**Why bad:** Requires users to run a database server; breaks the "clone and run" promise; personal data is harder to inspect/delete.
**Instead:** `style_memory.json` is a flat file owned by The Mirror. Creator reads it via the `dna_report.json` that Mirror produces.

### Anti-Pattern 4: Putting Miner/Lab Code in the Open-Source Repo

**What:** Publishing the Miner scraper or Lab batch processor code in the same repo as Mirror/Creator.
**Why bad:** Destroys the strategic moat. The hybrid architecture (closed factory + open user layer) only works if Miner/Lab code stays private.
**Instead:** Keep Miner/Lab as prompt documents only (V1). When V2 adds code, it goes in a separate private repository. The SaaS API is the only public interface to Miner/Lab data.

### Anti-Pattern 5: One Giant style_memory.json Per User

**What:** Accumulating all tweet history, all DNA versions, all Lab outputs into a single growing file.
**Why bad:** File grows unbounded; JSON load time increases; mixing raw archive data with derived analysis obscures what each skill actually owns.
**Instead:** Separate concerns:
- `style_memory.json` — raw tweet archive + computed snapshot (Mirror sync owns this)
- `dna_report.json` — derived analysis report (Mirror prompt produces this fresh each run)
- `lab_output/run_*.json` — Lab analysis per session (Lab owns these, timestamped)

---

## Scalability Considerations

| Concern | V1 (single user, <500 tweets) | V2 (single user, 5K tweets) | V3 (multi-user SaaS) |
|---------|------------------------------|----------------------------|----------------------|
| Storage | JSON files, <5MB total | JSON files still fine; archive may hit 2MB | SQLite per user or Postgres |
| style_memory size | ~50KB | ~500KB (manageable) | N/A — each user has their own file |
| Lab output history | 5-10 files, manual cleanup | 50-100 files; add session index file | Database-backed |
| Creator input assembly | Manual paste | Automated file resolution by date | API-mediated |
| Mirror sync | Manual or cronjob | Cronjob (Windows Task Scheduler) | Background worker per user |
| Miner/Lab isolation | Prompt-only; complete isolation | Private repo + API | SaaS API with API key auth |

---

## Confidence Assessment

| Decision | Confidence | Basis |
|----------|-----------|-------|
| File-mediated communication | HIGH | Derived from project constraints: prompt-only skills cannot call functions; existing `mirror_sync.py` already uses files |
| JSON over SQLite for V1 | HIGH | `style_memory.json` already exists and works; project is single-user, <1K tweets in V1 |
| Skill-as-directory abstraction | HIGH | Already established by project structure; each skill has its own folder |
| Folder layout recommendation | MEDIUM | Extends current structure logically; no existing orchestration to break |
| Build order | HIGH | Derived from data dependency graph; Layer 0 (mirror_sync.py) is the only existing code |
| SQLite migration threshold | MEDIUM | 10K-50K tweet threshold is a reasonable engineering heuristic; may need revision based on actual file sizes |

---

## Sources

- `skills/the-miner/SKILL.md` — Miner output schema, API integration spec
- `skills/the-lab/SKILL.md` — Lab classification schema, batch prompt structure
- `skills/the-mirror/SKILL.md` — style_memory schema, DNA report format, update protocol
- `skills/the-creator/SKILL.md` — Synthesis logic, 5 modes, input requirements
- `skills/the-mirror/mirror_sync.py` — Existing code layer; establishes file I/O patterns, incremental sync, `style_memory.json` schema
- `strateji.md` — Hybrid model (closed Miner/Lab, open Mirror/Creator), business rationale
- `.planning/PROJECT.md` — V1 scope, constraints, key decisions
