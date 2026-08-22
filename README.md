# FastAPI Starter

A small, production-oriented FastAPI starter focused on **reliability, security, and clean integration** rather than feature count.

This repository serves two purposes:

1. a dependable starting point for future backend projects;
2. a portfolio-quality example of practical backend engineering.

The project is still being hardened. The business-specific example domain has been removed; the remaining Google-specific OAuth flow is intentionally scheduled for provider-neutral cleanup before the starter is considered ready.

## Product Principle

> Prefer one feature that works end-to-end over many features that are only partially integrated.

Every addition should have a concrete use case, fit the existing architecture, and be covered by the appropriate tests. Infrastructure must not be added only because it is common in production systems.

In particular, **Redis, Kafka, Prometheus, Celery, and similar infrastructure are not part of the default target**. They should be introduced only when a real feature creates a clear requirement for them.

## Target

The finished starter should provide a balanced foundation for building backend services without becoming an enterprise framework.

The target includes:

- FastAPI application lifecycle with explicit configuration;
- PostgreSQL with Aerich-managed migrations;
- JWT authentication;
- role-based authorization with secure defaults;
- a provider-agnostic OAuth architecture with at least one working reference provider;
- Docker-based local development;
- tests for security-critical and core application behavior;
- Ruff linting and CI;
- clear operational and development documentation;
- no business-specific domain models in the starter core.

The target explicitly does **not** include speculative infrastructure or abstractions that have no demonstrated use in the starter.

## Current State

The hardening work completed so far establishes the following foundation:

- runtime and configuration blockers have been fixed;
- user registration and authentication behavior has been corrected;
- role-management privilege escalation has been restricted;
- authentication and authorization boundaries have focused regression coverage;
- database schema creation has been removed from application startup;
- Aerich migrations are the schema source of truth;
- application lifecycle and CORS configuration are environment-driven;
- a Dockerfile and Docker Compose development workflow are available;
- Compose runs one-shot migrations against a configured PostgreSQL database before starting the API;
- Pytest, Ruff, and GitHub Actions CI are wired into the project;
- API-level tests cover key authentication and authorization behavior;
- business-specific models, routes, and runtime dependencies have been removed.

### Remaining temporary architecture

The current OAuth implementation is Google-oriented. The final architecture should preserve a working provider as a reference implementation while moving provider-specific behavior behind a small generic interface.

## Project Readiness Definition

The starter is considered ready when all of the following are true:

- a clean checkout can be configured without editing source code;
- local and Docker development paths are documented and work predictably;
- an empty PostgreSQL database can be brought to the latest schema exclusively through migrations;
- application startup never creates or mutates database schemas implicitly;
- JWT registration, login, authentication, inactive-user handling, and authorization work end-to-end;
- role-management rules prevent privilege escalation and are covered by tests;
- OAuth provider code is separated from the authentication core through a small provider abstraction;
- at least one OAuth provider works through that abstraction and is tested at the integration boundary;
- the starter contains no `Project`, `Task`, or other business-specific domain models/routes;
- public and protected route behavior is intentional and tested;
- configuration has secure, understandable defaults and no committed secrets;
- Docker services have deterministic startup dependencies and migrations run once before the API starts;
- linting and tests pass locally and in CI;
- error behavior does not expose internal database or implementation details;
- the repository has concise documentation explaining setup, architecture, extension points, and security decisions;
- optional infrastructure is absent unless a concrete starter capability requires it.

## Roadmap

This roadmap is written to be executable incrementally by a developer or coding agent such as Codex. Complete one phase before expanding the scope.

### Phase 1 — Runtime baseline ✅

**Goal:** make the existing application safe to continue modifying.

Completed work includes runtime fixes, correct ID factories, registration cleanup, OAuth initialization fixes, safer environment examples, startup script cleanup, and a non-destructive Makefile workflow.

**Completion condition:** the application source has no known startup blocker caused by the original baseline and project maintenance commands do not delete source or migration history.

### Phase 2 — Authorization and ownership ✅

**Goal:** make authentication meaningful by enforcing authorization boundaries.

Completed work includes admin-only role management, self/admin user access rules, inactive-user checks, ownership enforcement for the temporary Project/Task domain, safer not-found behavior, and local first-admin bootstrapping.

