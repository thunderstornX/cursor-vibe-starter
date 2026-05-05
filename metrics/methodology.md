# Measurement methodology

`loc_analysis.py` reports the share of this repo's lines-of-code that
came from AI-directed work versus hand-written work. This file
documents the protocol so the numbers in `results.md` are
reproducible and auditable.

## What we count

Net lines of code per commit (`insertions - deletions`) over tracked
source files only. We **exclude**:

- Vendored or third-party trees (`vendor/`, `node_modules/`).
- Generated artefacts (lockfiles, paper PDFs/figures, eval results).
- Binary blobs (numstat reports `-` rather than a count).

The exclusion list lives at the top of `loc_analysis.py` and is
intentionally short. The point of the script is *not* to maximise
the LOC number; it is to make a defensible breakdown.

## How a commit gets bucketed

The first line of every commit message in this repository starts
with one of five tags:

| Tag         | Meaning                                                                |
|-------------|------------------------------------------------------------------------|
| `[ai]`      | AI-directed: prompt → patch → human review. The wording, structure, and order of the patch are the AI's; the human read it line-by-line and changed at most a few lines. |
| `[manual]`  | Hand-written: human typed every character. Reviewer may have suggested AI use; author chose not to.                                                                       |
| `[mixed]`   | Collaboration. AI wrote a draft, human substantially rewrote it (>30% of resulting lines). Or: AI wrote a function, human wrote the test and an adjacent helper.          |
| `[tooling]` | Generated config: `requirements.txt`, lockfiles, CI yaml, formatter output. We bucket these separately because LOC ratios from generated text say nothing about effort.   |
| `[merge]`   | Merge commit with no original content. Excluded from totals.                                                                                                                 |

A commit message that doesn't start with one of these tags is
bucketed as `untagged`. The `untagged` row exists so any drift in the
discipline shows up in the report rather than silently inflating one
of the other buckets.

## Why this protocol, and not LOC heuristics?

It is tempting to write a clever script that infers "AI lines" from
style fingerprints — overly verbose docstrings, excessive type hints,
specific naming patterns. We considered it; we rejected it.

1. **It's circular.** The most reliable way to detect AI-style code
   is to look for the patterns the *current generation* of models
   produces, which means the metric breaks the moment a different
   model with a different style is used.
2. **It rewards lying.** If "the script counts as AI based on
   docstring length", the obvious bypass is "rewrite the docstring".
   That's busywork that doesn't change the underlying question
   ("how much of this codebase is human-written?").
3. **It hides the boring answer.** A lot of real code is short
   functions and one-line wires. Heuristics over-attribute these
   either way; the honest answer is "the author can tell you".

The author-tagged protocol is the same trade-off used in academic
authorship lists: the contributors say what they contributed, and the
report aggregates. If the author tags wrong, the report is wrong;
that's a feature, not a bug, because it forces honesty.

## Limitations

- **A `[manual]` commit can still have used AI for autocomplete.**
  Modern editors complete tokens and short lines; the threshold for
  `[ai]` here is "the patch was written by the model, not the
  cursor". This is judgment, not measurement.
- **Reviewer effort is invisible.** A 50-line `[ai]` patch that took
  two hours of human review counts the same as a 50-line `[ai]`
  patch the human waved through. The metric measures *output*, not
  *effort*.
- **Refactors that net to zero LOC don't show up.** A `[manual]`
  refactor that deletes 200 lines and adds 200 lines reports `0` net.
  Refactor commits should be tagged `[manual]` and inspected
  separately if effort is the question.

## Reproducing the report

```bash
python -m metrics.loc_analysis              # text table
python -m metrics.loc_analysis --markdown   # what's pasted into results.md
python -m metrics.loc_analysis --json       # machine-readable
```

Run after a release tag if you want to compare across versions:
`python -m metrics.loc_analysis --since v1.0.0`.
