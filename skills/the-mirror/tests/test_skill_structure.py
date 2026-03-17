"""
test_skill_structure.py — Structural tests for The Mirror SKILL.md.

These tests are string-search (grep) tests. They read SKILL.md and assert
that specific sections and strings are present. Tests run in < 1 second,
require no LLM calls, and are deterministic.

Wave 0: All tests start RED (strings not yet in SKILL.md).
Wave 1: All tests turn GREEN after 02-02-PLAN.md is executed.
"""
from pathlib import Path
import pytest

SKILL_MD_PATH = Path(__file__).parent.parent / "SKILL.md"


@pytest.fixture(scope="module")
def skill_content():
    return SKILL_MD_PATH.read_text(encoding="utf-8")


def test_schema_documented(skill_content):
    """MSKILL-01: SKILL.md documents the actual style_memory.json schema
    as produced by mirror_sync.py — must contain tweet_archive field with
    per-tweet structure and the actual hook_type/tone enum values."""
    # The section heading that will be added in Wave 1
    assert "## style_memory.json Şeması (mirror_sync.py Çıktısı)" in skill_content
    # Actual enum values from mirror_sync.py detect_hook_type()
    assert "rakam_ile_bas" in skill_content
    assert "cesur_iddia" in skill_content
    # Actual tone enum values from mirror_sync.py detect_tone()
    assert "egitici" in skill_content
    assert "heyecanli" in skill_content
    # Per-tweet structure field
    assert "tweet_archive" in skill_content


def test_staleness_check_present(skill_content):
    """MSKILL-02: SKILL.md contains staleness check protocol with 7-day
    threshold and the required warning text format."""
    # Section heading for staleness check
    assert "## Aktivasyon Protokolü" in skill_content
    # The 7-day threshold must be explicit
    assert "7 gün" in skill_content
    # The Turkish warning command that will be present
    assert "SYNC UYARISI" in skill_content


def test_dna_report_fields(skill_content):
    """MSKILL-03: SKILL.md has a DNA report output section with all
    required fields — including data_confidence, sync_status, hook_arsenal,
    and tone_profile with actual enum values."""
    # The section heading for the new reconciled DNA report
    assert "## DNA Raporu Çıktı Şeması" in skill_content
    # Required top-level fields
    assert "data_confidence" in skill_content
    assert "sync_status" in skill_content
    assert "hook_arsenal" in skill_content
    # hook_type_performance must use actual mirror_sync.py enum values
    assert '"soru"' in skill_content
    assert '"provokasyon"' in skill_content
    assert '"liste_vaadi"' in skill_content
    # tone_performance must use actual mirror_sync.py enum values
    assert '"alaycı"' in skill_content
    assert '"egitici"' in skill_content
    assert '"profesyonel"' in skill_content


def test_data_sufficiency_gate(skill_content):
    """MSKILL-04: SKILL.md contains the data-sufficiency gate — <20 tweet
    check that triggers TAHMINİ mode for all output sections."""
    # The gate section
    assert "## Veri Yeterliliği Kontrolü" in skill_content
    # The threshold and flag
    assert "< 20" in skill_content
    assert "TAHMINİ" in skill_content
    # Instruction to compute signature_expressions from high_performers
    assert "high_performers" in skill_content
    assert "signature_expressions" in skill_content
