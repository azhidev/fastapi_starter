# FastAPI Starter

A small, production-oriented FastAPI foundation focused on authentication, authorization, predictable migrations, secure configuration, and an understandable development workflow.

The starter deliberately excludes business-specific example models and speculative infrastructure. It provides a reusable authentication core that can be extended by a real application rather than a framework that must first be dismantled.

## Status

The implementation roadmap through release-quality documentation is complete. The current baseline includes JWT authentication, role-based authorization, provider-neutral OAuth with a Google reference adapter, PostgreSQL migrations, Docker application services, tests, linting, and CI.

The repository has not been tagged as a release and no license has been selected yet. Choose a license before public redistribution.

## Features

- FastAPI lifecycle with explicit database connection startup and shutdown
- PostgreSQL persistence through Tortoise ORM
- Aerich-managed, migration-only schema changes
- Password registration and Argon2 password hashing
- JWT access tokens with bounded, configurable lifetime
- Active-user enforcement and secure-by-default private routes
- Role-based authorization with last-active-admin protection
- Provider-neutral OAuth account linking and JWT login
- Google OAuth reference adapter
- Stateless OAuth CSRF protection through a short-lived HttpOnly state cookie
- Environment-driven CORS and production configuration validation
- Non-root Docker image and deterministic migration-before-API startup
- Pytest regression coverage, Ruff, and GitHub Actions CI
- No Project, Task, or other business-domain API surface
- No Redis, queues, workers, metrics stack, or other optional infrastructure by default

## Requirements

- Python 3.10
- PostgreSQL; CI and development validation use PostgreSQL 16
- `make`
- Docker with Compose support for the optional containerized application workflow

PostgreSQL is an external dependency. This repository's Compose file does not create or own a database container.

## Quick Start

### 1. Create the environment

```bash
python -m venv .venv
source .venv/bin/activate
make install-dev
make env
```

`make env` copies `.env.example` to `.env` without overwriting an existing file.

Generate a strong application secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set at least these values in `.env`:

```env
APP_ENV=development
DATABASE_URL=postgres://USER:PASSWORD@localhost:5432/fastapi_starter
SECRET=replace-with-the-generated-secret
```

The target database must already exist and be reachable.

### 2. Apply migrations

```bash
make migrate
```

### 3. Run the API

```bash
make dev
```

The default endpoints are:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI document: `http://localhost:8000/openapi.json`

## Docker Workflow

Compose builds and runs only two application services:

1. `migrate` applies pending Aerich migrations and exits;
2. `api` starts only after `migrate` exits successfully.

Both services use `DATABASE_URL` from `.env`. They use host networking so a database URL containing `localhost` reaches PostgreSQL on the host.

Start the application:

```bash
make docker-up
```

Inspect status and logs:

```bash
make docker-ps
make docker-logs
```

Use the coordinated restart command when validating an existing database:

```bash
make docker-restart
```

This recreates the application containers and reruns pending migrations before starting the API. Raw `docker compose restart` is not the supported workflow because it bypasses Compose startup dependency conditions.

Stop the application:

```bash
make docker-down
```

`APP_PORT` selects the API port in the host-networked Compose workflow. It defaults to `8000`.

## Configuration

Settings are defined and validated in `app/core/config.py`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `FastAPI Starter` | OpenAPI and service name |
| `APP_VERSION` | `1.0.0` | Reported application version |
| `APP_ENV` | `development` | `development`, `test`, or `production` |
| `DEBUG` | `false` | Enables local Uvicorn reload and debug logging |
| `HOST` | `0.0.0.0` | Uvicorn bind host |
| `PORT` | `8000` | Uvicorn port; must be between 1 and 65535 |
| `APP_PORT` | `8000` | API port used by Compose |
| `DATABASE_URL` | local PostgreSQL URL | Tortoise and Aerich database connection |
| `SECRET` | required | JWT signing secret; minimum 32 characters |
| `JWT_LIFETIME_SECONDS` | `86400` | JWT lifetime; greater than zero and at most 30 days |
| `CORS_ORIGINS` | local frontend origins | Comma-separated allowed origins |
| `CORS_ALLOW_CREDENTIALS` | `true` | Enables credentialed CORS requests |
| `OAUTH_PROVIDER` | unset | Set to `google` to enable the reference provider |
| `OAUTH_REDIRECT_URI` | generic local callback | Registered OAuth callback URL |
| `GOOGLE_CLIENT_ID` | unset | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | unset | Google OAuth client secret |

### Production validation

When `APP_ENV=production`, startup rejects:

