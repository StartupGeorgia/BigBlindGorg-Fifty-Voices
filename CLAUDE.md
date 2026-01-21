# Fifty Voices

Open-source AI voice agent platform for building and deploying phone agents that handle inbound/outbound calls for appointments, questions, and lead qualification.

## Project Structure

```
fifty-voices/
├── backend/                    # FastAPI Python API
│   ├── app/
│   │   ├── api/               # REST endpoints (agents, calls, crm, telephony, etc.)
│   │   ├── core/              # Config, auth, caching, rate limiting
│   │   ├── db/                # SQLAlchemy session and base models
│   │   ├── middleware/        # CORS, error handling, logging
│   │   ├── models/            # Database models (Agent, User, Call, Contact, etc.)
│   │   ├── services/          # Business logic, AI integration, telephony providers
│   │   │   ├── telephony/     # Telnyx/Twilio implementations
│   │   │   └── tools/         # Built-in agent tools (contacts, appointments, etc.)
│   │   └── main.py            # FastAPI app entry point
│   ├── migrations/            # Alembic database migrations
│   ├── tests/                 # pytest test suite
│   └── scripts/               # Backend utilities (check.sh)
│
├── frontend/                   # Next.js 15 React app
│   ├── src/
│   │   ├── app/               # Next.js App Router pages
│   │   │   └── dashboard/     # Main UI (agents, calls, campaigns, crm, settings)
│   │   ├── components/        # React components
│   │   │   └── ui/            # shadcn/ui component library
│   │   ├── lib/               # API clients, utilities, integrations config
│   │   ├── hooks/             # Custom React hooks
│   │   └── widget/            # Embeddable voice widget source
│   ├── public/widget/         # Compiled widget distribution
│   └── tests/                 # Frontend tests (vitest)
│
├── scripts/                    # Project-level scripts (check-all.sh)
├── docker-compose.yml          # PostgreSQL 17 + Redis 7
└── Makefile                    # Common commands
```

## Organization Rules

**Keep code organized and modularized:**
- API routes → `backend/app/api/`, one file per resource
- Database models → `backend/app/models/`, one model per file
- Services/business logic → `backend/app/services/`
- React pages → `frontend/src/app/`, following Next.js App Router conventions
- React components → `frontend/src/components/`, one component per file
- UI primitives → `frontend/src/components/ui/` (shadcn/ui)
- API clients → `frontend/src/lib/api/`
- Tests → Next to the code they test or in `/tests`

## Code Quality - Zero Tolerance

After editing ANY file, run:

```bash
# Full check (backend + frontend)
make check

# Or run separately:
# Backend only
cd backend && bash scripts/check.sh

# Frontend only
cd frontend && npm run check
```

This runs:
- **Backend**: `ruff check`, `ruff format --check`, `mypy`, `pytest`
- **Frontend**: `eslint`, `tsc --noEmit`, `prettier --check`

Fix ALL errors/warnings before continuing.

## Development

```bash
# Start services (postgres, redis)
make dev

# Backend: cd backend && uv run uvicorn app.main:app --reload
# Frontend: cd frontend && npm run dev
```
