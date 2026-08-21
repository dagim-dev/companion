# NOVA Future Scaling Notes

These are intentional deferrals for a clean V4 release, not missing release requirements.

## SQLite and persistence

SQLite is appropriate for the current low-traffic, single-worker deployment. Keep database access inside the persistence modules and avoid SQL in routers. Version schema changes explicitly so a later Postgres migration is tractable.

## User scope

`memory_scope` uses a `ContextVar` for user isolation. It is convenient today, but new core service boundaries should increasingly accept `user_id` explicitly. This will make workers, jobs, and multi-instance execution safer and easier to reason about.

## Session state and turn coordination

`NovaState` is intentionally in-memory and single-process. The V4 per-user turn guard prevents local races; it is not a multi-worker solution. Before adding Uvicorn workers or replicas, move session state and turn coordination to Redis or database-backed storage, or use deliberate sticky routing.

## Extraction jobs

The memory extraction queue is currently a database-backed, single-worker queue. Preserve the enqueue, claim, and process interfaces so implementation can later move to Redis, arq, Celery, or a dedicated worker service. Make job claiming atomic before running multiple workers.

## Semantic memory

Maintain a small retrieval interface: user, input/query, limit, and returned memory records. That seam allows SQLite embeddings to move later to Postgres with pgvector or a dedicated vector store without changing prompts or turn orchestration.

## Observability and load controls

Add phase timing, queue depth, SQLite lock metrics, per-user rate limits, and explicit executor sizing only when usage demonstrates the need. Those are useful scale controls, but they are not needed to ship a correct small deployment.
