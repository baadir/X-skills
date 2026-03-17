---
phase: 2
slug: mirror-creator-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already installed from Phase 1) |
| **Config file** | `skills/the-mirror/tests/` (existing), `skills/the-creator/tests/` (Wave 0 creates) |
| **Quick run command** | `pytest skills/the-mirror/tests/ skills/the-creator/tests/ -v` |
| **Full suite command** | `pytest skills/the-mirror/tests/ skills/the-creator/tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest skills/the-mirror/tests/ skills/the-creator/tests/ -v`
- **After every plan wave:** Run full suite above
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 0 | MSKILL-01–04, CRTR-01–05 | structural | `pytest skills/the-mirror/tests/test_skill_structure.py skills/the-creator/tests/test_skill_structure.py -v` | Wave 0 | ⬜ pending |
| 2-02-01 | 02 | 1 | MSKILL-01 | structural | `pytest skills/the-mirror/tests/test_skill_structure.py::test_schema_documented -x` | ✅ | ⬜ pending |
| 2-02-02 | 02 | 1 | MSKILL-02 | structural | `pytest skills/the-mirror/tests/test_skill_structure.py::test_staleness_check_present -x` | ✅ | ⬜ pending |
| 2-02-03 | 02 | 1 | MSKILL-03 | structural | `pytest skills/the-mirror/tests/test_skill_structure.py::test_dna_report_fields -x` | ✅ | ⬜ pending |
| 2-02-04 | 02 | 1 | MSKILL-04 | structural | `pytest skills/the-mirror/tests/test_skill_structure.py::test_data_sufficiency_gate -x` | ✅ | ⬜ pending |
| 2-03-01 | 03 | 2 | CRTR-01 | structural | `pytest skills/the-creator/tests/test_skill_structure.py::test_dna_input_protocol -x` | ✅ | ⬜ pending |
| 2-03-02 | 03 | 2 | CRTR-02 | structural | `pytest skills/the-creator/tests/test_skill_structure.py::test_mod3_algorithm_signal -x` | ✅ | ⬜ pending |
| 2-03-03 | 03 | 2 | CRTR-03 | structural | `pytest skills/the-creator/tests/test_skill_structure.py::test_signature_terms_enforcement -x` | ✅ | ⬜ pending |
| 2-03-04 | 03 | 2 | CRTR-04 | structural | `pytest skills/the-creator/tests/test_skill_structure.py::test_cta_guidance_reference -x` | ✅ | ⬜ pending |
| 2-03-05 | 03 | 2 | CRTR-05 | structural | `pytest skills/the-creator/tests/test_skill_structure.py::test_data_confidence_gate -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `skills/the-mirror/tests/test_skill_structure.py` — stubs for MSKILL-01, MSKILL-02, MSKILL-03, MSKILL-04
- [ ] `skills/the-creator/tests/__init__.py` — package marker for new test directory
- [ ] `skills/the-creator/tests/test_skill_structure.py` — stubs for CRTR-01, CRTR-02, CRTR-03, CRTR-04, CRTR-05
- [ ] `skills/the-mirror/tests/fixtures/sample_style_memory_full.json` — full data fixture (>=20 tweets)
- [ ] `skills/the-mirror/tests/fixtures/sample_style_memory_sparse.json` — sparse data fixture (<20 tweets)

*Note: Tests use string-search (grep) against SKILL.md file content — fast (<1s), deterministic, no LLM calls required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mirror produces dna_report with real engagement data | MSKILL-03 | Requires live LLM + real style_memory.json | Load Mirror skill, paste style_memory.json, confirm dna_report fields populated |
| Creator Mod 1 uses signature_expressions term in output | CRTR-03 | Requires live LLM conversation | Run Creator Mod 1 with DNA report, verify ≥1 signature term appears in proposal |
| Creator Mod 3 provides algorithm-signal rationale | CRTR-02 | Requires live LLM conversation | Run Creator Mod 3 on a tweet, verify structured critique includes signal rationale |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
