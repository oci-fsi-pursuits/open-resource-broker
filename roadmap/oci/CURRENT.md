# OCI work status and next Codex iteration

Updated **17 November 2026**. This is the readable handoff for the fork's
[canonical backlog](backlog.json) and [iteration history](iterations.json).
Runtime changes remain on their individual branches.

## Resolved launch blocker: IMDS policy requirement

The user's manual request failed with stored `404 NotAuthorizedOrNotFound`.
The matching audit confirms `LaunchInstance` under the retained broker principal;
its generic error did not name the denied check. SSH worked, so workstation access
did not block that run. The candidate Bastion IP addition remains unapplied.

A fresh full policy read found a root **IAM Deny** rejecting instance creation
unless legacy metadata endpoints are disabled. The previous OCI launch body did
not carry `instanceOptions`. This is separate from the previously inspected
Security Zone rule, which concerns load-balancer SSL. Four metadata-related Deny
statements are absent from the 16 October policy snapshot and present on
17 November. Their exact addition date and actor have not been established.

Deny takes precedence over Allow. The earlier standard grants and catalog-read
grant were tested separately, not together. Default administrators are exempt
from Deny, which is consistent with the earlier operator-identity success;
operator membership in that group was not independently verified.

The last historical successful broker lifecycle was 22 October, commit
`7f6f13c5`. Current fresh reads confirmed the same broker identity and the old
installed commit/source hashes, instance-principal authentication without a
profile, and the expected E5 sizing/network tuple. The resolved image is the
stock Ubuntu control image, rather than the restored workstation-state image.
The retained four-grant historical snapshot is not a timestamped policy audit
of the 22 October success.

## Fix and validation

The isolated OCI-only fix is **`708e9b0c`** on
`codex/oci-imdsv2-launch`, based on current observed upstream **`7b356262`**.
It adds optional typed `instance_options`, preserves it through template defaults
and serialization, and sends the correct API key
`instanceOptions.areLegacyImdsEndpointsDisabled`. Omission retains existing OCI
behavior; explicit `false` is preserved. The validation deployment sets `true`.
No shared runtime, IAM policy, dynamic-group rule or Bastion allowlist was changed.

The separate validation stack **`8a4e4fb1`** combines the fix with the
existing preflight feature on current main. Both branches are pushed to the fork;
no new upstream PR or merge is claimed. The isolated fix passed **427 OCI offline
tests**; the combined stack passed **529**. Required lint/security/format and OCI
type checks passed. These suites overlap and are not 956 unique tests.

The fresh combined build passed **one E5 acquire/status/return lifecycle** under
the retained broker instance principal. OCI reports legacy metadata endpoints
disabled. Independent inventory found zero active owned workers and zero active
worker boot volumes, with no operator fallback. The owned Bastion session was
removed and the broker policy remained unchanged. The broker is retained.
A post-canary read confirmed that the root Assurance policy still matches the
earlier recorded statements and retains the active IMDSv2 creation guard.

Workstation security-token expiry interrupted the first pre-canary inventory.
A local controller empty-list parsing error stopped another attempt before any
resource creation. The corrected final run used one owned temporary Bastion
session. The existing broker and earlier test checkout were retained. No support
request was submitted; support submission remains unauthorized.

Fresh wheel and source-package artifacts were built on Linux from the exact
validation commit when recorded in the final report. The UI build was skipped.
No Docker, all-shape, RDMA throughput or Symphony acceptance is claimed.

## Other-team evaluation fork: local validation on 17 November

The user selected local build/validation first for the separate SDK-based
evaluation fork. A fresh checkout at `6bc40c19` remains clean. A wheel and source
archive built using the documented existing-backend procedure; a new runtime
passed dependency checks and OCI plugin registration with SDK `2.192.0`.

The installed-wheel focused selection collected 834 tests: **830 passed and four
failed**, with all **260 OCI tests passing as a subset**. The four shared scheduler
failures concern Windows home expansion, POSIX permission assumptions and path
separators. Tests were retained unchanged. The final run allowed loopback for
Windows asyncio while blocking outbound connections, and verified 602 imported
ORB modules under the isolated wheel environment.

