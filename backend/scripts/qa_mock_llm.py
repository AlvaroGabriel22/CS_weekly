"""Mock de API OpenAI-compatível para os testes de carga do QA (Agente L).

Responde /v1/chat/completions em ~50ms com JSON fixo, permitindo isolar a
capacidade do app (FastAPI/SQLite/PPTX) da capacidade do LLM real.

Uso:  ./venv/bin/python scripts/qa_mock_llm.py  (porta 9099)
Backend de QA aponta para ele com:
  LLM_PROVIDER=openai_compat LLM_BASE_URL=http://localhost:9099/v1 LLM_MODEL=mock
"""
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPLY = {
    "summary": "Resumo sintético de carga.",
    "highlights": ["item 1", "item 2"],
    "kpis": ["KPI 1"],
    "conclusions": ["ok"],
    "next_steps": ["seguir"],
}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        time.sleep(0.05)
        body = json.dumps({
            "id": "mock", "object": "chat.completion", "model": "mock",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant",
                                     "content": json.dumps(REPLY, ensure_ascii=False)}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silencioso
        pass


if __name__ == "__main__":
    print("mock LLM em http://localhost:9099/v1/chat/completions")
    ThreadingHTTPServer(("127.0.0.1", 9099), Handler).serve_forever()
