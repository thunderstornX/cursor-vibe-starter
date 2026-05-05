# 10 — Refactor for maintainability

## Context

Use this when a module has grown to 600+ lines, the tests pass, and
you can't remember what half of it does. Goal: smaller modules,
narrower contracts, no behaviour change. **The output of this
prompt should not change the test suite.**

## Template

```
Refactor the module below. Constraints (in order of priority):

  1. NO behavioural change. Every existing test must still pass
     unmodified.
  2. Split the module along *responsibility* lines, not file size.
     Suggest the split ONCE at the top before producing files.
  3. Each new module exposes only the symbols its callers need;
     everything else is a leading-underscore private.
  4. Public functions get a docstring; private helpers don't unless
     genuinely subtle.
  5. Replace dict-of-dict-of-list shapes with dataclasses or pydantic
     models when the shape crosses a function boundary.
  6. Replace inline strings used as enum values with a real Enum.
  7. Don't introduce new dependencies. Don't switch frameworks.
  8. Keep the same import path for every public function — i.e.
     `from app.module import f` keeps working. Use a re-export if
     necessary.

For each file you change:
  - Note which functions / classes moved where
  - Note any signatures you changed (these need tests updated and
     should be flagged as a behavioural change — if so, STOP and
     describe it instead of silently changing them)

Module:

{paste the module to refactor}
```

## Example

A 700-line `routes/scan.py` that mixes auth checks, validation,
queue submission, and Redis state mutation in one handler.

## Expected Output

Suggested split:

```
routes/scan.py        -> just the FastAPI handler, calls into the
                         service layer
service/scan.py       -> create_scan(user, target, profile) -> Scan
                         (no FastAPI deps; pure logic)
queue/scan.py         -> enqueue + poll Redis, returns dataclass
validators/target.py  -> hostname validation
```

Each file under 150 lines, each function with one job.

## Common Pitfalls

- **Silent signature changes.** AI will rename a parameter from
  `target` to `host` "for clarity" — tests still pass on positional
  args, but every external caller breaks. Watch for these.
- **"Refactor" that adds features.** If the diff includes a new
  endpoint or a new logging call, it's not a refactor. Reject it.
- **`from .module import *` in `__init__.py` to keep imports
  working.** Surface area explodes. Re-export deliberately.
- **`utils.py`.** If a file is named `utils.py`, it's a sign nobody
  thought about where things should live. Re-prompt.