- `DEBUG=true`;
- known development/test secrets or low-diversity secrets;
- incomplete OAuth provider credentials;
- provider credentials without explicit `OAUTH_PROVIDER` selection;
- non-HTTPS OAuth callback URLs when OAuth is enabled;
- wildcard CORS origins when credentialed CORS is enabled.

Secrets belong in the deployment environment or a secret manager. Do not commit `.env`.

## Database and Migrations

Aerich migrations are the only schema source of truth. Application startup opens connections but never creates or modifies tables.

Apply pending migrations locally:

```bash
make migrate
```

Apply them through the application image:

```bash
make docker-migrate
```

After changing a Tortoise model, generate a migration:

```bash
make migration
```

Review generated SQL before applying it, especially destructive operations and authorization-related constraints.

Do not run `make init` for a normal checkout. Aerich is already initialized; that target exists only for establishing migration metadata in a new derivative repository.

A clean PostgreSQL database has been validated through the complete migration chain. The final public schema contains only:

- `user`
- `role`
- `user_role`
- `oauthaccount`
- `aerich`

Historical migrations remain append-only for existing-database compatibility. Forward cleanup migrations remove the former example-domain tables.

## Authentication

### Register

```http
POST /api/v1/auth/register
Content-Type: application/json
```

```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "strong-password"
}
```

Registration normalizes email addresses, rejects extra persistence fields, hashes the password with Argon2, and returns `409` for duplicate usernames or emails.

### Password login

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded
```

Send `username` and `password` form fields. A successful response is:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

Use the token on private routes:

```http
Authorization: Bearer <jwt>
```

JWTs include issued-at, expiration, subject, and access-token type claims. Missing credentials, invalid credentials, inactive users, and insufficient roles have deterministic status codes and generic responses.

## Roles and First Admin

New users have no roles. After registering the first trusted account, bootstrap it locally:

```bash
make bootstrap-admin ADMIN_EMAIL=admin@example.com
```

The command requires an existing active user. It creates the `admin` role when necessary and assigns it idempotently.

Authorization rules include:

- users may read their own account and roles;
- admins may list users, inspect other users, and manage roles;
- normal users cannot assign themselves roles;
- the `admin` role cannot be deleted;
- removing roles cannot leave the system without an active administrator;
- malformed user and role identifiers are rejected before reaching the ORM.

## OAuth

OAuth is disabled until a provider is explicitly selected and configured.

```env
OAUTH_PROVIDER=google
OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/auth/oauth/callback
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

Register the exact redirect URI with Google. Production OAuth callback URLs must use HTTPS.

The generic endpoints are:

- `GET /api/v1/auth/oauth/login`
- `GET /api/v1/auth/oauth/callback`

The login endpoint creates a random OAuth `state` value, sends it to the provider, and stores it in a short-lived HttpOnly, SameSite cookie. The callback rejects missing or mismatched state before exchanging the authorization code.

After a successful exchange, the core:

1. normalizes the provider identity;
2. reuses an existing provider/subject link when present;
3. otherwise links an active local account with the same normalized email;
4. creates an OAuth-only user when no account exists;
5. returns the same JWT shape as password login.

Provider access and refresh tokens are intentionally not persisted. They are used only inside the provider adapter to retrieve identity. `oauthaccount` stores the provider name, provider subject, and local user link.

The normal test suite replaces the provider boundary and never calls Google. The Google adapter is the only reference provider; additional providers should be added only for an actual application requirement.

## API Surface

| Method | Path | Access |
| --- | --- | --- |
| `GET` | `/` | Public |
| `POST` | `/api/v1/auth/register` | Public |
| `POST` | `/api/v1/auth/login` | Public |
| `GET` | `/api/v1/auth/oauth/login` | Public; configured provider required |
| `GET` | `/api/v1/auth/oauth/callback` | Public; valid OAuth state required |
| `GET` | `/api/v1/users/me` | Active user |
| `GET` | `/api/v1/users/{user_id}` | Self or admin |
| `GET` | `/api/v1/users/{user_id}/roles` | Self or admin |
| `POST` | `/api/v1/users/{user_id}/roles/{role_name}` | Admin |
| `DELETE` | `/api/v1/users/{user_id}/roles/{role_name}` | Admin |
| `GET` | `/api/v1/roles/` | Admin |
| `POST` | `/api/v1/roles/` | Admin |
| `DELETE` | `/api/v1/roles/{role_id}` | Admin |
| `GET` | `/api/v1/admin/` | Admin |

Private access is the application-wide default. Public operations explicitly opt out through the `@public` marker. Documentation paths are intentionally public.

## Architecture

