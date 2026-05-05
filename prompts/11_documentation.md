# 11 — API + module documentation

## Context

Use this when you need a README + a module-reference doc for an
already-built service. AI is genuinely useful here — it's good at
spotting public surface and producing consistent docstrings. The
trick is keeping it from inventing parameters and behaviours.

## Template

```
Produce documentation for the codebase below. Output:

  1. README.md with:
     - One-paragraph description (what + why, no marketing)
     - Quickstart (clone, install, run, smoke test) as bash blocks
     - Configuration table: env var | type | default | description
     - "What's in the box" — directory tree with one-liner per dir
     - Tests section (how to run, what's covered)
  2. docs/api.md (if the service is HTTP) with:
     - One section per endpoint
     - Request / response examples in JSON, NOT prose
     - All error codes the endpoint can return
  3. docs/architecture.md with:
     - A 5-line "request lifecycle" walkthrough
     - A bulleted list of the *invariants* the system depends on
     - A "what could go wrong" section listing the failure modes
       you actually see in production

Rules:
  - Don't invent endpoints, parameters, or env vars. If you can't
    find a setting in the code, say "not documented in source —
    please confirm".
  - Don't write feature lists. Lead with quickstart.
  - No emojis. No "🚀 Welcome to..." opening lines. Plain technical
    prose.
  - One example per concept, not three.

Codebase:

{paste the service tree + relevant source}
```

## Example

A FastAPI service with `/v1/auth/login`, `/v1/scans`,
`/v1/scans/{id}`, two middleware, Redis sidecar.

## Expected Output

Quickstart that works on a clean machine:

```bash
git clone .../service.git
cd service
cp .env.example .env
docker compose up -d
curl -fsS http://localhost:8080/health
```

Configuration table that exactly matches the actual env vars used by
`config.py` — same names, same defaults.

## Common Pitfalls

- **Invented env vars.** AI sometimes lists `DATABASE_URL` when the
  service actually uses `POSTGRES_DSN`. Cross-check every row of the
  configuration table against the source.
- **Outdated examples.** A response shape from a previous version
  ends up in the docs and stays there for a year. Have the prompt
  generate from the current models.py.
- **Architecture diagrams.** Mermaid is fine; ASCII is fine; AI
  invents component names that don't exist. Read every box.
- **Promises.** "This service handles 10k req/sec" — only say that
  if you've measured it. Otherwise drop the claim.
