---
name: orb-provider-review
description: Review ORB provider changes and PR scope before implementation or publication, keeping provider behavior isolated and shared fixes separate. Use for this ORB fork's provider development and PR preparation.
---

# Orb Provider Review

Read the target checkout's `docs/root/developer_guide/adding_a_provider.md` and
`docs/root/architecture/multi-provider-design.md`. Consult current PR review
feedback when continuing a reviewed PR; distinguish reviewer requests from the
user's authorization and do not send messages without authorization.

Before editing, identify the target branch, PR base, planned paths, and relevant
profile in [scope-policy.json](references/scope-policy.json). Explain material
scope choices and the validation needed. Run the checker with `--planned-path`
for proposed files, plus its existing-change inventory. Proceed with already
authorized in-scope work; this workflow adds no universal approval gate.

```sh
python /path/to/orb-provider-review/scripts/check_scope.py --repo /path/to/checkout --base-ref upstream/main --profile oci-234 --planned-path src/orb/providers/oci/scheduler/hostfactory_field_mapping.py
```

Use the skill from the fork tooling checkout or its installed copy when checking
another worktree; do not copy safeguard files into an upstream feature branch.
Profiles are deliberately distinct: `oci-234`, `oci-capacity`, `azure-588`,
`packaging-589`, and `fork-tooling`. The capacity profile admits only OCI provider
and OCI test paths; full HostFactory integration needs a separately scoped
generic PR. Never infer a profile or base from the active branch.

Keep provider calculations and launch behavior inside the provider package.
Shared code may dispatch through registries, but must not acquire provider-name
branches, provider imports, or provider-specific top-level domain/DTO fields.
If an existing hook cannot carry needed data, describe the smallest generic
extension separately instead of introducing a provider-specific workaround.

Before publishing, rerun the checker without planned paths against the actual
PR base and review the whole resulting diff, including shared metadata. The
checker unions committed, staged, unstaged, and nonignored untracked paths;
both sides of renames/copies count. It fails on conflicts, missing references,
and paths outside the selected profile. Copy detection includes unchanged source
files, so copying shared code into a provider does not hide its original path.
Untracked files have destination paths only; Git copy ancestry becomes available
after staging or committing. Review their content and rerun before publishing.
Index `assume-unchanged` or `skip-worktree` flags make the inventory incomplete:
the audit fails and reports flagged paths without changing flags or files. Review
and clear those flags explicitly before relying on the final audit; path
exceptions cannot bypass an incomplete inventory.
It is a scope check, not a secrets
scanner, test runner, permission grant, or content review. In particular,
`pyproject.toml`, `uv.lock`, shared documentation, labels, and issue templates
must contain only the profile's intended integration edits.

For out-of-scope work, report the affected paths and separate the change before
publication. Do not edit policy or use exceptions to approve your own expansion.
If the user has selected an exact-path exception, pass `--allow-path PATH`
(repeatable) with `--reason TEXT`; retain that declaration in the JSON evidence.
There is no broad shared-code bypass. Continue independent authorized work.

Run focused tests appropriate to the change and the repository's required
quality checks. State what was validated and material limits, including mocked
versus live cloud tests. Record the tested commit, whether the checkout was dirty,
commands, exit results, and artifact hashes for package checks. When testing dirty
sources, retain the patch and hashes of added inputs in ignored evidence; verify
that the committed source matches those inputs or repeat affected checks. Keep
deployment IDs, credentials, and private source in
ignored local evidence. Do not claim container or scheduler acceptance from
unit tests alone. Save the checker's JSON through the caller's normal evidence
workflow when useful; it prints evidence and never writes to the target repo.
