#!/usr/bin/env python3
"""Validate roadmap references, source coverage, dependencies, and optional Git bases."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

BASELINE_BRANCH = "pr/oci-provider-scoped"
STATUSES = {
    "implemented_pending_merge",
    "implemented_pending_integration",
    "design_required",
    "planned",
    "validation_pending",
    "preserve_existing",
    "in_progress",
    "blocked",
    "complete",
    "deferred",
}
SCOPES = {"baseline", "provider", "shared", "deployment", "validation", "documentation"}
EXPECTED_COVERAGE = {
    "capability": {f"C{i:02}" for i in range(1, 13)},
    "priority": {f"P{i:02}" for i in range(1, 9)},
    "compatibility": {f"K{i:02}" for i in range(1, 6)},
    "safety": {f"S{i:02}" for i in range(1, 4)},
}


def validate(document: dict[str, Any]) -> list[str]:
    """Return structural/content-link errors; never change the roadmap."""
    errors: list[str] = []
    if document.get("version") != 1:
        errors.append("Unsupported roadmap version")
    branches = document.get("branches", {})
    items = document.get("items", [])
    coverage = document.get("coverage", [])
    external = document.get("external_dependencies", [])
    if not isinstance(branches, dict) or not all(isinstance(v, dict) for v in branches.values()):
        return [*errors, "branches must map names to branch records"]
    if not all(isinstance(v, list) for v in (items, coverage, external)):
        return [*errors, "items, coverage, and external_dependencies must be lists"]
    if not all(isinstance(v, dict) for v in [*items, *coverage, *external]):
        return [*errors, "Roadmap records must be objects"]
    item_ids = [i.get("id") for i in items]
    external_ids = [i.get("id") for i in external]
    coverage_ids = [i.get("id") for i in coverage]
    for label, ids in [("item", item_ids), ("external", external_ids), ("coverage", coverage_ids)]:
        if any(not isinstance(value, str) or not value for value in ids):
            return [*errors, f"{label} IDs must be nonempty strings"]
        if len(ids) != len(set(ids)):
            errors.append(f"Duplicate {label} IDs")
    if set(item_ids) & set(external_ids):
        errors.append("Item and external dependency IDs overlap")
    by_id = {i["id"]: i for i in items}
    by_coverage = {i["id"]: i for i in coverage}
    known = set(item_ids) | set(external_ids)
    for branch, record in branches.items():
        if not re.fullmatch(r"codex/[a-z0-9][a-z0-9/-]*", branch):
            errors.append(f"Invalid feature branch name: {branch}")
        if record.get("scope") not in SCOPES:
            errors.append(f"Invalid branch scope: {branch}")
        if not isinstance(record.get("existing"), bool):
            errors.append(f"Branch existing flag missing: {branch}")
        if record.get("state") not in {"starter", "implemented", "in_progress", "complete"}:
            errors.append(f"Invalid branch state: {branch}")
        base = record.get("base_ref")
        if not isinstance(base, str) or not base or base.startswith("-"):
            errors.append(f"Explicit base reference missing: {branch}")
        if record.get("scope") == "shared" and base != "upstream/main":
            errors.append(f"Shared branch must start from main: {branch}")
    for item in items:
        identity = item["id"]
        for key in ["title", "estimate", "owner_role", "owner"]:
            if not isinstance(item.get(key), str) or not item[key].strip():
                errors.append(f"{identity}: missing {key}")
        if item.get("phase") not in range(6) or item.get("priority") not in {
            "P0",
            "P1",
            "P2",
            "P3",
        }:
            errors.append(f"{identity}: invalid phase or priority")
        if item.get("status") not in STATUSES or item.get("scope") not in SCOPES:
            errors.append(f"{identity}: invalid status or scope")
        if item.get("branch") not in {*branches, BASELINE_BRANCH}:
            errors.append(f"{identity}: branch is not registered")
        for key in ["depends_on", "design_gates", "acceptance", "source_refs"]:
            value = item.get(key)
            if not isinstance(value, list) or any(not isinstance(s, str) or not s for s in value):
                errors.append(f"{identity}: {key} must be a string list")
                continue
            if key in {"acceptance", "source_refs"} and not value:
                errors.append(f"{identity}: {key} cannot be empty")
        for dependency in item.get("depends_on", []):
            if dependency not in known:
                errors.append(f"{identity}: unknown dependency {dependency}")
        for source in item.get("source_refs", []):
            if source not in by_coverage or identity not in by_coverage[source].get("item_ids", []):
                errors.append(f"{identity}: source link is missing or not reciprocal: {source}")
        if (
            item.get("status", "").startswith("implemented_") or item.get("status") == "complete"
        ) and not item.get("evidence"):
            errors.append(f"{identity}: implemented status requires evidence")
        if item.get("status") == "design_required" and not item.get("design_gates"):
            errors.append(f"{identity}: design-required work needs a named decision")
    for source in coverage:
        if (
            not source.get("title")
            or not isinstance(source.get("item_ids"), list)
            or not source["item_ids"]
        ):
            errors.append(f"{source['id']}: missing title or work mapping")
            continue
        for identity in source["item_ids"]:
            if identity not in by_id or source["id"] not in by_id[identity].get("source_refs", []):
                errors.append(f"{source['id']}: item link is missing or not reciprocal: {identity}")
    for category, expected in EXPECTED_COVERAGE.items():
        actual = {i["id"] for i in coverage if i.get("category") == category}
        if actual != expected:
            errors.append(
                f"{category}: missing {sorted(expected - actual)}, unexpected {sorted(actual - expected)}"
            )
    if not any(i.get("category") == "evidence" for i in coverage):
        errors.append("Operational evidence coverage is missing")

    def check_cycles(graph: dict[str, list[str]], label: str) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(identity: str) -> None:
            if identity in visiting:
                errors.append(f"{label} dependency cycle at {identity}")
                return
            if identity in visited:
                return
            visiting.add(identity)
            for dependency in graph.get(identity, []):
                if dependency in graph:
                    visit(dependency)
            visiting.remove(identity)
            visited.add(identity)

        for identity in graph:
            visit(identity)

    check_cycles({i["id"]: i.get("depends_on", []) for i in items}, "Work item")
    check_cycles({name: [r.get("base_ref", "")] for name, r in branches.items()}, "Branch")
    return errors


def check_refs(document: dict[str, Any], repo: Path) -> tuple[list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    records = []
    executable = shutil.which("git")
    if executable is None:
        return ["Git is unavailable"], records
    environment = {
        k: v
        for k, v in os.environ.items()
        if k.upper() not in {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"}
    }
    environment.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")

    def git(*arguments: str) -> str:
        result = subprocess.run(  # noqa: S603
            [
                executable,
                "--no-replace-objects",
                "-c",
                "core.fsmonitor=false",
                "-C",
                str(repo),
                *arguments,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
            env=environment,
        )
        return result.stdout.strip()

    for branch, record in document["branches"].items():
        try:
            head = git("rev-parse", "--verify", "--end-of-options", f"{branch}^{{commit}}")
            base = git(
                "rev-parse", "--verify", "--end-of-options", f"{record['base_ref']}^{{commit}}"
            )
            ancestor = git("merge-base", head, base)
            if ancestor != base:
                errors.append(
                    f"{branch}: base is not an ancestor; inspect/rebase before implementation"
                )
            if record["state"] == "starter" and head != base:
                errors.append(f"{branch}: starter state is stale; it has feature commits")
            records.append({"branch": branch, "head": head, "base": base, "state": record["state"]})
        except (OSError, subprocess.SubprocessError):
            errors.append(f"{branch}: Git reference check failed")
    return errors, records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=Path(__file__).with_name("backlog.json"))
    parser.add_argument("--check-refs", action="store_true")
    parser.add_argument("--repo", type=Path)
    args = parser.parse_args()
    if args.check_refs and args.repo is None:
        parser.error("--check-refs requires an explicit --repo")
    try:
        document = json.loads(args.file.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError("The roadmap must be a JSON object")
        errors = validate(document)
        refs = []
        if args.check_refs and not errors:
            ref_errors, refs = check_refs(document, args.repo)
            errors.extend(ref_errors)
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"result": "error", "error": str(error)}))
        return 2
    print(
        json.dumps(
            {
                "result": "fail" if errors else "pass",
                "errors": errors,
                "items": len(document.get("items", [])),
                "branches": len(document.get("branches", {})),
                "coverage_rows": len(document.get("coverage", [])),
                "verified_refs": refs,
            },
            indent=2,
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
