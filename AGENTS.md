# ORB fork contribution boundaries

For provider development or PR preparation, use
`.agents/skills/orb-provider-review/SKILL.md` before editing and before publishing.
Read the current provider guide and relevant review feedback; explain planned
paths and validation, then proceed within the user's existing authorization.

- Provider behavior belongs under `src/orb/providers/<provider>/`, using the
  registered extension points. Do not put provider imports, provider-name
  branches, or provider-specific fields into shared runtime code.
- Keep OCI #234, Azure #588, packaging #589, and generic HostFactory changes
  separate. A needed shared extension is a separate change to explain and scope;
  do not quietly widen the OCI feature.
- These safeguards belong to the fork tooling branch. Do not merge the tooling
  branch into an upstream feature branch or include it in an upstream PR.
- The checker verifies paths, not correctness or permission. Shared metadata
  files still need content review. Do not grant yourself scope exceptions;
  record exact paths and reasons only for exceptions the user selected.
- Tie validation to the tested commit and working-tree state. If files changed
  after a check, rerun the affected checks before publishing; distinguish source
  tests, installed-wheel tests, mocked cloud checks, and live acceptance.
- Preserve local configurations and private evidence under ignored `work/`.
  Keep credentials, deployment records, actual resource IDs, and private-fork
  source out of release inputs and public changes.

Existing task authorization remains valid. A scope failure stops publication of
the affected changes; continue independent work already within the agreed scope.
