"""
test_skill_structure.py — Structural tests for The Creator SKILL.md.

String-search tests. Read SKILL.md and assert specific strings exist.
Fast (< 1s), deterministic, no LLM calls.

Wave 0: All tests start RED.
Wave 2: All tests turn GREEN after 02-03-PLAN.md is executed.
"""
from pathlib import Path
import pytest

SKILL_MD_PATH = Path(__file__).parent.parent / "SKILL.md"


@pytest.fixture(scope="module")
def skill_content():
    return SKILL_MD_PATH.read_text(encoding="utf-8")


def test_dna_input_protocol(skill_content):
    """CRTR-01: Creator SKILL.md has a DNA Report Input Protocol section
    that describes how to process an incoming dna_report.json."""
    assert "## DNA Raporu Giriş Protokolü" in skill_content
    # Must reference the actual field names from the DNA report schema
    assert "data_confidence" in skill_content
    assert "voice_dna" in skill_content


def test_mod3_algorithm_signal(skill_content):
    """CRTR-02: Creator Mod 3 output format explicitly requires an
    X algorithm signal rationale section in every analysis."""
    # The explicit field name that will be added to Mod 3 output
    assert "X Algoritması Sinyal Gerekçesi" in skill_content


def test_signature_terms_enforcement(skill_content):
    """CRTR-03: Creator pre-flight DNA Test checklist explicitly references
    voice_dna.signature_terms field by name — not just 'Mirror raporuna göre'."""
    # The exact field reference that will be added
    assert "voice_dna.signature_terms" in skill_content


def test_cta_guidance_reference(skill_content):
    """CRTR-04: Creator pre-flight algorithm test references
    cta_guidance.recommended_ctas by name."""
    assert "cta_guidance.recommended_ctas" in skill_content


def test_data_confidence_gate(skill_content):
    """CRTR-05: Creator SKILL.md has a TAHMINI/data_confidence warning gate
    that prepends a warning block to EVERY output when DNA report confidence is low."""
    # The warning gate section
    assert "VERİ GÜVENİLİRLİĞİ DÜŞÜK" in skill_content
    # The TAHMINI branch must be explicit
    assert 'data_confidence.*TAHMINI' in skill_content or "data_confidence: TAHMINI" in skill_content
