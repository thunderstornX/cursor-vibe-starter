# 05 — Database schema design + migration

## Context

Use this when you need to translate a list of entities + relationships
into a real schema (Postgres) with a SQLAlchemy 2.x typed-ORM model
file and an Alembic migration. AI is great at the boilerplate;
*you* have to keep it from inventing fields.

## Template

```
Design a Postgres schema and a SQLAlchemy 2.x typed-ORM model for the
following entities. Output:

  1. ER summary (one short paragraph)
  2. SQL DDL for the tables (CREATE TABLE ...; CREATE INDEX ...;)
  3. SQLAlchemy 2.x typed models in models.py
  4. Alembic migration that applies (1)

Entities:
  {- entity name: fields and relationships}

Constraints:
  - All primary keys are uuid (server-default)
  - All timestamps are timestamptz
  - Soft delete via `deleted_at` only on the entities you list
  - Foreign keys ON DELETE: {RESTRICT | CASCADE | SET NULL — pick
    deliberately}
  - Index every foreign key
  - Index every column the application filters on heavily
  - No `JSON` columns unless the field is genuinely free-form
```

## Example

```
Entities:
  - users:    id, email (unique), password_hash, created_at
  - api_keys: id, user_id (FK), label, hash, created_at, revoked_at
  - scans:    id, user_id (FK), target, status, created_at,
              finished_at, profile (enum: quick|deep)
  - findings: id, scan_id (FK), severity (enum), title, evidence
              (jsonb)
```

## Expected Output

A models.py with:
- `Base = DeclarativeBase` once
- `users.email` `Mapped[str] = mapped_column(unique=True, nullable=False)`
- `scans.user_id = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)`
- `scans.profile = mapped_column(SQLEnum(ScanProfile, name="scan_profile"), nullable=False)`
- A clear `__repr__` on each model

A migration with `op.create_table` + `op.create_index` calls in the
right order (parents before children).

## Common Pitfalls

- **Auto-loaded relationships.** AI defaults to `lazy='select'` which
  is N+1 by default. Pick `selectin` or `joined` deliberately.
- **`JSON` columns for things that are list-of-strings.** Use a
  proper child table; you'll thank yourself the first time you need
  to query "all scans with finding X".
- **String-typed enums.** AI sometimes uses plain `String(20)` for
  `status`. Use a real Postgres enum or a `CHECK` constraint.
- **Forgetting indexes on FKs.** Postgres doesn't add them
  automatically. Every `ForeignKey` should have a matching `Index`.
- **`ON DELETE CASCADE` on user → scans.** Sometimes correct,
  sometimes catastrophic. Make the choice explicit, not implicit.
