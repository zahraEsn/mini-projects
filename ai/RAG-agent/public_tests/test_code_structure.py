"""
Tests for code structure — no API calls needed.
"""
import re
import pytest


def test_syntax_no_errors(source):
    """کد بدون خطای syntax اجرا می‌شود."""
    from conftest import SUBMISSION_PATH
    compile(source, SUBMISSION_PATH, "exec")


def test_rag_agent_exists(mod):
    """تابع rag_agent وجود دارد و callable است."""
    assert hasattr(mod, "rag_agent"), "rag_agent function not found"
    assert callable(mod.rag_agent)


def test_no_hardcoded_secrets(source):
    """مقادیر ثابت API key یا URL در کد وجود ندارد."""
    suspicious = []
    for line in source.splitlines():
        if "os.environ" in line or "os.getenv" in line:
            continue
        for m in re.findall(r'(sk-[A-Za-z0-9]{10,}|https?://[a-zA-Z0-9._/:-]{8,})', line):
            suspicious.append(m)
    assert not suspicious, f"Hardcoded values found: {suspicious}"


def test_reads_env_vars(source):
    """کانفیگ از متغیرهای محیطی خوانده می‌شود."""
    assert re.search(r"os\.(environ|getenv)", source), \
        "os.environ or os.getenv not found in code"


def test_uses_search_url_from_env(source):
    """SEARCH_API_URL از محیط خوانده می‌شود نه hardcode."""
    assert "SEARCH_API_URL" in source, \
        "SEARCH_API_URL not referenced in code"


def test_uses_llm_key_from_env(source):
    """LLM_API_KEY از محیط خوانده می‌شود."""
    assert "LLM_API_KEY" in source, \
        "LLM_API_KEY not referenced in code"
