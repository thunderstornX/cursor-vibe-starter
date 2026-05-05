# 12 — Incident response tooling

## Context

Use this when an incident has just started or just ended, and you need
either (a) a runbook stub the on-call can follow, or (b) a small CLI
that automates the read-only part of the response (collect logs,
extract IPs, snapshot state). This prompt is the *fastest* way to
turn the post-mortem ideas into reusable scaffolding.

## Template

```
Produce two artefacts for this incident class:

  1. runbooks/{slug}.md — a runbook the on-call follows. Sections:
     - **Trigger**: how does the on-call know this is the right runbook?
     - **Severity bands**: how to decide P0/P1/P2 in <30 seconds
     - **Diagnose** (numbered steps; each step has one command and
       one expected output)
     - **Mitigate** (numbered, with rollback)
     - **Communicate** (where to post, what to say)
     - **Post-incident**: what artefacts to capture before paging out
  2. scripts/{slug}.py — a Python click/typer CLI for the *read-only*
     parts of diagnose (the steps that don't change state). Each step
     is a separate subcommand. Output is structured: JSON to stdout,
     human-readable progress to stderr.

Rules:
  - The CLI must NEVER mutate state. It is purely diagnostic. If a
    step needs to mutate, leave it as a runbook step with the exact
    command, not as code.
  - Every command in the runbook is copy-pasteable verbatim. No
    `<your-deployment>` placeholders unless they're env-driven.
  - Severity bands MUST include user-facing impact, not internal
    metrics. "Login is broken for >1% of users" beats "p99 > 2s".
  - The runbook fits on one screen. If it doesn't, you're being
    asked to handle two incident classes — split it.

Incident class:

{describe the incident class — e.g. "redis is unreachable",
"scan queue backlog > 1000"}
```

## Example

Incident class: "FastAPI service returning 503s; we suspect Redis is
unreachable from the app pod."

## Expected Output

A runbook of ~40 lines starting with:

```
# Trigger
You are paged on `service: 503 rate > 5%`. The 503s carry
`{"error":{"code":"upstream.redis"}}`.
```

Diagnose steps using only `curl`, `redis-cli ping`, `kubectl logs`,
and `kubectl get` — no `kubectl exec sh`, no `kubectl edit`.

A `scripts/redis_check.py` with subcommands `ping`, `info`, `slowlog`,
`memory` — each printing JSON to stdout for the on-call to attach to
the incident channel.

## Common Pitfalls

- **Runbook that automates the mitigation.** Tempting; almost always
  wrong. The on-call needs to *understand* the mitigation. Keep
  mitigation in markdown.
- **Invented kubectl/aws CLI flags.** AI hallucinates flags
  confidently. Run every command before shipping the runbook.
- **Severity bands tied to internal metrics.** "p99 > 2s" doesn't
  page anyone. Tie to user-visible impact.
- **A 200-line runbook.** Each runbook handles one incident class.
  If your prompt covers three failure modes, write three runbooks.
- **Mixing diagnose and mitigate.** Mitigation steps should never
  appear above the "rollback" line of an earlier step. Separation
  saves blast radius.