```text
HTTP / FastAPI
      |
      +-- secure-by-default authentication dependency
      |
      +-- password login ------ Argon2 + JWT
      |
      +-- OAuth core ---------- provider contract ---------- Google adapter
      |
      +-- role authorization
      |
      v
Tortoise ORM
      |
      v
PostgreSQL + Aerich migrations
```

OAuth provider code normalizes external responses. The provider-neutral service owns local account linking. Models contain persistence rules. FastAPI routes translate core outcomes into HTTP responses.

## Project Structure

```text
app/
├── api/
│   ├── middlewares.py       # request timing middleware
│   └── v1/users.py          # authentication, users, roles, and admin routes
├── core/
│   ├── config.py            # environment settings and production validation
│   ├── identifiers.py       # validated API path identifier types
│   └── security.py          # JWT, password, global auth, and role dependencies
├── db/tortoise.py           # runtime ORM and Aerich configuration
├── models/
│   ├── oauth.py             # provider identity links
│   └── user.py              # users and roles
├── oauth/
│   ├── factory.py           # explicit provider selection
│   ├── google.py            # Google reference adapter
│   ├── service.py           # provider-neutral account linking
│   └── types.py             # provider contract and normalized identity
└── schemas/user.py          # public request and response models

migrations/models/           # append-only Aerich migration history
tests/                       # API, configuration, OAuth, and security regressions
tools/bootstrap_admin.py     # first-admin bootstrap command
main.py                      # FastAPI application and lifecycle
```

## Security Decisions

- Private routes are the global default; public routes require an explicit marker.
- Invalid bearer tokens are rejected consistently, including when supplied to public routes.
- Password login performs dummy Argon2 verification for missing and inactive users to reduce username timing disclosure.
- Inactive users cannot use existing JWT or OAuth identities.
- Role mutations are transactional and serialize last-admin checks.
- Authentication errors do not include database or provider internals.
- JWT lifetime is bounded and centralized.
- OAuth state is validated without adding a shared session store.
- Third-party OAuth tokens are not retained because no current capability needs them.
- Credentialed CORS cannot be combined with wildcard origins.
- Production configuration rejects common insecure combinations at startup.
- Optional infrastructure remains absent until a concrete feature requires it.

## Tests and CI

Run all local quality checks:

```bash
make check
```

Or run them separately:

```bash
make lint
make test
```

The API suite uses a disposable SQLite database for fast, isolated behavior tests. Migration behavior is validated separately against PostgreSQL.

GitHub Actions runs on pushes and pull requests. CI:

1. starts PostgreSQL 16;
2. installs development dependencies;
3. runs Ruff;
4. applies the complete Aerich migration history to PostgreSQL;
5. runs the Pytest suite.

Normal tests do not require third-party network access or OAuth credentials.

## Common Commands

| Command | Purpose |
| --- | --- |
| `make env` | Create `.env` from `.env.example` if absent |
| `make install` | Install runtime dependencies |
| `make install-dev` | Install development and test dependencies |
| `make run` | Run without reload |
| `make dev` | Run with debug reload |
| `make migrate` | Apply pending Aerich migrations |
| `make migration` | Generate a migration from model changes |
| `make bootstrap-admin ADMIN_EMAIL=...` | Assign the first admin role |
| `make docker-up` | Build and start migrations/API |
| `make docker-restart` | Coordinated migration-aware restart |
| `make docker-down` | Stop application containers |
| `make docker-logs` | Follow API logs |
| `make check` | Run Ruff and Pytest |
| `make clean` | Remove Python and test caches |

Patch-oriented maintenance helpers remain available through `make patch-apply` and `make patch-export`.

## Extending the Starter

- Add business models, schemas, migrations, and routers in the derivative application, not in the reusable starter core.
- Keep migration history append-only once a database has been shared.
- Add an OAuth provider by implementing `OAuthProvider`; do not duplicate account-linking logic.
- Add infrastructure only when a selected capability requires it.
- Preserve private-by-default routing and add regression tests for security behavior.
- Avoid abstractions that do not isolate a real boundary or reduce meaningful duplication.

## Maintenance Roadmap

The original hardening roadmap is complete. Ongoing maintenance should remain small and evidence-driven:

- perform a deployment-specific live Google OAuth smoke test when credentials are available;
- update pinned dependencies deliberately and address upstream deprecation warnings;
- select a license and create a tagged release when repository ownership chooses the release terms;
- add infrastructure or another OAuth provider only for a concrete application requirement.

## License

No license has been selected. Add the chosen license before publishing or redistributing the repository as an open-source project.
