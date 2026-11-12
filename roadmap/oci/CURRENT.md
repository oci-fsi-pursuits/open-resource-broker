# OCI work status and next Codex iteration

Updated **12 November 2026**. This is the readable handoff for the fork's
[canonical backlog](backlog.json) and [iteration history](iterations.json).
Runtime changes remain on their individual branches.

## Current blocker: broker-principal launch

The last proven broker-principal E5 lifecycle passed on **22 October at 08:59 PT**,
commit `7f6f13c5`. Acquire completed, the worker was terminated, and no new
persistent boot volume remained. It used the original parent compartment. The
retained historical IAM snapshot has four broad grants; its capture is not a
timestamped policy audit of the October 22 run.

The current tested source is `0dbc17f6`, based on `071f4596`. The same retained
broker now has eleven restricted policy statements, and workers target a dedicated
child compartment. The original image, subnet, NSG, AD and sizing were otherwise
unchanged for the initial failing tests. Later controls deliberately used a stock
Ubuntu image. The date and actor of the IAM changes have not been established.

These are observed differences, **not a proven root cause**:

- Broker-principal native OCI CLI and ORB launches returned 404 on the earlier
  attempts. The equivalent stock-image launch under the operator identity reached
  RUNNING and was cleaned up on 12 November. This points toward broker
  authorization/context rather than an ORB-only launch defect.
- Real compatibility reads and an oversized-memory rejection passed on the fresh
  installed build. The negative probe made zero launch calls.
- The inherited Security Zone's only enabled rule concerns load-balancer SSL;
  it does not apply to this Compute launch.
- The approved scoped IAM test returned the earlier 404. The later catalog-read
  test failed with frontend `Unknown error`; its stored provider detail remains
  unread. Do not label that latest result another 404 or a confirmed catalog fix.
- Temporary grants were removed, the original policy and local configuration were
  restored, and post-test inventory found zero active test workers/boot volumes.
  Owned temporary Bastion sessions were closed; the broker was retained.

Workstation token expiry interrupted the final diagnostic read. It is separate
from the broker's instance-principal authentication.

## Feature delivery

| Work | Implementation / publication | Acceptance still needed |
| --- | --- | --- |
| Base OCI provider and RDMA placement guide | Merged in #234 | Current principal regression; broader shape/auth coverage; measured RDMA |
| Azure optional transport / container fixes | #588 and #589 merged | Deployment-specific container/platform acceptance |
| Launch compatibility preflight | Pushed, `0dbc17f6`; 501 offline OCI tests | Successful current broker-principal acquire/status/return; upstream review |
| Hardware sizing helper | Pushed, `60a511cc`; 502 offline OCI tests | Review/merge; generic HostFactory contract and OCI consumer |
| Full HostFactory/Symphony capacity | Design/proposal; not integrated | Attribute persistence/CPU policy, bootstrap, registration, workload and return |
| Placement, public-IP, defined tags, boot performance | Planned | Implement and validate individually |
| Extra volumes, SDK, OKE, identity, power, pools/scaling | Design or planned | Their ownership/contracts, implementation and operational acceptance |

The 25 cards comprise **2 merged cards, 2 additional implemented follow-ups,
11 design-required, 6 planned and 4 acceptance workstreams**. The helper and
preflight suites share a 399-test baseline; 501 + 502 is not 1,003 unique tests.
Branch starters are not completed features.

## Next iteration: `INC-OCI-LAUNCH-001`

**Objective:** retrieve the actual stored provider error from the latest catalog
canary, then identify its failing operation. No further IAM grant is needed for
the read. The exact request and private evidence are in the ignored local
`work/oci-review-20261110/` records.

1. Use renewed operator access to read that stored request and capture its
   provider detail in the same short access session. Close the owned session.
2. If it remains an unexplained authorization denial, request tenancy IAM/Compute
   tracing of the exact failed permission/resource check, using the successful
   operator control and the last-good broker-principal comparison. Further IAM
   experiments need a specific new hypothesis and appropriate authorization.
3. If it is capacity, capture the real sanitized response for issue #677. If it
   is another error, follow that evidence before launching again.
4. Complete the current broker-principal lifecycle and verify cleanup before
   marking live acceptance passed.

Independent work may proceed on the hardware-helper review and the generic
HostFactory contract. The shared CLI error-detail loss is diagnosed but has no
implementation; keep that fix separate from OCI behavior.

## Source freshness and review order

The active follow-ups were tested against upstream `071f4596`. GitHub main was
observed at `7b356262` on 12 November, **34 commits newer**. That comparison changes
shared HostFactory/DTO/formatting code and contains no OCI-provider file changes.
Review those changes and refresh each active branch before publication; existing
test results do not establish compatibility with the newer base.

After the launch investigation: review preflight and the helper independently,
agree the generic HostFactory contract, then implement its OCI consumer. Preserve
existing provider behavior and advance the other controls in separate changes.

## Update this handoff each iteration

Read this file first, select one card/incident, and append facts/results to the
iteration history. Update the corresponding backlog progress dimensions and this
summary before handing work back. Preserve unknowns and failed experiments.
Raw deployment evidence stays ignored; planning summaries stay on the fork's
`codex/oci-feature-roadmap` branch, outside upstream feature PRs.