**Completion condition:** a normal authenticated user cannot elevate privileges or access another user's protected resources through guessed identifiers.

### Phase 3 — Lifecycle and configuration ✅

**Goal:** make application startup and configuration predictable.

Completed work includes explicit database initialization/shutdown, migration-only schema management, environment-driven CORS, centralized settings, and consistent Uvicorn configuration.

**Completion condition:** startup manages connections only; schema changes happen only through migrations; runtime behavior comes from validated settings.

### Phase 4 — Docker and developer workflow ✅

**Goal:** provide one understandable containerized development path.

Completed work includes a non-root application image, one Compose topology for the application, a one-shot migration service against an existing PostgreSQL database, API startup dependencies, and focused Makefile helpers.

**Completion condition:** the container architecture has one responsibility per service and does not duplicate database or migration workflows.

### Phase 5 — Core tests, linting, and CI ✅

**Goal:** prove that the integrated core behaves correctly before adding more architecture.

Completed work includes focused Pytest API tests, Ruff, GitHub Actions, PostgreSQL migration validation in CI, and activation of the temporary Project/Task routes used for ownership testing.

**Completion condition:** security-critical behaviors are represented by tests and the same quality checks can run locally and in CI.

### Phase 6 — Stabilize the current core ✅

**Goal:** fix behavior exposed by real end-to-end use before changing the domain architecture.

Completed work:

- exercised authentication and the temporary Project/Task flows end-to-end;
- made registration, login, inactive-user, role-management, delete, and ownership behavior deterministic;
- added transaction boundaries for role mutations and Project/Task race-sensitive operations;
- corrected active-core migration safety, restored user-role uniqueness, and neutralized an obsolete migration blocker;
- verified two coordinated Docker restarts against an existing PostgreSQL database;
- added focused regression coverage without introducing new product features.

Do not introduce new product features in this phase.

**Completion condition:** known core flows are deterministic, security rules have regression coverage, and no unresolved integration bug is being hidden by the next refactor.

### Phase 7 — Remove the example business domain ✅

**Goal:** turn the repository from a task-management example into a genuinely generic starter.

Completed work:

- removed Project and Task models, schemas, repositories, routes, and router registration;
- removed domain-specific tests after preserving their security intent in authentication and authorization coverage;
- removed runtime ORM registration for the example domain and deleted its now-unused layering;
- added an append-only migration that removes Project, Task, and other leftover business-domain tables while preserving authentication data and existing migration history;
- verified that the generated API schema no longer exposes the example business domain;
- avoided replacing Project/Task with another arbitrary example domain.

**Completion condition:** the starter core contains authentication/infrastructure concerns only and no business-specific API surface.

### Phase 8 — Generic OAuth architecture

**Goal:** preserve OAuth capability without coupling the authentication core to Google.

Scope:

- define the smallest useful OAuth provider contract;
- isolate authorization URL generation, callback/token exchange, and normalized user identity behind that contract;
- make provider selection/configuration explicit;
- adapt the existing Google flow as the first reference provider instead of implementing multiple providers;
- keep OAuth account persistence provider-aware but provider-neutral;
- test the provider boundary and core account-link/login behavior without requiring live third-party calls in the normal test suite.

Do **not** add GitHub, Microsoft, Discord, or other providers merely to demonstrate extensibility. A second provider should be added only when there is an actual requirement.

**Completion condition:** authentication core code does not depend on Google-specific behavior, while one reference provider still works through the generic path.

### Phase 9 — Final API and security consistency

**Goal:** make the remaining starter surface coherent enough to reuse without cleanup on every new project.

Scope:

- standardize authentication/authorization errors and HTTP status codes;
- review public-route opt-out behavior and secure-by-default routing;
- review secret/config validation and production-safe defaults;
- review token lifetime and OAuth token persistence decisions;
- remove dead compatibility code and stale configuration;
- keep abstractions only when they reduce duplication or isolate a real boundary.

Do not add rate limiting, Redis-backed sessions, queues, metrics stacks, or background workers unless a concrete capability is selected that requires them.

**Completion condition:** the starter has a small, internally consistent API/security foundation with no known dead paths or misleading configuration.

### Phase 10 — Release-quality documentation and repository polish

**Goal:** make the repository understandable to a new developer without reading the source first.

Scope:

