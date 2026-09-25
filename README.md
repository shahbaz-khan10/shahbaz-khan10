# FCT Garments ERP — Phase 1: AMS

Auth & Admin Management System (AMS) for a single-factory garments ERP. Provides the central
identity service, RBAC, audit trail and all business master data that later modules
(merchandising, planning, stores, cutting, sewing, quality) will build on.

Built from scratch for this factory — deliberately **not** multi-tenant. It follows the
conventions of the legacy ERP-2.0 codebase (auth-service pattern, `seed-on-boot`,
compose profiles, Makefile) but re-implements them for a hardcoded single tenant so that
`employees`, `roles`, `permissions` and `audit` stay simple.

```
┌──────────────┐     http /api/* (JWT Bearer)      ┌──────────────────────────────┐
│  Next.js APP │ ────────────────────────────────► │  Django + django-ninja       │
│  (AMS UI)    │      /.well-known/jwks.json ◄──── │  AUTH · Rbac · Audit · EPM   │
└──────────────┘                                   └──────────┬───────────────────┘
                                                              │ SQLite (dev) / Postgres
                                                              ▼
                                                    ┌──────────────────────┐
                                                    │ employees · masters  │
                                                    └──────────────────────┘
```

## What's included

- **Identity**: username/email + password login (sliding-window rate limit, account lockout),
  RS256 JWT with refresh-token rotation, server-side refresh/hash + blacklist, JWKS at
  `/.well-known/jwks.json`, change/reset password, `POST /api/auth/logout`.
- **RBAC**: `Service → Permission (module.entity.action)` catalog, roles, role→permission
  matrix, user→role assignment, codes like `ams.item.approve`. Super Admin users bypass.
- **Audit**: every create/update/delete (soft) on domain tables + login/logout/password
  events are written to `AuditLog` with actor + client IP, viewable at `GET /api/audit/logs`.
- **Organization**: company profile, departments, designations, production lines, employees.
- **Business masters**: currencies + exchange rates, buyers, suppliers, item categories,
  items, units of measure + conversions, colors, sizes + size groups, warehouses.
- **UI**: Next.js App Router dashboard with the full list of master screens, generic CRUD
  tables, permission-gated navigation/actions, roles permission-matrix editor, audit viewer.
- **Deploy**: Docker images + compose profiles, Makefile, seeds, 33 pytest tests.

## Repo layout

```
auth-service/Backend/
  Dockerfile, requirements.txt
  src/
    manage.py, pytest.ini
    core/        settings, Ninja API wiring, URLs
    common/      base models, pagination, CRUD-router factory
    authentication/  User, JWT utils, JWKS, rate limit, login API
    permissions/ Service, Permission, Role (+ API + RBAC + seeds)
    employees/   CompanyProfile, Department, Designation, ProductionLine, Employee (+ API)
    masters/     Currency, Buyer, Item, ... 15 master models (+ API)
    audit/       AuditLog, middleware, signals, viewer
    tests/       pytest suite (auth, rbac, crud, audit)
ams/frontend/    Next.js 14 + Tailwind + TypeScript
infra/           docker-compose.yml (profiles: infra / app)
Makefile         shortcuts for setup, run, test, docker
```

## Quickstart

### Local (fastest — SQLite)

Requirements: Python 3.12, Node 20.

```bash
# backend
make backend-install            # or: python -m venv auth-service/Backend/.venv && pip install -r auth-service/Backend/requirements.txt
make backend-migrate
make backend-seed               # creates super admin: admin / SuperAdmin@123 (env-overridable)
make backend-run                # http://127.0.0.1:8000  — API docs at /api/docs/

# frontend (new terminal)
make frontend-install
make frontend-dev               # http://127.0.0.1:3000
```

Open http://127.0.0.1:3000, sign in as `admin` / `SuperAdmin@123`.

### Docker (Postgres + Redis)

