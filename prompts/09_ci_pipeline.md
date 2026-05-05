# 09 — CI/CD pipeline (GitHub Actions)

## Context

Use this when a project is at the "I push code and it works on my
laptop" stage and needs a real CI: lint, test, security scans, build,
and a deploy step that requires manual approval. AI tools love to
bolt on twenty steps; we want six good ones.

## Template

```
Produce a GitHub Actions workflow for a Python project. Constraints:

  - Trigger on push to main and PR to main
  - Single workflow file, no fan-out over reusable workflows
  - Steps (in order):
      1. Checkout
      2. Set up Python {3.12}
      3. Cache pip
      4. Install requirements-dev.txt
      5. Lint: ruff check
      6. Test: pytest -q with --maxfail=3
      7. Security: bandit (medium+) + pip-audit + semgrep p/python
      8. Build Docker image (no push) — verifies the Dockerfile is sane
      9. Upload coverage as an artifact
  - Each security tool's output is uploaded as an artifact AND
    fails the build on findings (no soft-warn mode)
  - Concurrency: cancel in-progress runs on the same ref

Rules:
  - Pin every action to a SHA, not a tag (tags are mutable)
  - No `secrets.GITHUB_TOKEN` written into a step's env unless the
    step actually needs it
  - No `continue-on-error: true` anywhere — failures fail the build

Plus: produce a `.github/dependabot.yml` for pip + actions weekly
updates.
```

## Example

Drop in your repo path and Python version requirement.

## Expected Output

A single `.github/workflows/ci.yml` of ~60 lines, each step doing
one thing. Concurrency block at the top:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

Pinned action SHAs (you'll need to look these up in the repo's
release page) — or a comment noting where to pull them from.

## Common Pitfalls

- **`uses: actions/checkout@v4`.** Tag — not SHA. Mutable. AI loves
  tags; you have to do the SHA pinning by hand.
- **Running `pip install -r requirements.txt` AND
  `requirements-dev.txt`.** Duplicates the install step. Use one
  pinned dev file that includes the runtime one.
- **Running tests against the build image.** Sometimes wanted, but
  usually you just want pytest against the local source — keep them
  separate.
- **Caching the wrong path.** `~/.cache/pip` for pip; `~/.cache/uv`
  for uv. Mixing them silently does nothing.
- **`if: github.event_name == 'pull_request'` on a step that
  shouldn't run on main.** Inverted condition is the most common
  CI bug. Test it.
