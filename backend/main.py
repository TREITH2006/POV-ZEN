from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import get_settings
import models  # noqa: F401 — ensures all models are registered on Base.metadata
from rate_limit import limiter
from routes import announcements, auth, documents, food, groups, issues, join_requests, rent, terms, website_issues

settings = get_settings()

_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

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


@app.middleware("http")
async def enforce_trusted_origin_for_mutations(request: Request, call_next):
    # CSRF backstop, specifically needed because the deployed configuration
    # uses COOKIE_SAMESITE=none (required when frontend and API are on
    # unrelated domains, e.g. two separate *.onrender.com subdomains, which
    # browsers treat as cross-site since onrender.com is a public suffix).
    # SameSite=None deliberately sends the auth cookie on cross-site
    # requests, so it provides none of the CSRF protection SameSite=Strict/
    # Lax normally give for free. CORS does not fill that gap either — CORS
    # only blocks a cross-site script from *reading* a response, not from
    # *sending* a state-changing request in the first place (a classic
    # cross-site <form> POST, e.g. to the multipart issue/document upload
    # endpoints, is unaffected by CORS entirely).
    #
    # Browsers attach an Origin header to every cross-site request and to
    # same-origin fetch/XHR requests using an unsafe method (Fetch spec), so
    # checking it here catches both a forged cross-site form post and a
    # forged cross-site fetch — without needing a CSRF token or any
    # frontend change. A request with no Origin header at all (non-browser
    # clients: curl, server-to-server calls, the test suite) is not a
    # browser-driven CSRF vector and is left alone, same as standard
    # Origin-validation CSRF defenses (e.g. Django's) do.
    if request.method in _UNSAFE_METHODS:
        origin = request.headers.get("origin")
        if origin is not None and origin not in settings.cors_origin_list:
            return JSONResponse(status_code=403, content={"detail": "Origin not allowed"})
    return await call_next(request)

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
