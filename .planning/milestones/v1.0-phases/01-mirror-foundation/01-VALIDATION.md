---
phase: 1
slug: mirror-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23+ |
| **Config file** | `skills/the-mirror/tests/conftest.py` — Wave 0 creates this |
| **Quick run command** | `pytest skills/the-mirror/tests/ -x -q` |
| **Full suite command** | `pytest skills/the-mirror/tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest skills/the-mirror/tests/ -x -q`
- **After every plan wave:** Run `pytest skills/the-mirror/tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | SYNC-01 | unit | `pytest tests/test_auth.py::test_client_init -x` | Wave 0 | ⬜ pending |
| 1-01-02 | 01 | 1 | SYNC-01 | unit | `pytest tests/test_auth.py::test_client_init -x` | ✅ | ⬜ pending |
| 1-01-03 | 01 | 1 | SYNC-02 | unit | `pytest tests/test_categorize.py::test_tweet_fields -x` | ✅ | ⬜ pending |
| 1-01-04 | 01 | 1 | SYNC-03 | unit | `pytest tests/test_fetch.py::test_incremental_cutoff -x` | ✅ | ⬜ pending |
| 1-01-05 | 01 | 1 | SYNC-04 | unit | `pytest tests/test_categorize.py::test_hook_types -x` | ✅ | ⬜ pending |
| 1-01-06 | 01 | 1 | SYNC-05 | unit | `pytest tests/test_atomic_write.py::test_crash_safety -x` | ✅ | ⬜ pending |
| 1-01-07 | 01 | 1 | SYNC-06 | unit | `pytest tests/test_memory.py::test_rolling_window -x` | ✅ | ⬜ pending |
| 1-01-08 | 01 | 1 | SYNC-07 | unit | `pytest tests/test_fetch.py::test_rate_limit_backoff -x` | ✅ | ⬜ pending |
| 1-01-09 | 01 | 1 | SYNC-08 | unit | `pytest tests/test_cli.py::test_dry_run -x` | ✅ | ⬜ pending |
| 1-01-10 | 01 | 1 | SYNC-09 | unit | `pytest tests/test_report.py::test_summary_output -x` | ✅ | ⬜ pending |
| 1-02-01 | 02 | 1 | MEM-01 | unit | `pytest tests/test_memory.py::test_schema_keys -x` | ✅ | ⬜ pending |
| 1-02-02 | 02 | 1 | MEM-02 | unit | `pytest tests/test_memory.py::test_high_performers -x` | ✅ | ⬜ pending |
| 1-02-03 | 02 | 1 | MEM-03 | unit | `pytest tests/test_memory.py::test_snapshot_ratios -x` | ✅ | ⬜ pending |
| 1-02-04 | 02 | 1 | MEM-04 | unit | `pytest tests/test_memory.py::test_initial_seed -x` | ✅ | ⬜ pending |
| 1-02-05 | 02 | 1 | MEM-05 | unit | `pytest tests/test_memory.py::test_evolution_log -x` | ✅ | ⬜ pending |
| 1-02-06 | 02 | 2 | REFS-05 | smoke | `pytest tests/test_gitignore.py::test_gitignore_blocks -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `skills/the-mirror/tests/__init__.py` — empty init
- [ ] `skills/the-mirror/tests/conftest.py` — sample tweet fixtures, mock twikit client
- [ ] `skills/the-mirror/tests/test_categorize.py` — stubs for SYNC-02, SYNC-04
- [ ] `skills/the-mirror/tests/test_fetch.py` — stubs for SYNC-03, SYNC-07
- [ ] `skills/the-mirror/tests/test_atomic_write.py` — stubs for SYNC-05
- [ ] `skills/the-mirror/tests/test_memory.py` — stubs for SYNC-06, MEM-01–MEM-05
- [ ] `skills/the-mirror/tests/test_cli.py` — stubs for SYNC-08
- [ ] `skills/the-mirror/tests/test_report.py` — stubs for SYNC-09
- [ ] `skills/the-mirror/tests/test_auth.py` — stubs for SYNC-01
- [ ] `skills/the-mirror/tests/test_gitignore.py` — stubs for REFS-05
- [ ] Framework install: `pip install pytest pytest-asyncio` — if not already installed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| twikit cookie auth actually works against X without triggering Error 226 | SYNC-01 | Requires live X session; cannot mock bot detection | Run `python mirror_sync.py --dry-run` against @ciftcibahadir, confirm no 226/suspend errors |
| `view_count` non-zero for real tweets | SYNC-02 | Requires live auth as account owner | After `--dry-run` success, inspect output JSON for `view_count > 0` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
