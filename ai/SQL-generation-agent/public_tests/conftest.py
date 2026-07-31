from __future__ import annotations

import pathlib
import json
import os
import threading
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


SUBMISSION_DIR = pathlib.Path(
    os.environ.get(
        "SUBMISSION_DIR",
        pathlib.Path(__file__).resolve().parents[1] / "starter_code",
    )
)
if SUBMISSION_DIR.exists():
    sys.path.insert(0, str(SUBMISSION_DIR))


class _LLMHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8")
        self.server.requests.append(json.loads(body))

        response = {
            "choices": [
                {
                    "message": {
                        "content": self.server.response_text,
                    }
                }
            ]
        }
        payload = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        return


@pytest.fixture
def env():
    return {
        "LLM_BASE_URL": "http://localhost:8000/v1",
        "LLM_API_KEY": "test-key",
        "LLM_MODEL": "local-model",
        "SQL_DIALECT": "SQLServer",
        "CURRENT_DATE": "2026-06-15",
        "TIMEZONE": "Asia/Tehran",
    }


@pytest.fixture
def llm_env_factory(env):
    servers = []

    def factory(response_text):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _LLMHandler)
        server.response_text = response_text
        server.requests = []
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        servers.append(server)

        configured_env = dict(env)
        configured_env["LLM_BASE_URL"] = f"http://127.0.0.1:{server.server_port}/v1"
        return configured_env, server

    yield factory

    for server in servers:
        server.shutdown()
        server.server_close()


@pytest.fixture
def accounting_schema():
    path = (
        pathlib.Path(__file__).resolve().parents[1]
        / "input_data"
        / "accounting_schema.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def call_schema():
    path = (
        pathlib.Path(__file__).resolve().parents[1]
        / "input_data"
        / "call_center_schema.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def store_schema():
    path = (
        pathlib.Path(__file__).resolve().parents[1]
        / "input_data"
        / "store_schema.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def university_schema():
    path = (
        pathlib.Path(__file__).resolve().parents[1]
        / "input_data"
        / "university_schema.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))
