# main.py
import time

from dotenv import load_dotenv
from fastapi import FastAPI, Request

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


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %s (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
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
