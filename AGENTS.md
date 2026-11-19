# ORB fork: Codex iteration handoff

This is fork coordination, not an upstream feature change. Keep this file and
`roadmap/oci/` out of provider feature PRs.

## Start an OCI work iteration

1. Read the canonical `roadmap/oci/CURRENT.md`, `backlog.json`, and `iterations.json`
   on `codex/oci-feature-roadmap`. Find its checkout with `git worktree list`;
   this workspace normally uses `work/oci-feature-roadmap/roadmap`. If it is not
   checked out, use `git show codex/oci-feature-roadmap:roadmap/oci/CURRENT.md` and
   the equivalent commands for the JSON files.
2. Pick one work card or incident and state the result that will finish this
   iteration. Read its blocker and latest evidence before repeating experiments.
3. Confirm the actual implementation worktree, branch, head, base and dirty state.
   The main workspace may contain an older coordination checkout. Do not assume
   that its source is the current implementation or current upstream main.
4. Apply the `orb-provider-review` skill for provider development or PR work.
   Provider behavior belongs inside its provider. Shared contracts and generic
   fixes need their own scoped changes. Existing task authorization still applies;
   these instructions add no universal permission gate.

## Scope of new OCI fixes

- Use the provider-review checker's `oci-provider` profile against the actual PR
  base before editing and again before publication. Allowed paths are only
  `src/orb/providers/oci/`, `tests/providers/oci/`, and
  `docs/root/providers/oci/`. The broad `oci-234` profile is historical only.
- Shared CLI, DTO/domain, scheduler/HostFactory, other-provider, packaging,
  dependency and workflow changes are outside the OCI fix queue. They require
  separately scoped work and distinct user direction; do not bundle them here.
- The user's 17 November landing-page exception is a one-time documentation
  change on `codex/oci-landing-docs`, limited to `README.md` and
  `docs/root/index.md`. Record exact head/base, paths and reason through
  `--allow-path`; do not turn these files into permanent allowed paths or reuse
  this exception for later changes. No navigation file change is needed.
  This exception was consumed by commit `fa2745ad8edf1de5c7b61896a949ac4c7d2a5981`;
  any later outside-document change needs new user direction.
- A documentation exception never authorizes Python, package metadata or a
  workflow. Keep fork tooling and this coordination file out of feature PRs.

## Owner inspection before publication

The user requires a complete local review packet and explicit approval of its
exact snapshot before feature pushes, PR creation (draft included), PR branch or
description updates, or marking a PR ready. Earlier broad publication
authorization is superseded. Continue local implementation, tests and commits.
Never infer approval from "proceed", a test pass, another agent's review, or an
older instruction. Do not create an approval record before that explicit reply.

Fetch upstream, then check every candidate branch contains the observed PR base;
fetching refs alone does not synchronize a branch. Include all paths and full
diffs, head/base/dirty state, proposed PR descriptions, scope/check evidence and
remaining live acceptance. Use the installed publication approval checker before
any publication; missing or stale approval blocks it. Changes to the snapshot
require renewed inspection and approval. Fork-only tracking and safeguards stay
outside upstream feature PRs.

Use descriptive branch names such as `fix/oci-imdsv2-launch`, without AI branding
or AI attribution/signature trailers in commits or PR text. Preserve published
history until the user approves any branch replacement. Existing planning branch
names and historical records are retained as provenance, not a naming template.

## Finish an iteration

- Update the canonical card and CURRENT summary, then append a record to
  `iterations.json`: objective, work IDs, source commit/dirty state, changes,
  checks and outcomes, observed facts, remaining hypotheses, cleanup and next step.
- Keep implementation, publication, offline checks and live acceptance separate.
  A starter branch is not implementation; a fork push is not an upstream merge;
  a unit pass or operator-identity launch is not broker-principal acceptance.
- Record dates and evidence. Preserve previous records; explain corrections in a
  later entry. Do not combine overlapping branch-suite counts into a unique total.
- Keep credentials, resource IDs, network details, resolved configs and raw cloud
  reports under ignored `work/`. Commit only sanitized summaries and references.
- End with the concrete outcome, blocker and next action. Never claim completion
  because a session ended or a tool became unavailable.

## Investigating a failed live run

- Compare with the last successful commit, identity, policy and deployment inputs.
  State observed changes separately from a demonstrated cause.
- Capture the stored provider error and request/operation IDs before closing
  temporary access. A frontend `Unknown error` is insufficient for classification.
- Workstation security-token expiry can interrupt Bastion diagnostics; it does
  not explain a broker instance-principal launch denial.
- After inconclusive permission tests, obtain the failed authorization/resource
  check from tenancy IAM or service tracing rather than repeating broader grants.
- Respect the exact scope and expiry of temporary IAM approvals. Verify removal,
  original-policy integrity and owned worker/boot-volume/session cleanup. Record
  any unconfirmed cleanup explicitly. Retain the broker when authorized.
