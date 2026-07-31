"""
Bonus tests for citation support.
These tests check if candidate implemented <cite> tags and citations list.
Failing these tests does not affect the base score.
"""
import re
import pytest


def test_citations_field_exists(agent_result):
    """BONUS — فیلد citations در خروجی وجود دارد."""
    assert "citations" in agent_result, \
        "Missing 'citations' key — implement citations for bonus points"


def test_citations_is_list(agent_result):
    """BONUS — فیلد citations یک لیست است."""
    assert isinstance(agent_result.get("citations"), list), \
        "citations must be a list"


def test_cite_tags_in_answer(agent_result):
    """BONUS — متن answer شامل تگ‌های <cite>N</cite> است."""
    answer = agent_result.get("answer", "")
    tags   = re.findall(r"<cite>\d+</cite>", answer)
    assert tags, \
        "No <cite>N</cite> tags found in answer — use <cite>1</cite> to reference documents"


def test_citations_match_document_ids(agent_result):
    """BONUS — citation id ها با id اسناد موجود مطابقت دارند."""
    doc_ids   = {d["id"] for d in agent_result.get("documents", [])}
    citations = agent_result.get("citations", [])
    if not citations:
        pytest.skip("No citations to validate")
    invalid = [c for c in citations if c not in doc_ids]
    assert not invalid, \
        f"Citations {invalid} don't match any document id {doc_ids}"


def test_cite_tags_match_citations_list(agent_result):
    """BONUS — اعداد داخل <cite> با لیست citations یکسانند."""
    answer    = agent_result.get("answer", "")
    from_tags = sorted(set(int(n) for n in re.findall(r"<cite>(\d+)</cite>", answer)))
    from_list = sorted(set(agent_result.get("citations", [])))
    if not from_tags and not from_list:
        pytest.skip("No citations to compare")
    assert from_tags == from_list, \
        f"Mismatch — tags: {from_tags}, citations list: {from_list}"
