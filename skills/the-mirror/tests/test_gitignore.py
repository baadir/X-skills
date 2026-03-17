"""
test_gitignore.py — Credential protection smoke test (REFS-05).

This test is IMPLEMENTED now (not a stub) because it only reads a file
on disk and asserts that the .gitignore contains the required patterns.
It will PASS once skills/the-mirror/.gitignore exists with correct content.
"""
from pathlib import Path


def test_gitignore_blocks():
    """REFS-05: .gitignore blocks cookies.json, .env, and style_memory.json.

    Reads skills/the-mirror/.gitignore and asserts that all three
    sensitive file patterns appear in it, ensuring credentials and
    local data files will never be accidentally committed.
    """
    gitignore_path = Path(__file__).parent.parent / ".gitignore"

    assert gitignore_path.exists(), (
        f".gitignore not found at {gitignore_path}. "
        "Run Task 2 to create skills/the-mirror/.gitignore."
    )

    content = gitignore_path.read_text(encoding="utf-8")

    assert "cookies.json" in content, (
        "cookies.json not found in .gitignore — twikit auth cookie must be blocked"
    )
    assert ".env" in content, (
        ".env not found in .gitignore — API credentials must be blocked"
    )
    assert "style_memory.json" in content, (
        "style_memory.json not found in .gitignore — local user data must be blocked"
    )
