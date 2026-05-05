# 01 — API design from requirements

## Context

Use this prompt when you have a one-paragraph product requirement and
need a first-pass REST API surface — endpoints, request/response shapes,
error codes — *before* you start coding the controllers. This is the
prompt to run *first* on a new service so you don't end up retro-fitting
a coherent shape over four weeks of ad-hoc routes.

## Template

```
We need a REST API for the following product requirement:

  {one-paragraph requirement}

Constraints:
  - HTTP framework: {FastAPI | Flask | Express}
  - Auth model:     {JWT bearer | API key | OAuth client_credentials}
  - Persistence:    {Postgres | Redis | none}
  - Versioned:      {yes — under /v1 | no}

Design the API surface. For each endpoint, give me:
  1. Method + path
  2. One-line purpose
  3. Request schema (json fields, types, required/optional)
  4. Response schema for the success path
  5. Error codes the endpoint can return + when each is raised

Do NOT generate implementation code yet — only the API contract.
End with three open design questions you would ask the product owner
before implementing.
```

## Example

```
We need a REST API for the following product requirement:

  Internal team submits security scans against domains they own. A
  scan takes 30-120 seconds. Submitters need to retrieve their scan
  status and final report. Other teammates can view all reports.
  Targets must be within the corporate domain allow-list.

Constraints:
  - HTTP framework: FastAPI
  - Auth model:     JWT bearer
  - Persistence:    Postgres
  - Versioned:      yes — under /v1
```

## Expected Output

A clean table of endpoints, e.g.:

```
POST   /v1/scans              submit a new scan
       request:   {target: str (domain), profile: "quick"|"deep"}
       response:  {scan_id: uuid, status: "queued"}
       errors:    400 invalid target, 403 target not in allow-list,
                  429 rate-limited

GET    /v1/scans/{id}         poll for scan status + final report
       response:  {scan_id, status, target, started_at, finished_at,
                  findings: list, report_url}
       errors:    404 not found, 403 not your scan & not a teammate

GET    /v1/scans              list scans (own + teammate-visible)
       response:  paginated list
       errors:    401
```

Plus the three open questions ("Do report URLs expire?", etc.).

## Common Pitfalls

- **The model invents auth scopes you don't have.** It will happily
  add `scope:admin` and `scope:scanner` even though your JWT only
  carries `sub` and `exp`. Re-read every `requires_scopes` claim.
- **Polymorphic 200 responses.** AI sometimes returns `{...} | null`
  on the same endpoint. Force a stable shape — make `null` an
  explicit `404`.
- **No rate-limit codes.** AI tends to forget `429` even when the
  constraints mention rate limiting. Always check.
- **Missing idempotency.** For `POST /scans` you usually want an
  `Idempotency-Key` header story. Ask explicitly.
