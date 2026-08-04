# main.py
import json
import time

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response

from utils.logging import get_logger, setup_logging

from admin.router import router as admin_users_router
from admin_memberships.router import router as admin_memberships_router
from admin_payments.router import router as admin_payment_router
from admin_professionals.router import router as admin_pf_router
from article_comments.router import router as article_comments_router
from article_reviews.router import router as article_reviews_router
from articles.router import router as articles_router
from auth.router import router as auth_router
from dashboard.router import router as admin_dashboard_router
from database import create_db_and_tables
from professionals.router import router as professionals_router
from professional_reviews.router import router as professional_reviews_router
from stripe_local.router import router as stripe_router
from users.router import router as me_settings_router
from articles_web.router import router as articles_web_router
load_dotenv()
setup_logging()

logger = get_logger("aleppi.request")

app = FastAPI(
    title="ALEPPI BACKEND",
    version="0.1.0",
)

# Claves cuyo valor se enmascara antes de loguear un body (passwords, tokens,
# datos de tarjeta, etc.). Comparación case-insensitive.
_SENSITIVE_KEYS = {
    "password", "token", "secret", "authorization", "card", "cvc", "cvv",
    "access_token", "refresh_token", "client_secret", "api_key", "apikey",
    "card_number", "cardnumber", "ssn",
}
_MAX_BODY_LOG_LEN = 2000


def _mask_sensitive(data):
    if isinstance(data, dict):
        return {
            key: ("***" if key.lower() in _SENSITIVE_KEYS else _mask_sensitive(value))
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [_mask_sensitive(item) for item in data]
    return data


def _format_body_for_log(raw: bytes, content_type: str) -> str:
    if not raw:
        return ""
    if "application/json" not in (content_type or ""):
        return f"<{len(raw)} bytes, {content_type or 'unknown content-type'}>"
    try:
        parsed = json.loads(raw)
    except ValueError:
        return f"<{len(raw)} bytes, invalid json>"
    text = json.dumps(_mask_sensitive(parsed), ensure_ascii=False)
    if len(text) > _MAX_BODY_LOG_LEN:
        text = text[:_MAX_BODY_LOG_LEN] + "...(truncated)"
    return text


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()

    # Los uploads multipart (fotos, licencias) no se leen ni loguean: forzar
    # la lectura completa del body rompería el streaming a disco de UploadFile.
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        req_body_log = "<multipart/form-data, no logueado>"
    else:
        req_raw = await request.body()
        req_body_log = _format_body_for_log(req_raw, content_type)

    response = await call_next(request)

    resp_raw = b""
    async for chunk in response.body_iterator:
        resp_raw += chunk
    resp_body_log = _format_body_for_log(resp_raw, response.headers.get("content-type"))

    response_headers = dict(response.headers)
    response_headers.pop("content-length", None)
    response = Response(
        content=resp_raw,
        status_code=response.status_code,
        headers=response_headers,
        media_type=response.media_type,
    )

    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %s (%.1f ms) | req=%s | res=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
        req_body_log,
        resp_body_log,
    )
    return response

app.include_router(auth_router)
app.include_router(professionals_router)
app.include_router(professional_reviews_router)
app.include_router(admin_users_router)
app.include_router(stripe_router)
app.include_router(admin_dashboard_router)
app.include_router(admin_pf_router)
app.include_router(admin_payment_router)
app.include_router(admin_memberships_router)
app.include_router(articles_router)
app.include_router(article_reviews_router)
app.include_router(me_settings_router)
app.include_router(article_comments_router)
app.include_router(articles_web_router)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()


@app.get("/", tags=["health"])
def root():
    return {"message": "OK, API corriendo"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
