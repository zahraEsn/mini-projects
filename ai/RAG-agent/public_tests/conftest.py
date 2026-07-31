"""
Q1 public tests.
Search API is mocked from local input_data/documents.json.
LLM uses real credentials from .env.
"""
import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

ROOT = Path(__file__).parent.parent
DOCS_PATH = ROOT / "input_data" / "documents.json"
SUBMISSION_PATH = os.environ.get(
    "SUBMISSION_PATH",
    str(ROOT / "starter_code" / "solution.py"),
)


# ---------------------------------------------------------------------------
# Mock search — returns list of {"text": "..."} matching real API format
# ---------------------------------------------------------------------------

def _keyword_search(query_text: str, top_k: int = 5) -> list:
    """Simple keyword search over local documents.json."""
    with open(DOCS_PATH, encoding="utf-8") as f:
        docs = json.load(f)   # already in [{"text": "..."}, ...] format
    words = set(query_text.replace("؟", "").replace("،", "").split())
    scored = sorted(docs, key=lambda d: -sum(1 for w in words if w in d["text"]))
    return scored[:top_k]


def _make_search_response(url, *args, **kwargs):
    """Unified GET handler — intercepts any HTTP GET to search URL."""
    params   = kwargs.get("params", {})
    query    = params.get("query_text", "")
    top_k    = int(params.get("top_k", 5))
    results  = _keyword_search(query, top_k)

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = results
    resp.raise_for_status = MagicMock()
    return resp


def _make_httpx_client_mock():
    client = MagicMock()
    client.get.side_effect = _make_search_response
    client.__enter__ = lambda s: client
    client.__exit__  = MagicMock(return_value=False)
    return client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def source():
    with open(SUBMISSION_PATH, encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="session")
def mod(source):
    sub_dir = os.path.dirname(os.path.abspath(SUBMISSION_PATH))
    if sub_dir not in sys.path:
        sys.path.insert(0, sub_dir)
    spec = importlib.util.spec_from_file_location("solution", SUBMISSION_PATH)
    m    = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="session")
def mock_search_patches(mod):
    """
    Returns started patches that mock all HTTP GET calls to the search API.
    Candidate's code calls the real search URL — mock intercepts it transparently.
    When we run final tests with real SEARCH_API_URL/KEY, this fixture is not used.
    """
    patches = [
        patch("requests.get", side_effect=_make_search_response),
        patch("httpx.get",    side_effect=_make_search_response),
        patch("httpx.Client", return_value=_make_httpx_client_mock()),
    ]
    if hasattr(mod, "httpx"):
        patches += [
            patch.object(mod.httpx, "get",    side_effect=_make_search_response),
            patch.object(mod.httpx, "Client", return_value=_make_httpx_client_mock()),
        ]
    if hasattr(mod, "requests"):
        patches += [
            patch.object(mod.requests, "get", side_effect=_make_search_response),
        ]
    for p in patches:
        p.start()
    yield
    for p in reversed(patches):
        try:
            p.stop()
        except Exception:
            pass


@pytest.fixture(scope="session")
def agent_result(mod, mock_search_patches):
    """Run rag_agent once with mock search — cached for all tests."""
    return mod.rag_agent("ماده ۱۹۰ قانون مدنی چه شرایطی برای صحت معامله مقرر کرده است؟")


@pytest.fixture(scope="session")
def agent_result_empty(mod, mock_search_patches):
    """Run rag_agent with a query that returns no documents."""
    # temporarily return empty list
    with patch("requests.get", side_effect=lambda *a, **kw: _empty_resp()), \
         patch("httpx.get",    side_effect=lambda *a, **kw: _empty_resp()):
        try:
            return mod.rag_agent("xyzxyzxyz irrelevant query 12345")
        except Exception as e:
            return e


def _empty_resp():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = []
    resp.raise_for_status = MagicMock()
    return resp
