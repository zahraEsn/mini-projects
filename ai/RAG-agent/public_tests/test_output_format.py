"""
Tests for rag_agent output structure.
Uses mock search (from conftest.py), real LLM.
"""
import pytest


def test_output_is_dict(agent_result):
    """خروجی rag_agent یک dict است."""
    assert isinstance(agent_result, dict), \
        f"Expected dict, got {type(agent_result)}"


def test_answer_field_exists(agent_result):
    """فیلد answer در خروجی وجود دارد."""
    assert "answer" in agent_result, "Missing 'answer' key in output"


def test_answer_is_nonempty_string(agent_result):
    """فیلد answer یک رشته غیر خالی است."""
    answer = agent_result.get("answer", "")
    assert isinstance(answer, str), f"answer must be str, got {type(answer)}"
    assert len(answer.strip()) > 0, "answer is empty"


def test_documents_field_exists(agent_result):
    """فیلد documents در خروجی وجود دارد."""
    assert "documents" in agent_result, "Missing 'documents' key in output"


def test_documents_is_list(agent_result):
    """فیلد documents یک لیست است."""
    assert isinstance(agent_result.get("documents"), list), \
        "documents must be a list"


def test_documents_not_empty(agent_result):
    """حداقل یک سند بازیابی شده است."""
    assert len(agent_result.get("documents", [])) > 0, \
        "documents list is empty"


def test_each_document_has_id(agent_result):
    """هر سند دارای فیلد id است."""
    for i, d in enumerate(agent_result.get("documents", [])):
        assert "id" in d, f"Document {i} missing 'id' field"


def test_each_document_has_text(agent_result):
    """هر سند دارای فیلد text است."""
    for i, d in enumerate(agent_result.get("documents", [])):
        assert "text" in d, f"Document {i} missing 'text' field"
        assert isinstance(d["text"], str) and len(d["text"]) > 0, \
            f"Document {i} has empty text"


def test_document_ids_are_1_based(agent_result):
    """id اسناد از ۱ شروع می‌شود."""
    docs = agent_result.get("documents", [])
    if docs:
        ids = sorted(d["id"] for d in docs)
        assert ids[0] == 1, f"First document id should be 1, got {ids[0]}"


def test_document_ids_are_sequential(agent_result):
    """id اسناد پیوسته و بدون تکرار هستند."""
    docs = agent_result.get("documents", [])
    ids  = [d["id"] for d in docs]
    assert len(ids) == len(set(ids)), "Duplicate document ids found"