All 31 OCI Python/JSON inputs match the wheel; ten AWS/Kubernetes JSON inputs are
absent. Their unexercised runtime impact remains unknown. Native CLI server startup
uses `fcntl`; the local API smoke exercises the installed app directly through
Uvicorn. Its result is **pass**; this does not establish Linux CLI daemon,
UI, container, OKE or OCI lifecycle acceptance. The test server was stopped.
Liveness/readiness returned 200; the health endpoint returned 503 with workstation
memory at 95.6%. This is recorded as a host-health limit, not a full health pass.

The fork's authentication contract offers API keys and OKE workload identity,
not broker instance principals. No cloud resources, IAM or Bastion access were
changed by that separate evaluation. Its historical handoff preceded the retained
broker's IMDS investigation and successful lifecycle reported above. Raw evidence
stays under ignored `work/other-team-orb/20261117/`.

## Provider-only guardrails confirmed on 17 November

All new OCI code work uses the installed **`oci-provider`** gate: only
`src/orb/providers/oci/`, `tests/providers/oci/`, and
`docs/root/providers/oci/` are allowed. IMDS (7 paths), combined validation
(11), original preflight (6), and the capacity helper (2) passed the applicable
strict profiles with no exceptions. Use these isolated publication branches;
the main workspace's older coordination branch is not a new OCI PR candidate.

Shared CLI, DTO/domain, scheduler/HostFactory, other-provider, dependency,
packaging and workflow changes remain outside this queue. The generic
`Unknown error` and HostFactory proposals are deferred as separately scoped work.
The wider `oci-234` profile is historical-only and requires an explicit flag.

The sole one-time landing-page exception is **`fa2745ad`** on
`codex/oci-landing-docs`: `README.md` and `docs/root/index.md` now include OCI
in their provider introductions/lists. The navigation already linked OCI.
The two-file branch fails without its exact document declarations and reason;
these paths are not added to the provider allowlist or authorized for later edits.

Fork-only guardrail commit **`0e89bddf`** is installed locally.
Guardrail tests recorded **36 passes and one Windows-specific skip**; required
lint/format and real-branch/negative checks passed. This is a local
pre-publication gate; no GitHub branch-protection or CI workflow was changed.

## Feature delivery

| Work | Implementation / publication | Acceptance still needed |
| --- | --- | --- |
| Base OCI provider and RDMA placement guide | Merged in #234 | Broader shape/auth coverage and measured RDMA |
| Azure optional transport / container fixes | #588 and #589 merged | Deployment-specific container/platform acceptance |
| IMDSv2 launch option incident fix | Pushed, `708e9b0c`; 427 offline tests | Upstream review and merge |
| Launch compatibility preflight | Original fork branch `0dbc17f6`; fresh combined validation `8a4e4fb1` | Independent publication-branch refresh/review and upstream merge |
| Hardware sizing helper | Pushed, `60a511cc`; 502 offline OCI tests | Refresh/review/merge; generic HostFactory contract and OCI consumer |
| Full HostFactory/Symphony capacity | Design/proposal; not integrated | Attribute persistence/CPU policy, bootstrap, registration, workload and return |
| Placement, public-IP, defined tags, boot performance | Planned | Implement and validate individually |
| Extra volumes, SDK, OKE, identity, power, pools/scaling | Design or planned | Their contracts, implementation and operational acceptance |

The original 25 cards still comprise **2 merged cards, 2 additional implemented
follow-ups, 11 design-required, 6 planned and 4 acceptance workstreams**. The IMDS
repair is tracked on the launch incident, outside that original card count.
The 501/502 historical suites share a 399-test baseline; do not add them as
1,003 unique tests. Branch starters are not completed features.

## Next iteration: `PREFLIGHT`

Publish the isolated IMDS fix and refreshed preflight under `oci-provider`, keeping the one-time two-file landing-page correction independent.

Shared CLI acquire-message propagation and generic HostFactory implementation
are outside the current provider-only authorization. This `404` supplies no `OutOfHostCapacity` fixture for #677. Preserve
the original preflight branch and hardware helper provenance: their earlier
baselines differ from the newly refreshed validation stack. The hardware helper
still needs review against current main before publication.

## Update this handoff each iteration

Read this file first, select one card/incident, and append facts/results to the
iteration history. Keep implementation, publication, offline checks and live
acceptance separate. Raw deployment evidence stays ignored; planning summaries
stay on the fork's `codex/oci-feature-roadmap` branch, outside feature PRs.
