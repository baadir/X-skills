---
phase: 3
slug: miner-lab-references
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Bu faz tamamen dokümantasyon — test framework kurulumu gerekmez. Grep string-search yeterli.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | grep (no pytest needed — documentation-only phase) |
| **Config file** | none |
| **Quick run command** | `grep -n "0.3\|dinamik\|prompt-only" skills/the-miner/SKILL.md skills/the-lab/SKILL.md` |
| **Full suite command** | See Per-Task Verification Map below |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run task's specific grep verify command
- **After every plan:** Run full grep suite against all modified files
- **Before `/gsd:verify-work`:** All grep checks must return matches
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Requirement | Test Type | Automated Command | Status |
|---------|------|-------------|-----------|-------------------|--------|
| 3-01-01 | 01 | MLSKILL-01 | string-search | `grep -n "0.3" skills/the-miner/SKILL.md` | ⬜ pending |
| 3-01-02 | 01 | MLSKILL-01 | string-search | `grep -n "dinamik\|sorgu" skills/the-miner/SKILL.md` | ⬜ pending |
| 3-01-03 | 01 | MLSKILL-01 | string-search | `grep -n "priority_score" skills/the-miner/SKILL.md` | ✅ already passes |
| 3-01-04 | 01 | MLSKILL-03 | string-search | `grep -n "prompt-only\|kod yok" skills/the-miner/SKILL.md` | ⬜ pending |
| 3-02-01 | 02 | MLSKILL-02 | string-search | `grep -n "custom_id" skills/the-lab/SKILL.md` | ✅ already passes |
| 3-02-02 | 02 | MLSKILL-02 | string-search | `grep -n "S-tier\|S tier" skills/the-lab/SKILL.md` | ✅ already passes |
| 3-02-03 | 02 | MLSKILL-03 | string-search | `grep -n "prompt-only\|kod yok" skills/the-lab/SKILL.md` | ⬜ pending |
| 3-03-01 | 03 | REFS-01 | string-search | `grep -n "decay_factor" references/x_algorithm_signals.md` | ✅ already passes |
| 3-03-02 | 03 | REFS-02 | string-search | `grep -n "twikit 2.3.3" references/tweet_datasets.md` | ⬜ pending |
| 3-03-03 | 03 | REFS-02 | string-search | `grep -n "kullanılmıyor\|v1.*dışı" references/tweet_datasets.md` | ⬜ pending |
| 3-04-01 | 04 | REFS-03 | string-search | `grep -n "twikit" decision.md` | ⬜ pending |
| 3-04-02 | 04 | REFS-03 | string-search | `grep -n "data_confidence\|DNA" decision.md` | ⬜ pending |
| 3-04-03 | 04 | REFS-04 | string-search | `grep -n "Karar verildi\|yerelde" strateji.md` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None — this phase uses grep against existing files, no test infrastructure setup needed.
3 requirements (MLSKILL-01 priority_score, MLSKILL-02 custom_id + S-tier, REFS-01 decay_factor) already pass before any work begins.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Miner SKILL.md is internally consistent (no code blocks claim to be runnable) | MLSKILL-03 | Requires reading for semantic sense, not just string presence | Read the-miner/SKILL.md — no function definitions, no import statements should be present as executable code |
| decision.md backfill is accurate (decisions match what was actually implemented) | REFS-03 | Requires cross-referencing against actual code | Spot-check 3 decisions against mirror_sync.py to confirm accuracy |

---

## Validation Sign-Off

- [ ] All tasks have grep verify commands
- [ ] Sampling continuity: verify after each task commit
- [ ] 3 already-passing checks documented as baseline
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
