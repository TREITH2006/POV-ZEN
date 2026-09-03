# POV-ZEN

A private PG (Paying Guest accommodation) management web application. Every PG
operates as an isolated group: an Owner manages one PG group; Users join a
group only after the Owner approves their request, and never see another
group's data.

## Stack

- **Frontend:** HTML, CSS, vanilla JavaScript (mobile-first, no build step)
- **Backend:** Python, FastAPI, SQLAlchemy, Alembic
- **Database:** SQLite (dev) — PostgreSQL-ready (swap `DATABASE_URL`)
- **Auth:** email/password (bcrypt-hashed), JWT session cookie (httpOnly)
- **Testing:** pytest + FastAPI TestClient (28 tests, incl. mandatory
  cross-group isolation checks)

## Project Structure

```
pov-zen/
├── backend/
│   ├── main.py            FastAPI app + router wiring
│   ├── config.py          Settings (env-var driven)
│   ├── database.py        SQLAlchemy engine/session
│   ├── models/            ORM models (one file per entity)
│   ├── schemas/           Pydantic request/response schemas
│   ├── routes/            Thin HTTP controllers
│   ├── services/          Business logic + group-isolation enforcement
│   ├── auth/              Password hashing, JWT, identity dependency
│   ├── utils/             ID/access-key generation
│   ├── alembic/           Database migrations
│   ├── uploads/           Local file storage (gitignored contents)
│   └── tests/             pytest suite
├── frontend/
│   ├── index.html          Login / registration
│   ├── access-key.html     One-time display of a new PG's access key
│   ├── terms.html          Terms & Conditions gate
│   ├── join.html           Access-key entry for unapproved Users
│   ├── user-dashboard.html Resident dashboard
│   ├── owner-dashboard.html Owner dashboard
│   ├── css/style.css
│   └── js/                 api.js (fetch wrapper), ui.js (shared helpers),
│                            one file per page
├── .env.example
└── requirements.txt → backend/requirements.txt
```

## Local Setup

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp ../.env.example .env
# Edit .env: at minimum, set a real SECRET_KEY
#   python -c "import secrets; print(secrets.token_urlsafe(32))"
alembic upgrade head
uvicorn main:app --reload --port 8000
```

The API is now at `http://127.0.0.1:8000`. Interactive docs at
`http://127.0.0.1:8000/docs`.

### 2. Frontend

The frontend is static — no build step. Serve it with any static file
server, e.g.:

```bash
cd frontend
python -m http.server 5500
```

Open `http://127.0.0.1:5500`. If you serve the frontend from a different
host/port, update `CORS_ORIGINS` in `backend/.env` accordingly, and set
`window.POV_ZEN_API_BASE` at the top of `frontend/js/api.js` (or before it
loads) if the backend isn't at `http://127.0.0.1:8000`.

### 3. Tests

```bash
cd backend
source .venv/Scripts/activate
python -m pytest tests/ -v
```

## Database Migrations

Schema changes are managed by Alembic, not `create_all`:

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

## Key Design Notes

- **Group isolation** is enforced entirely server-side: every group-scoped
  query filters by the `group_id` derived from the authenticated session,
  never from a client-supplied value. See `backend/services/*.py`.
- **Access Key vs Group ID**: the Group ID is a non-secret identifier; the
  Access Key is a secret, owner-rotatable credential (stored as a keyed hash)
  that only lets a user *submit* a join request — an Owner must still approve
  it before any group data becomes visible.
- **File uploads** are validated by sniffing actual file content (magic
  bytes), not filename or declared MIME type, and stored under random
  filenames outside any public/static path.
- **Rate limiting** guards login, registration, and join-request submission
  (the realistic brute-force targets) — see `backend/rate_limit.py`. It's
  disabled under `ENVIRONMENT=test` since the test client's fake IP would
  otherwise trip shared limits across unrelated tests.
- **No AI/external API integration** is included — the original spec
  referenced a public "free API keys" GitHub repo for experimentation; that
  was deliberately not used (using shared/leaked third-party API keys is a
  ToS violation and a security risk). Nothing in the functional requirements
  needs an external AI API, so it was left out of this build.

## Not Yet Implemented (by design, for a later iteration)

- Google OAuth login (email/password is fully functional today; the auth
  layer is isolated in `backend/auth/` so OAuth can be added without
  touching business logic)
- Cloud/object file storage (local disk today, behind an abstraction in
  `backend/services/storage_service.py`)
- Actual deployment to a free-tier host (architecture is portable/env-driven,
  but no live deployment has been performed)
