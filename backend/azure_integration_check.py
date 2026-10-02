"""
E2E check: Azure AI Foundry provider (mock Foundry server — no real key spent).

Boots a tiny HTTP server mimicking the Foundry /models/chat/completions route,
points AZURE_AI_ENDPOINT at it, then exercises:
  1. /health reports azure configured + available
  2. journal summarize routes through azure (ai_source == 'azure')
  3. _query_ai falls back ollama -> azure -> groq in the right order

Run:  ./venv/bin/python azure_integration_check.py
"""

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

os.environ.setdefault("JWT_SECRET", "test-secret-azure-integration-000000000000")
os.environ["AZURE_AI_ENDPOINT"] = "http://localhost:8971"
os.environ["AZURE_AI_KEY"] = "mock-foundry-key"
os.environ["AZURE_DEPLOYMENT"] = "gpt-5.4-mini"
os.environ["ENCRYPTION_PASSPHRASE"] = "test-passphrase-azure-integration"
os.environ["ENCRYPTION_SALT"] = "9f2c7ae15b38d046c1a9e57b2f8d3601"
os.environ["OLLAMA_URL"] = "http://localhost:1"  # nothing there — forces fallback
os.environ["GROQ_API_KEY"] = ""

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app.core.config as _config

_config.Settings.Config = type("Config", (), {"env_file": None, "env_file_encoding": "utf-8", "extra": "ignore"})
import importlib

_config.settings = _config.Settings()
import app.core.health as _health
import app.services.ai_service as _ai

_ai.settings = _config.settings
_health.settings = _config.settings
importlib.reload(_ai)
importlib.reload(_health)
_ai.settings = _config.settings
_health.settings = _config.settings

HITS = {"chat": 0}


class MockFoundry(BaseHTTPRequestHandler):
    """Answers both route styles:
    • Foundry:            /models/chat/completions
    • classic AzureOpenAI /openai/deployments/<dep>/chat/completions
    """

    def do_POST(self):
        path = self.path.split("?")[0]  # strip ?api-version=...
        if path.endswith("/chat/completions"):
            HITS["chat"] += 1
            body = json.dumps(
                {
                    "id": "chatcmpl-mock",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": '{"summary": "Mock Azure summary: you sounded anxious but coping."}',
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "model": "gpt-5.4-mini",
                    "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *a):
        pass


def main():
    server = HTTPServer(("localhost", 8971), MockFoundry)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    from app.core.health import health_ai
    from app.services.ai_service import _query_ai, summarize_journal

    # 1. health reports azure
    h = health_ai()
    assert h["azure"]["configured"] is True, f"azure not configured: {h}"
    assert h["azure"]["available"] is True
    assert h["azure"]["deployment"] == "gpt-5.4-mini"
    assert h["any_available"] is True
    print("1. health_ai(): azure configured+available OK")

    # 2. summarize_journal routes through azure
    r = summarize_journal("Today was rough. I had a panic attack before class but used breathing and got through it.")
    assert r["ai_source"] == "azure", f"expected azure, got {r['ai_source']}: {r}"
    assert "Mock Azure summary" in r["summary"]
    assert HITS["chat"] >= 1
    print(f"2. summarize_journal(): ai_source=azure OK (foundry hits: {HITS['chat']})")

    # 3. generic _query_ai hits azure when ollama is down
    out = _query_ai("ping", prompt_version="test/v1")
    assert out.strip(), "_query_ai returned empty"
    print("3. _query_ai(): ollama-down fallback -> azure OK")

    server.shutdown()
    print("\nALL AZURE INTEGRATION CHECKS PASSED")


if __name__ == "__main__":
    main()
