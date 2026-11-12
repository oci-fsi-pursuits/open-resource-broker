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