- convert this roadmap-oriented README into the final user-facing README while retaining a short maintenance roadmap;
- document local setup, Docker setup, migrations, authentication, OAuth extension, configuration, tests, and CI;
- document the final project structure and important architectural decisions;
- add repository metadata such as description, topics, and license when selected;
- ensure every advertised feature is implemented and tested before listing it as a capability;
- prepare the first stable release only after the readiness definition above is satisfied.

**Completion condition:** the repository accurately describes what it does, how to run it, how to extend it, and where its intentional boundaries are.

## Guidance for Codex / Coding Agents

When continuing work on this repository, follow these rules:

1. **Read this README and the current code before proposing changes.** Treat the roadmap as intent, but treat the code and tests as the source of truth for current behavior.
2. **Work on one roadmap phase at a time.** Do not mix unrelated refactors, infrastructure, and features into the same patch.
3. **Prefer incremental patches.** Changes should be reviewable, reversible, and narrow enough to understand from the diff.
4. **Preserve working behavior unless the active phase intentionally changes it.** Add or update regression tests when changing security or externally visible behavior.
5. **Do not add speculative infrastructure.** Redis, Kafka, Prometheus, Celery, Elasticsearch, Kubernetes, and similar tools require a concrete feature-level justification.
6. **Do not create abstraction for its own sake.** Introduce an interface/layer only when it isolates a real boundary, reduces meaningful duplication, or enables the stated target architecture.
7. **Keep the starter generic.** Do not introduce a new business domain after Project/Task are removed.
8. **Keep authentication cohesive.** JWT and generic OAuth belong to one authentication design; avoid parallel authentication systems that do not share user/account rules.
9. **Keep migrations authoritative.** Application startup must not generate schemas.
10. **Never advertise unfinished capability.** Documentation should distinguish current behavior from planned work.
11. **Finish integration before expanding scope.** If the current phase exposes a bug, fix it before starting the next phase.
12. **Optimize for maintainability over feature count.** The smallest solution that is secure, understandable, and well integrated is preferred.

## Working With Incremental Patches

This repository includes Makefile helpers for the patch-based workflow used during hardening.

Apply and stage a patch:

```bash
make patch-apply PATCH=/path/to/change.patch
```

Export the current tracked changes relative to a base revision:

```bash
make patch-export PATCH=changes.patch BASE=HEAD
```

Untracked files are intentionally not exported until they are added to Git.

## Current Development Setup

### Local

```bash
python -m venv .venv
source .venv/bin/activate
make install-dev
make env
make migrate
make dev
```

### Docker

```bash
make docker-up
```

The Compose workflow uses `DATABASE_URL` from `.env` to connect to an existing PostgreSQL database, runs migrations once, and starts the API only after migrations succeed. PostgreSQL is not managed by this Compose project. Because the default local URL uses `localhost`, the application containers use host networking; ensure the configured database is running and reachable before starting Compose.

Use the coordinated restart path when validating an existing database:

```bash
make docker-restart
```

This recreates the application containers, reruns pending migrations, and starts the API only after migrations succeed. Raw `docker compose restart` is not the supported workflow because it bypasses Compose startup dependency conditions.

### Quality checks

```bash
make check
```

## Architecture Direction

The desired final dependency direction is intentionally small:

```text
HTTP / FastAPI
      |
      v
Authentication + authorization core
      |
      +---- JWT
      |
      +---- OAuth provider interface ---- reference provider
      |
      v
Persistence / Tortoise ORM
      |
      v
PostgreSQL + Aerich migrations
```

Cross-cutting concerns such as configuration, logging, Docker, testing, and CI support this core rather than becoming independent feature systems.

## Optional Future Extensions

Optional infrastructure should live outside the default starter until justified by a real use case. Examples:

- Redis when a chosen capability genuinely needs shared ephemeral state, caching, rate limiting, or token/session revocation;
- a queue or Kafka when a real asynchronous/event-driven workflow requires delivery semantics beyond in-process background work;
- Prometheus when the project defines operational metrics that are actually useful to monitor.

These are **extension points, not roadmap requirements**.

## Status

The project is currently in the hardening/refactoring stage. Phases 1–7 are implemented; Phase 8 is the next engineering phase. The repository should not be presented as a finished generic starter until the readiness definition is satisfied.
