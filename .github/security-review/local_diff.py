"""Read a complete PR diff from the exact checked-out Git revision."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


def read_diff(repository: Path, base: str, head: str) -> str:
    for revision in (base, head):
        if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
            raise ValueError("Review requires full base and head commit IDs")

    def git(*arguments: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(repository), *arguments], text=True, encoding="utf-8"
        )

    if git("rev-parse", "HEAD").strip() != head:
        raise ValueError("Checkout does not match the review head")

    if git("rev-parse", "--is-shallow-repository").strip() != "false":
        raise ValueError("Review requires complete Git history")

    git("diff", "--quiet", "HEAD", "--")
    merge_bases = git("merge-base", "--all", base, head).splitlines()
    if len(merge_bases) != 1:
        raise ValueError("Review requires one unambiguous merge base")

    return git(
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--no-color",
        "--find-renames",
        "--src-prefix=a/",
        "--dst-prefix=b/",
        merge_bases[0],
        head,
        "--",
    )
