# ADR-001: Backend Framework Choice

**Status:** Accepted
**Date:** 2025-12-21
**Decision Makers:** System Architecture Team

---

## Context

We need to select a backend framework for the PMS-Webapp that will:
- Handle high-concurrency webhook processing from 5 channel platforms
- Provide REST API for frontend (Next.js) and mobile apps
- Support background task processing for channel synchronization
- Enable real-time features (booking notifications, status updates)
- Integrate with Supabase PostgreSQL and Redis
- Scale to 1000+ properties and 10000+ bookings/month

## Decision Drivers

1. **Async Performance**: High-volume webhook handling requires non-blocking I/O
2. **Developer Productivity**: Fast development with good tooling
3. **Type Safety**: Catch errors at compile/lint time
4. **API Documentation**: Auto-generated OpenAPI specs
5. **Ecosystem**: Background tasks, caching, ORM support
6. **Team Expertise**: Existing skills and hiring market

## Options Considered

### Option 1: FastAPI (Python)

**Pros:**
- Native async/await with excellent performance
- Automatic OpenAPI documentation from type hints
- Pydantic v2 for robust data validation
- Rich ecosystem (Celery, SQLAlchemy, Redis libraries)
- Strong typing with Python 3.11+
- Large talent pool, good documentation
- Easy integration with ML/AI features if needed later

**Cons:**
- GIL limits true parallelism (mitigated by async)
- Runtime type checking only (not compile-time)
- Less mature than Django

### Option 2: NestJS (Node.js/TypeScript)

**Pros:**
- Full TypeScript with compile-time type checking
- Decorator-based architecture similar to Spring
- Good async support with Node.js event loop
- OpenAPI integration via decorators
- Unified frontend/backend language (TypeScript)

**Cons:**
- Heavier framework with more boilerplate
- Less mature ORM options (TypeORM has issues)
- Higher memory usage
- More complex dependency injection

### Option 3: Django + Django REST Framework

**Pros:**
- Battle-tested, mature framework
- Excellent ORM and admin interface
- Large ecosystem and community
- Good security defaults

**Cons:**
- Not async-native (ASGI support added later)
- Heavier/slower than FastAPI for async workloads
- More opinionated, less flexible
- DRF serializers more verbose than Pydantic

## Decision

**We choose FastAPI** for the following reasons:

1. **Async-First Design**: FastAPI is built from the ground up for async operations, making it ideal for handling high-volume webhooks from 5 channel platforms concurrently.

2. **Automatic OpenAPI**: Type hints generate complete OpenAPI 3.1 documentation automatically, reducing documentation burden and ensuring spec accuracy.

3. **Pydantic Integration**: Pydantic v2 provides fast, robust data validation with excellent error messages, crucial for processing varied webhook payloads.

4. **Performance**: Benchmarks show FastAPI matching Node.js/Go for async workloads while maintaining Python's productivity.

5. **Celery Compatibility**: Excellent integration with Celery for background task processing (channel sync, reconciliation).

6. **SQLAlchemy 2.0**: Modern async ORM support with SQLAlchemy 2.0 and asyncpg for PostgreSQL.

7. **Team Fit**: Python's readability and FastAPI's simplicity enable faster onboarding.

## Consequences

### Positive

- High-performance async webhook handling
- Automatic, always-up-to-date API documentation
- Strong data validation with clear error messages
- Easy background task integration with Celery
- Good developer experience with IDE support

### Negative

- Runtime type checking only (mitigated by strict linting)
- Some async libraries less mature than sync equivalents
- Need to manage async context carefully (avoid blocking calls)

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Blocking calls in async code | Strict code review, run_in_executor for blocking ops |
| Memory usage with many connections | Connection pooling, proper async cleanup |
| Python ecosystem fragmentation | Pin dependency versions, regular updates |

## Implementation Notes

```python
# Recommended stack
FastAPI==0.110.x
Pydantic==2.x
SQLAlchemy==2.0.x
asyncpg==0.29.x
Celery==5.x
uvicorn==0.27.x

# Project structure
src/
  api/           # FastAPI routes
  core/          # PMS-Core business logic
  channel/       # Channel Manager adapters
  direct/        # Direct Booking Engine
  models/        # SQLAlchemy models
  schemas/       # Pydantic schemas
  tasks/         # Celery tasks
  utils/         # Shared utilities
```

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [FastAPI vs Flask vs Django Performance](https://www.techempower.com/benchmarks/)
- [Pydantic v2 Performance](https://docs.pydantic.dev/latest/concepts/performance/)
