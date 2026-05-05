# 08 — Structured JSON logging

## Context

Use this when a service's output is `print()` calls and one-off
`logger.info("user %s did thing", x)` lines — the kind of logging
that's fine in dev and unparseable in prod. Goal: every log line is
JSON, one line per event, with a stable schema your log aggregator
can index.

## Template

```
Set up structured JSON logging for this FastAPI service. Output:

  1. `logging_config.py` that:
     - configures stdlib logging (no print)
     - emits JSON via python-json-logger
     - injects request_id (from a contextvar) into every log line
     - injects fields: ts, level, msg, logger, request_id, user_id
       (when available), latency_ms (on access logs)
     - redacts secrets (Authorization header, JWT, X-API-Key) at the
       formatter level
  2. A request middleware that:
     - generates a request_id (uuid4 by default; honours an incoming
       X-Request-ID if present)
     - sets it on the contextvar
     - logs ONE access log per request at INFO with: method, path,
       status, latency_ms
  3. A pytest test asserting that:
     - secrets in headers do NOT appear in any captured log
     - request_id is propagated end-to-end
     - exception logs include traceback

Rules:
  - One event per line. Multi-line tracebacks become an array field.
  - Never log the request body. Body redaction is a rabbit hole;
    avoid the rabbit.
  - Logger name is the module name; do not use root.
  - Production: JSON to stdout. Development: pretty-printed if a
    tty is attached.
```

## Example

Drop in your existing `main.py` to refactor.

## Expected Output

A formatter that turns a `logger.info("auth ok", extra={"user_id": uid})`
into:

```json
{"ts":"2026-05-03T10:14:32Z","level":"INFO","msg":"auth ok","logger":"app.auth","request_id":"6b...","user_id":"42"}
```

A redactor that recognises `Authorization`, `X-API-Key`, and any
`*token*` field by name and replaces values with `***`.

## Common Pitfalls

- **String-formatting log messages with secrets.**
  `logger.info(f"token={token}")` survives every redactor. Use
  structured fields.
- **`logging.basicConfig` plus `logger.addHandler` both.** Double
  output. Pick one, document it.
- **`print()` for "just this one debug line".** It bypasses every
  formatter. Use `logger.debug`.
- **Tracebacks on a single line.** Loses indentation, kills
  greppability. Let the JSON formatter put it in a `traceback` array.
- **`request_id` reset on async hops.** A naive `threading.local`
  doesn't work in FastAPI. Use `contextvars.ContextVar`.
