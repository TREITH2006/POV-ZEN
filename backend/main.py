from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import get_settings
import models  # noqa: F401 — ensures all models are registered on Base.metadata
from rate_limit import limiter
from routes import announcements, auth, documents, food, groups, issues, join_requests, rent, terms, website_issues

settings = get_settings()

# Schema is owned by Alembic migrations (backend/alembic/), not by
# Base.metadata.create_all — run `alembic upgrade head` before first start.
app = FastAPI(title="POV-ZEN API", version="1.0.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(join_requests.router)
app.include_router(announcements.router)
app.include_router(food.router)
app.include_router(issues.router)
app.include_router(rent.router)
app.include_router(documents.router)
app.include_router(groups.router)
app.include_router(terms.router)
app.include_router(website_issues.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
