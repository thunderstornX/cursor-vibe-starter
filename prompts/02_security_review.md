# 02 — Security review of a code diff

## Context

Use this prompt when you've staged a non-trivial diff (>50 lines or
crossing an auth/crypto/IO boundary) and want a sceptical second pair
of eyes before pushing. The output should read like a code review,
not a sales pitch — flag issues, don't summarise the change.

## Template

```
Review the following diff with a security mindset. Treat me as the
adversary, not the author.

Specifically look for:
  1. Injection (SQL, command, LDAP, log, header, template)
  2. Authentication / authorisation bypasses
  3. Hardcoded secrets, weak crypto choices, predictable tokens
  4. Input validation gaps at trust boundaries
  5. Information leakage in error responses or logs
  6. Race conditions on shared state (cache, DB, filesystem)
  7. Resource-exhaustion paths (unbounded loops, large allocations,
     unauthenticated expensive endpoints)
  8. Use of dangerous APIs (`eval`, `pickle.loads`, `subprocess shell=True`,
     `yaml.load`, etc.)

For each finding:
  - Severity: low | medium | high | critical
  - File:line
  - One-sentence explanation of *why* this is a problem in this code
  - Concrete fix (snippet, not prose)

If a section has no findings, say "no findings". Don't pad.

Diff:

{paste diff here}
```

## Example

Drop in a diff that adds a new `/scans` POST handler reading the
`target` field from the body and shelling out to `nmap`:

```
Diff:

+@router.post("/scans")
+async def create_scan(payload: dict):
+    target = payload["target"]
+    proc = subprocess.run(f"nmap -sV {target}", shell=True, ...)
+    return {"output": proc.stdout.decode()}
```

## Expected Output

```
1. CRITICAL — example/scans.py:3
   `subprocess.run(..., shell=True)` with f-string built from request
   body is command injection. A target like
   `example.com; rm -rf /tmp/state` is a working exploit.
   Fix: shell=False with an argv list, and validate `target` against
   a domain regex before passing it through:
       subprocess.run(["nmap", "-sV", target], shell=False, ...)

2. HIGH — example/scans.py:1
   The handler accepts `dict`, so anything goes through. Use a
   pydantic model with a constrained `target: HostnameStr` so the
   validation is at the boundary, not inside the handler.

3. MEDIUM — example/scans.py:5
   Returning raw `proc.stdout` to the caller leaks tool versions and
   stack traces if nmap fails. Parse it server-side, return only the
   structured findings.
```

## Common Pitfalls

- **The model says "looks good".** That's not a code review; that's
  a hallucinated stamp. Re-prompt asking for at least three concerns,
  even if low-severity.
- **It misses control-flow issues.** AI tools are good at pattern
  injection (SQLi, command injection) and weak at "this branch never
  runs" or "this lock is held across an await". Read those bits
  yourself.
- **Severity inflation.** AI labels things "CRITICAL" too liberally.
  Re-read every CRITICAL claim — if it requires the operator to
  already be root, it's not critical.
