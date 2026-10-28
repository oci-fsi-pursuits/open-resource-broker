#!/usr/bin/env python3
"""Read-only ORB PR path audit; emits JSON, with exit codes 0/pass, 1/fail, 2/error."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

POLICY = Path(__file__).resolve().parents[1] / "references" / "scope-policy.json"
ORIGINS = ("committed", "staged", "unstaged", "untracked", "planned")


class ScopeError(Exception):
    """Invalid configuration or an incomplete Git inventory."""


def git(repo: Path, *args: str) -> bytes:
    """Run Git without a shell, external diff drivers, or optional index writes."""
    executable = shutil.which("git")
    if executable is None:
        raise ScopeError("Git is not available on PATH")
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"}
    }
    environment.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    try:
        # Fixed read-only subcommands and argument lists; refs are not shell code.
        result = subprocess.run(  # noqa: S603
            [
                executable,
                "--no-replace-objects",
                "-c",
                "core.fsmonitor=false",
                "-C",
                str(repo),
                *args,
            ],
            capture_output=True,
            check=False,
            timeout=30,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ScopeError("Git could not complete the read-only inventory") from exc
    if result.returncode:
        # Do not echo Git errors, which can include credential-bearing remotes.
        raise ScopeError(f"Git failed while reading {args[0]}; verify repository and references")
    return result.stdout


def relative_path(value: str, *, prefix: bool = False) -> str:
    """Require exact slash-separated repository paths, never patterns or traversal."""
    candidate = value[:-1] if prefix and value.endswith("/") else value
    if (
        not candidate
        or candidate.startswith("/")
        or "\\" in candidate
        or ":" in candidate
        or "\0" in candidate
        or any(part in {"", ".", ".."} for part in candidate.split("/"))
        or (prefix and not value.endswith("/"))
    ):
        raise ScopeError("Use exact repository-relative paths with forward slashes")
    return value


def parse_changes(data: bytes) -> list[dict[str, Any]]:
    """Parse Git --name-status -z, retaining both rename/copy endpoints."""
    if not data:
        return []
    if not data.endswith(b"\0"):
        raise ScopeError("Incomplete NUL-delimited Git output")
    tokens = data[:-1].split(b"\0")
    changes = []
    i = 0
    while i < len(tokens):
        status = tokens[i].decode("ascii", errors="strict")
        kind = status[:1]
        count = 2 if kind in {"R", "C"} else 1
        if kind not in {"A", "C", "D", "M", "R", "T", "U", "X", "B"}:
            raise ScopeError("Unsupported Git change status")
        if (kind in {"R", "C"} and not status[1:].isdigit()) or (
            kind not in {"R", "C"} and status != kind
        ):
            raise ScopeError("Malformed Git change status")
        if i + count >= len(tokens):
            raise ScopeError("Incomplete Git change record")
        paths = [
            relative_path(p.decode("utf-8", "surrogateescape"))
            for p in tokens[i + 1 : i + count + 1]
        ]
        changes.append({"status": status, "paths": paths})
        i += count + 1
    return changes


def parse_index_flags(data: bytes) -> list[dict[str, Any]]:
    """Find index flags that prevent a complete working-tree audit; never clear them."""
    if data and not data.endswith(b"\0"):
        raise ScopeError("Incomplete NUL-delimited index inventory")
    flagged = []
    for record in data.split(b"\0"):
        if not record:
            continue
        if len(record) < 3 or record[1:2] != b" ":
            raise ScopeError("Malformed Git index inventory")
        tag = record[:1].decode("ascii", errors="strict")
        if not tag.isalpha():
            raise ScopeError("Unsupported Git index tag")
        assume_unchanged = tag.islower()
        skip_worktree = tag.upper() == "S"
        if assume_unchanged or skip_worktree:
            flagged.append(
                {
                    "path": relative_path(record[2:].decode("utf-8", "surrogateescape")),
                    "tag": tag,
                    "assume_unchanged": assume_unchanged,
                    "skip_worktree": skip_worktree,
                }
            )
    return sorted(flagged, key=lambda item: (item["path"], item["tag"]))


def load_profile(name: str) -> tuple[dict[str, Any], str]:
    try:
        raw = POLICY.read_bytes()
        document = json.loads(raw)
        profile = document["profiles"][name]
        if document["version"] != 1:
            raise ScopeError("Unsupported scope policy version")
        for path in profile["paths"]:
            relative_path(path)
        for prefix in profile["prefixes"]:
            relative_path(prefix, prefix=True)
        if not isinstance(profile["content_review"], str):
            raise ScopeError("Invalid scope policy review note")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ScopeError("Unknown profile or invalid bundled scope policy") from exc
    return profile, hashlib.sha256(raw).hexdigest()


def audit(args: argparse.Namespace) -> dict[str, Any]:
    profile, digest = load_profile(args.profile)
    exceptions = sorted({relative_path(path) for path in args.allow_path})
    if bool(exceptions) != bool(args.reason and args.reason.strip()):
        raise ScopeError(
            "Exact --allow-path exceptions and a nonempty --reason are required together"
        )
    if args.base_ref.startswith("-") or not args.base_ref.strip():
        raise ScopeError("A non-option Git base reference is required")
    repo = Path(os.fsdecode(git(Path(args.repo), "rev-parse", "--show-toplevel").rstrip(b"\r\n")))
    base = (
        git(repo, "rev-parse", "--verify", "--end-of-options", f"{args.base_ref}^{{commit}}")
        .decode()
        .strip()
    )
    head = git(repo, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    ancestors = git(repo, "merge-base", "--all", base, head).decode().splitlines()
    if len(ancestors) != 1:
        raise ScopeError("Exactly one merge base is required; inspect divergent history")
    merge_base = ancestors[0]
    common = (
        "--name-status",
        "-z",
        "--find-renames",
        "--find-copies",
        "--find-copies-harder",
        "--no-ext-diff",
        "--no-textconv",
        "--ignore-submodules=none",
    )
    index_flags = parse_index_flags(git(repo, "ls-files", "-v", "-z"))
    inventory = {
        "committed": parse_changes(git(repo, "diff", *common, merge_base, head, "--")),
        "staged": parse_changes(git(repo, "diff", "--cached", *common, "HEAD", "--")),
        "unstaged": parse_changes(git(repo, "diff", *common, "--")),
        "untracked": [],
        "planned": [{"status": "planned", "paths": [relative_path(p)]} for p in args.planned_path],
    }
    for path in git(repo, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0"):
        if path:
            inventory["untracked"].append(
                {"status": "?", "paths": [relative_path(path.decode("utf-8", "surrogateescape"))]}
            )
    by_path: dict[str, set[str]] = {}
    conflicts = set()
    for origin, changes in inventory.items():
        for change in changes:
            for path in change["paths"]:
                by_path.setdefault(path, set()).add(origin)
                if change["status"][:1] in {"U", "X", "B"}:
                    conflicts.add(path)
    paths = []
    for path in sorted(by_path):
        permitted = path in profile["paths"] or any(path.startswith(p) for p in profile["prefixes"])
        paths.append(
            {
                "path": path,
                "origins": [o for o in ORIGINS if o in by_path[path]],
                "scope": "allowed"
                if permitted
                else "exception"
                if path in exceptions
                else "outside",
            }
        )
    violations = [item["path"] for item in paths if item["scope"] == "outside"]
    return {
        "result": "fail" if violations or conflicts or index_flags else "pass",
        "repository": str(repo),
        "profile": args.profile,
        "policy_sha256": digest,
        "base_ref": args.base_ref,
        "base_commit": base,
        "head_commit": head,
        "head_ref": git(repo, "rev-parse", "--abbrev-ref", "HEAD").decode().strip(),
        "merge_base": merge_base,
        "dirty": None
        if index_flags
        else any(inventory[o] for o in ("staged", "unstaged", "untracked")),
        "inventory_complete": not index_flags,
        "index_flags": index_flags,
        "incomplete_reasons": [
            "Index flags may hide working-tree edits; review and clear them explicitly"
        ]
        if index_flags
        else [],
        "inventory": inventory,
        "paths": paths,
        "violations": violations,
        "conflicts": sorted(conflicts),
        "declared_exceptions": {"paths": exceptions, "reason": args.reason or None},
        "content_review_required": profile["content_review"],
        "limits": "Path scope only; does not verify content, secrets, tests, or human authorization.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", required=True, help="Target Git checkout; never inferred from the skill location"
    )
    parser.add_argument(
        "--base-ref", required=True, help="Explicit PR base reference, resolved without fetching"
    )
    parser.add_argument("--profile", required=True, help="Explicit profile in the bundled policy")
    parser.add_argument(
        "--planned-path",
        action="append",
        default=[],
        help="Additional exact path to review before editing",
    )
    parser.add_argument(
        "--allow-path",
        action="append",
        default=[],
        help="Exact exception path already selected by the user",
    )
    parser.add_argument(
        "--reason", help="Record the user's scope exception reason; does not grant authorization"
    )
    args = parser.parse_args(argv)
    try:
        report = audit(args)
    except (ScopeError, UnicodeError) as exc:
        print(json.dumps({"result": "error", "error": str(exc)}, ensure_ascii=True, sort_keys=True))
        return 2
    print(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
