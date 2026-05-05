# 07 — Structured error handling

## Context

Use this when a service has grown a thicket of `try/except: pass`,
inconsistent error shapes, and 500s leaking stack traces. The goal
is one error contract, applied uniformly, that gives clients enough
to act on without leaking server internals.

## Template

```
Refactor the error-handling pathway for this FastAPI service. Output:

  1. A small exception hierarchy in `errors.py`:
     - AppError(Exception): code: str, http_status: int, public: bool
     - ValidationError, NotFoundError, AuthError, RateLimitError,
       UpstreamError as subclasses
  2. A FastAPI exception handler (registered on the app) that turns
     any AppError into a stable JSON shape:
       {"error": {"code": "...", "message": "..."}}
  3. Replace ad-hoc HTTPExceptions / try/except blocks in the code
     paths I list below with the new exception types
  4. A logging filter that drops NotFoundError noise to DEBUG and
     escalates UpstreamError to ERROR

Rules:
  - The error code in the response is the SAME string as the
    exception class's `code` attribute — clients can match on it
  - Public-facing messages NEVER include the upstream's response
    body, file paths, or sql
  - The handler logs the *full* exception with traceback at ERROR
    level once; it does not log the response

Code paths to refactor:

{paste the offending file or function}
```

## Example

Imagine a `/v1/scans/{id}` handler that does
`raw = redis.get(key); return json.loads(raw)` — leaks
`json.JSONDecodeError` to the client when redis returns junk.

## Expected Output

The handler should:
- Catch the json error, raise `UpstreamError(code="redis.bad_payload")`
- Let the registered handler turn that into HTTP 502 with
  `{"error": {"code": "redis.bad_payload", "message": "scan store returned an invalid payload"}}`
- Log the full exception with traceback once, server-side

## Common Pitfalls

- **`raise HTTPException(500, str(e))` everywhere.** Returns whatever
  the upstream said — including stack traces, sql, paths. Always go
  through your own exception type.
- **Catching `Exception` then re-raising as `AppError(...)` without
  `from e`.** You lose the original traceback. Use `raise X from e`.
- **Public messages with f-strings into them.** AI loves
  `f"User {email} not found"`. That's user enumeration. Generic
  messages, structured codes.
- **Logging the request body.** Bodies often contain JWTs, tokens,
  or PII. Log structured fields you select; don't log the body.
- **Different shapes for validation vs auth errors.** Clients break
  silently. Pick one shape and never deviate.