```bash
docker compose -f infra/docker-compose.yml --profile app up -d --build   # full stack
docker compose -f infra/docker-compose.yml --profile infra up -d         # infra only (hybrid dev)
docker compose -f infra/docker-compose.yml --profile app logs -f
```

`backend-setup` runs migrate + all three seeds automatically on first start.

## Configuration (backend)

| Env var | Default | Purpose |
| --- | --- | --- |
| `DEBUG` | `false` | Django debug |
| `SECRET_KEY` | dev key | Django secret (set in prod) |
| `USE_SQLITE` / `DATABASE_URL` | SQLite | `postgres://user:pass@host:5432/db` for Postgres |
| `REDIS_URL` | in-process | Optional Redis for rate limit/cache |
| `ACCESS_TOKEN_EXPIRY_HOURS` / `REFRESH_TOKEN_EXPIRY_DAYS` | 1 / 7 | Token lifetimes |
| `JWT_PRIVATE_KEY_PATH` / `JWT_PUBLIC_KEY_PATH` | in-memory keypair | RS256 key files (persist in prod) |
| `SUPER_ADMIN_USERNAME` / `SUPER_ADMIN_PASSWORD` / `SUPER_ADMIN_EMAIL` | admin / SuperAdmin@123 | Seed credentials |
| `CORS_ALLOW_ALL_ORIGINS` | true | Dev convenience |

Frontend: `API_BASE_URL` (default `http://127.0.0.1:8000/api`). Tokens are kept in httpOnly
cookies; the app refreshes them automatically via `/auth/refresh`.

## API map (all under `/api`)

| Path | What |
| --- | --- |
| `POST /auth/login` · `/refresh` · `/logout` · `/change-password` · `/reset-password`, `GET /auth/me` | identity |
| `GET /services`, `GET /permissions` | permission catalog |
| `GET/POST/PATCH/DELETE /users` · `/roles`, `PUT /roles/{id}/permissions`, `POST /users/{id}/roles` | users & roles |
| `GET/POST/PATCH/DELETE /departments` · `/designations` · `/production-lines` · `/employees` | org |
| `GET/POST/PATCH/DELETE /buyers` · `/suppliers` · `/item-categories` · `/items` · `/units-of-measure` · `/uom-conversions` · `/colors` · `/sizes` · `/size-groups` · `/currencies` · `/exchange-rates` · `/warehouses` | business masters |
| `GET /audit/logs`, `GET/PUT /company` | audit + company profile |
| `/.well-known/jwks.json` | JWKS (for microservice JWT verification) |

List endpoints support `page`, `page_size`, `search`, plus FK / boolean filters.
Every master follows `create / view / edit / delete (+ approve)` gated by `ams.<entity>.<action>`.

## Permissions & roles

Seeded catalog: `ams.*` services with 78 permissions (`view/ create/ edit/ delete` per master,
plus `item.approve`, `role.manage`, `company_profile.edit`). Seeds ship 10 roles:
Super Admin, Admin, Merchandiser, Store Keeper, Production Manager, Line Supervisor,
QC Inspector, HR Officer, Accountant, Viewer. Adjust them in
`permissions/management/commands/seed_catalog.py` then re-run `make backend-seed`.

## Tests

```bash
make backend-test     # 33 tests: auth flows, RBAC enforcement, CRUD soft-delete, audit trail
```

## Roadmap

1. **Phase 2 – Merchandising (MMS)**: buyers, style/order development, BOMs.
2. **Phase 3 – Planning & Scheduling (PMS)**: production orders, line loading, capacity.
3. **Phase 4 – Stores/Inventory**: GRN, issues, stock, WMS.
4. **Phase 5 – Cutting/Sewing/Finishing data capture + QMS**.

New modules follow the same pattern: a `Service` row, a permission catalog for their entities
in `seed_catalog.py`, a Django app with `models.py` + `api.py` (via `make_crud_router`), and
frontend screens via the generic `Table`/`MasterScreen` components.