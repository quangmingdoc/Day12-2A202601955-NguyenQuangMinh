"""Agent service — điểm ráp nối của cả lab (CP1, CP3, CP4).

Luồng một request tới /ask:

    client ──► verify_api_key ──► rate_limiter ──► cost_guard
                                                       │
                              store.get_history ◄──────┘
                                       │
                                    ask_llm
                                       │
                              store.append × 2 ──► cost_guard.record ──► log_event
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from utils.mock_llm import ask_llm

from .auth import verify_api_key
from .config import get_settings
from .cost_guard import CostGuard
from .lifecycle import lifecycle
from .logging_utils import log_event
from .rate_limiter import RateLimiter
from .store import ConversationStore, get_redis_client

SERVICE_NAME = "day12-agent"
SERVICE_VERSION = "1.0.0"


# ─────────────────────────────────────────────────────────────
# Providers — CHO SẴN
# Tách ra thành hàm để test có thể thay bằng Redis giả qua
# app.dependency_overrides, và để kết nối Redis chỉ tạo khi thật sự cần.
# ─────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_store() -> ConversationStore:
    return ConversationStore(get_redis_client())


@lru_cache(maxsize=1)
def get_rate_limiter() -> RateLimiter:
    return RateLimiter(get_redis_client(), get_settings().rate_limit_per_minute)


@lru_cache(maxsize=1)
def get_cost_guard() -> CostGuard:
    return CostGuard(get_redis_client(), get_settings().monthly_budget_usd)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """CHO SẴN — chạy lúc app khởi động và lúc tắt."""
    lifecycle.install()
    log_event("service_started", service=SERVICE_NAME, version=SERVICE_VERSION)
    yield
    log_event("service_stopped", service=SERVICE_NAME)


app = FastAPI(title="Day 12 Production Agent", version=SERVICE_VERSION, lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


# ─────────────────────────────────────────────────────────────
# Dashboard — trang tổng quan, không phục vụ traffic thật
# ─────────────────────────────────────────────────────────────
DASHBOARD_HTML = f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{SERVICE_NAME}</title>
<style>
  :root {{
    --bg: #0b0d12; --card: #12151c; --border: #232733; --text: #e6e9ef;
    --muted: #8b93a7; --accent: #6ea8fe; --ok: #3ddc84; --bad: #ff5c72; --warn: #f5c451;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 2.5rem 1.5rem; background: var(--bg); color: var(--text);
    font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  }}
  .wrap {{ max-width: 880px; margin: 0 auto; }}
  h1 {{ font-size: 1.5rem; margin: 0 0 0.25rem; }}
  .sub {{ color: var(--muted); margin: 0 0 2rem; font-size: 0.9rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 1.1rem 1.3rem; }}
  .card h2 {{ font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); margin: 0 0 0.6rem; }}
  .status-row {{ display: flex; align-items: center; gap: 0.55rem; font-size: 1.05rem; font-weight: 600; }}
  .dot {{ width: 10px; height: 10px; border-radius: 50%; background: var(--muted); flex-shrink: 0; }}
  .dot.ok {{ background: var(--ok); box-shadow: 0 0 8px var(--ok); }}
  .dot.bad {{ background: var(--bad); box-shadow: 0 0 8px var(--bad); }}
  .detail {{ color: var(--muted); font-size: 0.82rem; margin-top: 0.35rem; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
  td {{ padding: 0.35rem 0; border-bottom: 1px solid var(--border); }}
  td:first-child {{ color: var(--muted); width: 40%; }}
  td:last-child {{ text-align: right; font-family: ui-monospace, monospace; }}
  .endpoints a {{ color: var(--accent); text-decoration: none; }}
  .endpoints a:hover {{ text-decoration: underline; }}
  .endpoints code {{ background: #1a1e28; padding: 0.1rem 0.4rem; border-radius: 4px; }}
  .badge {{ display: inline-block; font-size: 0.72rem; padding: 0.15rem 0.5rem; border-radius: 999px; margin-left: 0.4rem; }}
  .badge.get {{ background: #1e3a5f; color: #8ec9ff; }}
  .badge.post {{ background: #3f2c14; color: #f5c451; }}
  footer {{ margin-top: 2rem; color: var(--muted); font-size: 0.78rem; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{SERVICE_NAME}</h1>
  <p class="sub">v{SERVICE_VERSION} · production agent service · trạng thái được đọc trực tiếp từ /health và /ready</p>

  <div class="grid">
    <div class="card">
      <h2>Liveness</h2>
      <div class="status-row"><span id="health-dot" class="dot"></span><span id="health-text">Đang kiểm tra…</span></div>
      <div class="detail" id="health-detail">&nbsp;</div>
    </div>
    <div class="card">
      <h2>Readiness</h2>
      <div class="status-row"><span id="ready-dot" class="dot"></span><span id="ready-text">Đang kiểm tra…</span></div>
      <div class="detail" id="ready-detail">&nbsp;</div>
    </div>
  </div>

  <div class="card" style="margin-bottom:1.5rem">
    <h2>Cấu hình đang chạy</h2>
    <table>
      <tr><td>Service</td><td>{SERVICE_NAME}</td></tr>
      <tr><td>Version</td><td>{SERVICE_VERSION}</td></tr>
      <tr><td>Runtime</td><td>FastAPI + Uvicorn, Docker (multi-stage)</td></tr>
      <tr><td>State store</td><td>Redis (rate limit, cost guard, lịch sử hội thoại)</td></tr>
      <tr><td>Auth</td><td>header <code>X-API-Key</code>, so sánh bằng <code>secrets.compare_digest</code></td></tr>
    </table>
  </div>

  <div class="card endpoints">
    <h2>Endpoints</h2>
    <table>
      <tr><td><code>/health</code><span class="badge get">GET</span></td><td>liveness, không phụ thuộc Redis</td></tr>
      <tr><td><code>/ready</code><span class="badge get">GET</span></td><td>readiness, kiểm tra kết nối Redis</td></tr>
      <tr><td><code>/ask</code><span class="badge post">POST</span></td><td>hỏi agent, cần <code>X-API-Key</code></td></tr>
      <tr><td><code>/docs</code><span class="badge get">GET</span></td><td><a href="/docs">Swagger UI</a></td></tr>
    </table>
  </div>

  <footer>Trang này chỉ đọc trạng thái, không gọi Redis hay LLM — an toàn để để public.</footer>
</div>

<script>
async function checkEndpoint(path, dotId, textId, detailId) {{
  const dot = document.getElementById(dotId);
  const text = document.getElementById(textId);
  const detail = document.getElementById(detailId);
  try {{
    const res = await fetch(path, {{ cache: "no-store" }});
    const body = await res.json().catch(() => ({{}}));
    if (res.ok) {{
      dot.classList.add("ok");
      text.textContent = "OK (" + res.status + ")";
    }} else {{
      dot.classList.add("bad");
      text.textContent = "Lỗi (" + res.status + ")";
    }}
    detail.textContent = JSON.stringify(body);
  }} catch (err) {{
    dot.classList.add("bad");
    text.textContent = "Không kết nối được";
    detail.textContent = String(err);
  }}
}}
checkEndpoint("/health", "health-dot", "health-text", "health-detail");
checkEndpoint("/ready", "ready-dot", "ready-text", "ready-detail");
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard():
    """Trang tổng quan cho service — thông tin tĩnh + trạng thái live qua JS."""
    return DASHBOARD_HTML


# ─────────────────────────────────────────────────────────────
# Health & readiness
# ─────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    """Liveness probe — process còn sống không?

    TODO (CP1 + CP4):
      - Đang tắt dần (``lifecycle.shutting_down``) → trả
        ``JSONResponse(status_code=503, content={"status": "shutting_down"})``
      - Bình thường → ``{"status": "ok", "service": SERVICE_NAME,
        "version": SERVICE_VERSION}`` (mặc định FastAPI trả 200).

    Endpoint này phải **nhẹ**: không gọi Redis, không query DB. Nó chỉ trả
    lời câu hỏi "có cần restart container này không?". Nếu nó phụ thuộc
    Redis, Redis chết một nhịp là cả cụm container bị restart theo.
    """
    if lifecycle.shutting_down:
        return JSONResponse(status_code=503, content={"status": "shutting_down"})
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.get("/ready")
def ready(store: ConversationStore = Depends(get_store)):
    """Readiness probe — đã sẵn sàng nhận traffic chưa?

    TODO (CP4):
      - Đang tắt dần → 503 ``{"status": "shutting_down"}``
      - ``store.ping()`` False → 503 ``{"status": "not ready", "redis": False}``
      - Ngược lại → ``{"status": "ready", "redis": True}``

    Khác /health ở chỗ: endpoint này ĐƯỢC PHÉP kiểm tra dependency. Load
    balancer dùng nó để quyết định có đẩy request vào instance này không.
    """
    if lifecycle.shutting_down:
        return JSONResponse(status_code=503, content={"status": "shutting_down"})
    if not store.ping():
        return JSONResponse(status_code=503, content={"status": "not ready", "redis": False})
    return {"status": "ready", "redis": True}


# ─────────────────────────────────────────────────────────────
# Endpoint chính
# ─────────────────────────────────────────────────────────────
@app.post("/ask")
def ask(
    payload: AskRequest,
    user_id: str = Depends(verify_api_key),
    store: ConversationStore = Depends(get_store),
    limiter: RateLimiter = Depends(get_rate_limiter),
    guard: CostGuard = Depends(get_cost_guard),
):
    """Hỏi agent một câu.

    TODO (CP3 + CP4) — làm ĐÚNG THỨ TỰ sau:
      1. ``limiter.check(user_id)``           → 429 nếu gọi quá nhanh
      2. ``guard.check(user_id)``             → 402 nếu hết ngân sách
      3. ``history = store.get_history(user_id)``
      4. ``result = ask_llm(payload.question, history)``
      5. ``store.append(user_id, "user", payload.question)`` và
         ``store.append(user_id, "assistant", result["answer"])``
      6. ``guard.record(user_id, result["cost_usd"])``
      7. ``log_event("ask_completed", user_id=user_id,
         tokens_in=result["tokens_in"], tokens_out=result["tokens_out"],
         cost_usd=result["cost_usd"])``
      8. trả về::

            {
                "answer": result["answer"],
                "user_id": user_id,
                "history_length": len(history),
                "cost_usd": result["cost_usd"],
                "tokens": {"in": result["tokens_in"], "out": result["tokens_out"]},
            }

    Vì sao check trước rồi mới gọi LLM? Vì tiền mất ở bước gọi LLM. Chặn sau
    khi đã gọi thì bạn vừa trả tiền vừa trả lỗi.

    ``user_id`` do ``verify_api_key`` trả về, nên request không có API key
    hợp lệ sẽ dừng ở 401 trước khi chạm vào bất cứ dòng nào ở đây.
    """
    limiter.check(user_id)
    guard.check(user_id)

    history = store.get_history(user_id)
    result = ask_llm(payload.question, history)

    store.append(user_id, "user", payload.question)
    store.append(user_id, "assistant", result["answer"])

    guard.record(user_id, result["cost_usd"])

    log_event(
        "ask_completed",
        user_id=user_id,
        tokens_in=result["tokens_in"],
        tokens_out=result["tokens_out"],
        cost_usd=result["cost_usd"],
    )

    return {
        "answer": result["answer"],
        "user_id": user_id,
        "history_length": len(history),
        "cost_usd": result["cost_usd"],
        "tokens": {"in": result["tokens_in"], "out": result["tokens_out"]},
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
