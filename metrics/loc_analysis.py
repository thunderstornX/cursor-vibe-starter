#!/usr/bin/env python3
"""LOC analysis: what fraction of this repo's commits were AI-directed
vs. human-written, by net-added lines of code?

Usage:

    python -m metrics.loc_analysis              # whole repo
    python -m metrics.loc_analysis --since v1.0.0
    python -m metrics.loc_analysis --json       # machine-readable

Methodology in plain English:

  * We parse ``git log`` for every commit on the current branch.
  * Each commit's first line is expected to start with one of:
        [ai]      — AI-directed: prompt -> patch -> human review
        [manual]  — human-written: keystroke for keystroke
        [mixed]   — collaboration where neither dominates
        [merge]   — merge commit with no original work
        [tooling] — generated configs, lockfiles, CI yaml
  * For each commit we compute the *net* lines added (insertions
    minus deletions) over tracked source files, ignoring vendored
    paths and pure-data outputs.
  * We sum by tag and emit a table.

The protocol is documented in ``metrics/methodology.md``. The script
is intentionally simple so the methodology stays auditable: there is
no clever line-counting heuristic, no "AI lines we can detect"
feature. Either the commit author tells the script which bucket a
commit belongs in, or we don't count it.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess  # nosec B404 — argv is hardcoded literals
import sys
from dataclasses import dataclass, field
from pathlib import Path


_TAG_RE = re.compile(r"^\s*\[(ai|manual|mixed|merge|tooling)\]\s*", re.I)
_VALID_TAGS = ("ai", "manual", "mixed", "merge", "tooling", "untagged")

# Paths the LOC counter ignores. These are vendored, generated, or
# pure-data files where counting LOC tells you about the size of the
# upstream, not about effort.
_IGNORE_PATTERNS = (
    re.compile(r"^vendor/"),
    re.compile(r"^node_modules/"),
    re.compile(r"^paper/"),                 # latex+figures, not code
    re.compile(r"^results/"),               # measured-output blobs
    re.compile(r"\.lock$"),
    re.compile(r"\.png$|\.jpg$|\.svg$|\.pdf$"),
)


@dataclass
class Bucket:
    commits: int = 0
    insertions: int = 0
    deletions: int = 0
    files: set[str] = field(default_factory=set)

    @property
    def net(self) -> int:
        return self.insertions - self.deletions


def _parse_tag(subject: str) -> str:
    m = _TAG_RE.match(subject)
    return m.group(1).lower() if m else "untagged"


def _ignored(path: str) -> bool:
    return any(rx.search(path) for rx in _IGNORE_PATTERNS)


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args],
                                     text=True,
                                     stderr=subprocess.DEVNULL)  # nosec B603 B607


def collect(since: str | None = None) -> tuple[dict[str, Bucket], int]:
    """Return (buckets, total_commits)."""
    rev_range = since if since else "HEAD"
    raw = _git("log", "--reverse", "--no-merges",
               "--pretty=format:__COMMIT__%H%n%s",
               "--numstat", rev_range)
    buckets: dict[str, Bucket] = {t: Bucket() for t in _VALID_TAGS}
    cur_tag: str | None = None
    total = 0
    for line in raw.splitlines():
        if line.startswith("__COMMIT__"):
            subject_line = next_subject_for(raw, line)
            cur_tag = _parse_tag(subject_line)
            buckets[cur_tag].commits += 1
            total += 1
            continue
        if not line.strip() or cur_tag is None:
            continue
        # numstat row: "ins\tdel\tpath"
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        ins_s, del_s, path = parts
        if ins_s == "-" or del_s == "-":  # binary file
            continue
        if _ignored(path):
            continue
        try:
            ins, dels = int(ins_s), int(del_s)
        except ValueError:
            continue
        b = buckets[cur_tag]
        b.insertions += ins
        b.deletions += dels
        b.files.add(path)
    return buckets, total


def next_subject_for(raw: str, marker_line: str) -> str:
    """Given the ``__COMMIT__<sha>`` line, return the next non-blank
    line — the commit subject."""
    lines = raw.splitlines()
    try:
        idx = lines.index(marker_line)
    except ValueError:
        return ""
    for nxt in lines[idx + 1:]:
        if nxt.strip():
            return nxt
    return ""


def render_table(buckets: dict[str, Bucket], total: int) -> str:
    out = []
    out.append(f"{'tag':<10}  {'commits':>8}  {'insert':>8}  "
               f"{'delete':>8}  {'net LOC':>8}  {'files':>6}  {'% of net':>9}")
    out.append("-" * 70)
    real_net_total = sum(max(0, b.net) for tag, b in buckets.items()
                          if tag not in ("merge", "tooling"))
    real_net_total = max(real_net_total, 1)
    for tag in _VALID_TAGS:
        b = buckets[tag]
        share = (max(0, b.net) / real_net_total * 100) if tag not in ("merge", "tooling") else 0.0
        out.append(f"{tag:<10}  {b.commits:>8}  {b.insertions:>8}  "
                   f"{b.deletions:>8}  {b.net:>8}  {len(b.files):>6}  "
                   f"{share:>8.1f}%")
    out.append("")
    out.append(f"total commits: {total}")
    return "\n".join(out)


def render_markdown(buckets: dict[str, Bucket], total: int) -> str:
    """Markdown table, suitable for pasting into a results.md."""
    lines = ["| tag | commits | insertions | deletions | net LOC | files |",
             "|---|---:|---:|---:|---:|---:|"]
    for tag in _VALID_TAGS:
        b = buckets[tag]
        lines.append(
            f"| {tag} | {b.commits} | {b.insertions} | "
            f"{b.deletions} | {b.net} | {len(b.files)} |")
    lines.append("")
    lines.append(f"_Total commits: {total}_")
    return "\n".join(lines)


def to_json(buckets: dict[str, Bucket], total: int) -> str:
    obj = {"total_commits": total, "by_tag": {
        tag: {"commits": b.commits, "insertions": b.insertions,
              "deletions": b.deletions, "net": b.net,
              "files": len(b.files)}
        for tag, b in buckets.items()
    }}
    return json.dumps(obj, indent=2)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--since", help="git revision range (e.g. v1.0.0)")
    p.add_argument("--json", action="store_true",
                   help="emit JSON instead of a text table")
    p.add_argument("--markdown", action="store_true",
                   help="emit a markdown table (for results.md)")
    args = p.parse_args(argv)

    buckets, total = collect(since=args.since)
    if args.json:
        print(to_json(buckets, total))
    elif args.markdown:
        print(render_markdown(buckets, total))
    else:
        print(render_table(buckets, total))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
