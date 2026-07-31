"""
Tests verifying candidate's code calls the search API correctly.
Mock intercepts the real HTTP call — candidate must use GET with correct params.
"""
import json
import pytest
from unittest.mock import patch, MagicMock, call


def _capture_get(captured):
    """Returns a GET side_effect that records calls and returns mock docs."""
    def _get(url, *args, **kwargs):
        captured.append({"url": url, "kwargs": kwargs})
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = [
            {"text": "ماده ۱۹۰ قانون مدنی: برای صحت هر معامله شرایط ذیل اساسی است."},
            {"text": "ماده ۱ قانون مدنی: قانون مدنی ایران روابط خصوصی را تنظیم می‌کند."},
        ]
        resp.raise_for_status = MagicMock()
        return resp
    return _get


def test_search_api_is_called(mod):
    """کد کاراموز یک HTTP GET به SEARCH_API_URL می‌زند."""
    captured = []
    get_fn   = _capture_get(captured)
    http_client = MagicMock()
    http_client.get.side_effect = get_fn
    http_client.__enter__ = lambda s: http_client
    http_client.__exit__  = MagicMock(return_value=False)

    patches = [
        patch("requests.get", side_effect=get_fn),
        patch("httpx.get",    side_effect=get_fn),
        patch("httpx.Client", return_value=http_client),
    ]
    if hasattr(mod, "httpx"):
        patches += [
            patch.object(mod.httpx, "get",    side_effect=get_fn),
            patch.object(mod.httpx, "Client", return_value=http_client),
        ]
    if hasattr(mod, "requests"):
        patches += [patch.object(mod.requests, "get", side_effect=get_fn)]

    for p in patches:
        p.start()
    try:
        mod.rag_agent("ماده ۱۹۰ قانون مدنی چیست؟")
    except Exception:
        pass
    finally:
        for p in reversed(patches):
            try: p.stop()
            except Exception: pass

    assert len(captured) > 0, \
        "No HTTP GET call was made — rag_agent must call the search API"


def test_search_params_contain_query_text(mod):
    """پارامتر query_text در درخواست جستجو وجود دارد."""
    captured = []
    get_fn   = _capture_get(captured)
    http_client = MagicMock()
    http_client.get.side_effect = get_fn
    http_client.__enter__ = lambda s: http_client
    http_client.__exit__  = MagicMock(return_value=False)

    patches = [
        patch("requests.get", side_effect=get_fn),
        patch("httpx.get",    side_effect=get_fn),
        patch("httpx.Client", return_value=http_client),
    ]
    if hasattr(mod, "httpx"):
        patches += [patch.object(mod.httpx, "get", side_effect=get_fn),
                    patch.object(mod.httpx, "Client", return_value=http_client)]
    if hasattr(mod, "requests"):
        patches += [patch.object(mod.requests, "get", side_effect=get_fn)]

    for p in patches: p.start()
    try:
        mod.rag_agent("ماده ۱۹۰ قانون مدنی چیست؟")
    except Exception:
        pass
    finally:
        for p in reversed(patches):
            try: p.stop()
            except Exception: pass

    assert captured, "No GET call captured"
    params = captured[0]["kwargs"].get("params", {})
    assert "query_text" in params, \
        f"'query_text' missing from GET params: {params}"


def test_search_params_contain_top_k(mod):
    """پارامتر top_k در درخواست جستجو وجود دارد."""
    captured = []
    get_fn   = _capture_get(captured)
    http_client = MagicMock()
    http_client.get.side_effect = get_fn
    http_client.__enter__ = lambda s: http_client
    http_client.__exit__  = MagicMock(return_value=False)

    patches = [
        patch("requests.get", side_effect=get_fn),
        patch("httpx.get",    side_effect=get_fn),
        patch("httpx.Client", return_value=http_client),
    ]
    if hasattr(mod, "httpx"):
        patches += [patch.object(mod.httpx, "get", side_effect=get_fn),
                    patch.object(mod.httpx, "Client", return_value=http_client)]
    if hasattr(mod, "requests"):
        patches += [patch.object(mod.requests, "get", side_effect=get_fn)]

    for p in patches: p.start()
    try:
        mod.rag_agent("ماده ۱۹۰ قانون مدنی چیست؟")
    except Exception:
        pass
    finally:
        for p in reversed(patches):
            try: p.stop()
            except Exception: pass

    assert captured, "No GET call captured"
    params = captured[0]["kwargs"].get("params", {})
    assert "top_k" in params, \
        f"'top_k' missing from GET params: {params}"


def test_graceful_on_search_error(mod):
    """در صورت خطای سرویس جستجو، تابع crash نمی‌کند."""
    def _error_get(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 500
        resp.raise_for_status.side_effect = Exception("Internal Server Error")
        resp.json.side_effect = Exception("Internal Server Error")
        return resp

    http_client = MagicMock()
    http_client.get.side_effect = _error_get
    http_client.__enter__ = lambda s: http_client
    http_client.__exit__  = MagicMock(return_value=False)

    patches = [
        patch("requests.get", side_effect=_error_get),
        patch("httpx.get",    side_effect=_error_get),
        patch("httpx.Client", return_value=http_client),
    ]
    if hasattr(mod, "httpx"):
        patches += [patch.object(mod.httpx, "get", side_effect=_error_get),
                    patch.object(mod.httpx, "Client", return_value=http_client)]
    if hasattr(mod, "requests"):
        patches += [patch.object(mod.requests, "get", side_effect=_error_get)]

    for p in patches: p.start()
    try:
        result = mod.rag_agent("سوال تستی")
        assert isinstance(result, dict), "Must return dict even on search error"
        assert "answer" in result
    except Exception as e:
        raise AssertionError(f"rag_agent crashed on search error: {e}")
    finally:
        for p in reversed(patches):
            try: p.stop()
            except Exception: pass


def test_graceful_on_empty_results(agent_result_empty):
    """در صورت خالی بودن نتایج جستجو، تابع crash نمی‌کند."""
    assert not isinstance(agent_result_empty, Exception), \
        f"rag_agent crashed on empty results: {agent_result_empty}"
    assert isinstance(agent_result_empty, dict)
    assert "answer" in agent_result_empty
