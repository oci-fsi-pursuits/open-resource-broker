# OCI work status and next Codex iteration

Updated **19 November 2026**. This is the readable handoff for the fork's
[canonical backlog](backlog.json) and [iteration history](iterations.json).
Runtime changes remain on their individual branches.

## Current checkpoint — 19 November

Fresh fetches confirm **organization main, local main and FINOS main all match
`3ab6716a`**, zero commits ahead or behind. Organization main had already been
updated before this iteration fetched it; no remote sync push was needed or run.
Origin now has **39 branches**, including `gh-pages`, which must be preserved.

This checkpoint collects the latest local roadmap, all **25 work cards**,
append-only iteration history and owner-inspection instructions. It stays on
the existing fork-only planning branch and outside upstream feature PRs. The
exact resulting local commit and complete diff are in ignored
`work/oci-repo-protocol-20261118/REVIEW.html`. Roadmap publication is held for
inspection; historical sections below describe their dated snapshots.

The named cleanup proposal covers **16 baseline-only starter branches**, with
their exact heads and original card/dependency mappings retained. Live GitHub
enumeration examined **14 open FINOS PRs and zero organization PRs**; none uses a
candidate branch. Current OCI PRs **877, 878, 879 and 881** remain drafts and are
preserved. No branch, worktree or remote history was deleted or rewritten.

Next: inspect this checkpoint and the exact cleanup list, approve publication
and cleanup if desired, then resume the cohesive OCI launch-controls bundle.
No new feature branch, implementation, application test, PR update or cloud run
was performed in this coordination step. The other chat's platform work is
preserved unchanged.

## Organization fork workflow and branch hygiene — 18 November

The working repository is **`oci-fsi-pursuits/open-resource-broker`** (`origin`),
with **`finos/open-resource-broker`** as `upstream`. Working from the organization
fork is the intended workflow. Live read-only checks confirmed organization
`main` at **`ff7732e3`** and FINOS `main` at **`3ab6716a`**: zero commits ahead,
1,642 behind. A normal fast-forward sync is available. No sync or push was run.
The separate screenshot with one branch and one unique commit describes a
different history; inspect that repository and preserve its unique commit before
using any discard option there.

The canonical planning branch is still **`codex/oci-feature-roadmap`**, checked
out at **`work/oci-feature-roadmap/roadmap`**. Its `roadmap/oci/` directory contains
this summary, all **25 work cards**, and append-only iteration history. Recent
updates are **uncommitted locally**, so the GitHub branch is an older checkpoint.
Do not delete or replace this checkout. Preserve its historical name until any
neutral rename and all reference changes are separately reviewed.

The coordination gap was refreshing individual feature branches and local main
without updating organization main, retaining duplicate review/history refs,
and using future-work starter branches where backlog cards would suffice. The
read-only inventory finds **38 origin branches, 45 local branches, 19 worktrees**.
**16 baseline-only starter names** can be reviewed for retirement after preserving
their card mappings. Active PR heads, unpublished implementation, dirty tracking
and live-proof references are preserved. No branch or worktree was removed.

Use this protocol going forward:

1. Sync organization `main` from FINOS with a fast-forward; inspect unique commits
   if it diverges. Fetching alone does not update a branch.
2. Keep future work in roadmap cards. Create a neutral `feat/`, `fix/` or `docs/`
   branch only when work starts, with one implementation checkout per coherent PR.
3. Record actual branch/head/base/dirty state and permitted paths before edits.
   Check each feature branch against current upstream; syncing main does not
   refresh existing feature branches.
4. Prepare the complete diff, scope, checks, upstream-formatted description and
   live limitations for owner inspection. Exact-snapshot approval is required
   before publishing feature changes or changing a PR.
5. Checkpoint the canonical roadmap after each iteration and publish it only
   after inspection. Keep fork coordination out of upstream feature PRs.
6. After merge or supersession, verify patch equivalence and evidence retention;
   obtain approval for the exact cleanup list. Never remove dirty work or assume
   that squash-merged commits are unmerged solely from ancestry.

The proposed four-feature **IMDSv2/preflight/public-IP/boot-performance bundle has
not been created**. Git metadata writes were denied by the sandbox and the
escalated creation request was declined; implementation stopped without a retry
or alternate path. Existing feature commits and PRs remain intact. TAGS and
PLACEMENT have a detailed read-only contract, not implementation or new tests.
The separate evaluation-fork/API-key work from another chat is unchanged.

Evidence: ignored `work/oci-repo-protocol-20261118/branch-audit.json`,
`remote-observation.json`, and `work/oci-next-controls-20261118/controls-proposal.json`.
Next: sync organization main, inspect/checkpoint the roadmap, approve the cleanup
list, then resume local consolidation. No force push, deletion, PR mutation or
cloud operation occurred.

## Previous single-feature staging: OCI public-IP assignment

The next bounded OCI feature is **NETWORK**, branch `feat/oci-public-ip`, clean
commit **`d837609c`**. Fresh upstream fetch confirms base **`3ab6716a`**, with
zero commits behind. The focused packet is ignored
`work/oci-public-ip-stage-20261118/STAGED_PR.html`: full five-file diff,
template-formatted description, exact evidence and unapproved push/create
snapshots. No push, PR, readiness change or cloud operation was performed.

An isolated frozen CI test/lint environment passed **434 offline OCI tests** with
the live subtree explicitly excluded. Coverage measured **9/9 changed executable
source lines** and **6/6 outcomes of new decisions** covered. Overall OCI package
line coverage in that selection was **92.52% (1237/1337)**; it is separate from
whole-project coverage. This run overlaps earlier results and includes the 35
focused cases. No new tests were written solely to improve percentages.

The strict provider scope gate passes with five OCI-owned paths and no
exceptions. Exact-commit quality/type evidence is retained. Independent review
found no concrete source blocker. Existing configured values of the previously
ignored `public_ip_assignment` field will now take effect, so review them before
deployment. Actual public/private-subnet address readback remains live acceptance
work. The shared formatter pinning failure remains separate. Both publication
gates correctly block until the owner approves this staged packet.

## Upstream descriptions applied and verified on 18 November

The owner approved applying the reviewed descriptions upstream. PRs
[877](https://github.com/finos/open-resource-broker/pull/877),
[878](https://github.com/finos/open-resource-broker/pull/878) and
[879](https://github.com/finos/open-resource-broker/pull/879) now contain the exact
reviewed template text; their source heads are unchanged. The reviewed neutral
docs branch at **`e2e32a6a`** was published as
[881](https://github.com/finos/open-resource-broker/pull/881), replacing closed
#880. Its diff contains only the approved two landing documents. The old branch
and history are preserved; no force push was used.

GitHub's Markdown renderer verified **14 sections and 28 checklist items** for
each current PR, including the approved short disclosure. All four remain drafts;
no readiness change or merge was performed. The completed code PR runs have
only the shared formatter-action failure remaining. The new docs job confirms
the same unpinned setup-action failure; five other checks were pending at the
captured read. EasyCLA passes on all four. No shared workflow was edited.

The scoped publication gates passed for the three body updates and the docs
push/create actions. NETWORK and BOOT-PERF remain local; no new feature PRs were
opened. Updated source, body or readiness actions still require their own owner
approval. Evidence and the current summary are ignored
`work/oci-pr-descriptions-20261118/UPSTREAM.html`.

## Owner review required before publication

The user requires inspecting every change before any publication. Earlier broad
publication authorization is superseded. Do not push feature changes, create a
PR (including a draft), update its branch/description or mark it ready without
explicit approval of the complete, exact local snapshot. General instructions
to proceed, successful tests and peer review are insufficient. The explicit
18 November approval above was applied only to the reviewed body updates and
docs replacement. New or changed actions require renewed approval. The previous
private publication helper is retired.

PRs [877](https://github.com/finos/open-resource-broker/pull/877),
[878](https://github.com/finos/open-resource-broker/pull/878),
[879](https://github.com/finos/open-resource-broker/pull/879) and
[880](https://github.com/finos/open-resource-broker/pull/880) were opened before
owner inspection and were held as drafts. After review, #877-879 received the
approved descriptions and #880 was closed in favor of #881. No merge was performed.

Fresh reads confirmed upstream main **`3ab6716a`**. The three code PR branches
contain it, but the original docs PR was **16 commits behind**. Fork main is
**1,642 commits behind** upstream. Local main was fast-forwarded and the same
two-line docs correction was refreshed locally as **`e2e32a6a`**; neither remote
main nor PR880 was updated. Fetching refs is separate from refreshing a branch.

Six neutral local review branches are zero commits behind the observed main:
`fix/oci-imdsv2-launch`, `feat/oci-shape-capacity`, `feat/oci-launch-preflight`,
`feat/oci-public-ip`, `feat/oci-boot-volume-performance`, and
`docs/oci-provider-introductions`. The user does not want AI-branded branch names
or AI attribution/signature trailers. Historical names remain only as provenance;
existing remote heads are not renamed or replaced without approval.

Local public-IP commit **`d837609c`** passed **434 OCI tests, one skipped**.
It uses the existing `public_ip_assignment` field and preserves saved false
against a true provider default. Local boot-performance commit **`92fedef4`**
passed **541 OCI tests, one skipped**. Strict values and an OCI-only row hook
preserve authored settings through aliases/defaults/save-reload and request
serialization. Required quality and strict scope checks passed for both.
These commits match their tested inputs and have not been pushed. Actual address
and VPU/performance readback plus boot cleanup remain live acceptance work.

Refreshed IMDS/preflight/sizing branches passed **427/501/502** offline tests
respectively. These overlap and are not a unique total. Their newer base has not
received a fresh live run; the earlier live proof remains tied to `8a4e4fb1`.
All four PRs passed CLA at the recorded read. Their formatter suggestion jobs
fail before formatting: the pinned outer reviewdog action has an unpinned
`reviewdog/action-setup@v1.5.0` dependency rejected by FINOS full-SHA policy.
This shared CI problem is outside OCI scope; no workflow was changed. Other CI
checks were still running at the recorded snapshot.

Full local review material and raw checks remain under ignored
`work/oci-status-batch-20261117/`. The local packet binds exact branch/head/base,
full diff, proposed PR text, destination and evidence. Missing or stale explicit
approval blocks publication. Tooling and this tracker remain local, outside all
feature PRs, pending inspection.

## PR description preparation and owner review on 18 November

All six local proposed descriptions now follow the verified upstream template's
14 sections and exact checklist labels. Empty issue placeholders were removed,
OCI test configuration is explicit, and unsupported tests/warnings/full-CI or
performance assertions remain unchecked. Earlier live stack evidence is
identified separately from the refreshed commits. The owner selected a short
factual assistance disclosure; it adds no signature or coauthor trailer.

The rendered preview is ignored
`work/oci-pr-descriptions-20261118/DESCRIPTIONS.html`. Preparation changed no
feature sources, tests or GitHub state. The owner subsequently approved the
upstream update described above. The refreshed landing description is now
paired with #881 at `e2e32a6a`; closed #880 preserves older `fa2745ad`.

The disclosure choice alone did not authorize publication. The subsequent
explicit upstream approval was recorded and verified for its limited actions.

## Local PR checker validation on 18 November

The repository exposes local `make` targets for required Ruff checks, Pyright,
architecture, version drift, provider tests, documentation and workflow checks.
`ci-check-quick` covers quality, architecture and version drift; it does not run
the full PR matrix. Use Python 3.12 and frozen job dependency groups. A new local
lint environment matches locked Ruff **0.17.4**; the earlier shared development
venv has **0.16.10**. Previous OCI test counts remain unchanged.

Full-repository required Ruff lint/security/format checks passed across all six
local candidates with an explicit Windows checkout adjustment. The raw runs
failed on a single tracked symlink (`test_dispatcher.py`) checked out as its
textual target name. Compatibility runs exclude that verified alias only; its
real regular-file target remains scanned. No shared script, Git setting or
feature source was modified. Exact Linux/full-matrix acceptance is not claimed.

Python-version drift and the repository action-SHA consistency validator passed.
The latter does not follow external composite actions. An additional bounded,
read-only metadata check detects the linked job's exact nested unpinned setup
action; downloaded action code was not executed. The current formatter-suggester
pin was updated upstream between the previous and current base. No shared CI
fix is included. The connected CI reader was unavailable; evidence uses the
saved exact job log and reads of the pinned public action metadata.

Repeatable native commands, Linux commands, raw/adjusted results and limits are
in ignored `work/oci-local-ci-20261118/LOCAL-CI.html`. WSL and Docker are not
installed on this workstation. No remote mutation or approval record was made.
Publication remains held for owner inspection and explicit snapshot approval.

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

The original isolated OCI-only fix is **`708e9b0c`** on
`codex/oci-imdsv2-launch`, based on then-observed upstream **`7b356262`**.
It adds optional typed `instance_options`, preserves it through template defaults
and serialization, and sends the correct API key
`instanceOptions.areLegacyImdsEndpointsDisabled`. Omission retains existing OCI
behavior; explicit `false` is preserved. The validation deployment sets `true`.
No shared runtime, IAM policy, dynamic-group rule or Bastion allowlist was changed.

The separate validation stack **`8a4e4fb1`** combines the fix with the
existing preflight feature on then-observed main. Both branches were pushed to the fork;
at that stage no new upstream PR or merge was claimed. The isolated fix passed **427 OCI offline
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

Manual verification instructions now use that already-installed local runtime and
a fresh timestamped output directory. The user-run result is **pending**; the
prior agent-run results above remain unchanged. This handoff reran no application
tests and changed no runtime source or cloud resources. Return the checks table
and any failed check before further evaluation work.

On **18 November**, the user selected a local CLI compatibility build for this
separate fork. Clean local commit **`47fec82e`** on `fix/oci-imdsv2-compat`,
based on `6bc40c19`, changes three OCI runtime files and two OCI test files.
Strict provider-level `instance_options` reaches both direct and pool SDK launch
payloads; omission retains prior behavior and explicit `false` is preserved.
Per-template metadata options remain unsupported. The archived initial template
prototype failed defaults/persistence; this smaller contract does not fix shared
template behavior or alter shared runtime.

All **302 OCI tests passed**, including 42 new cases. Strict provider scope passed
without exceptions, and tested inputs matched the final commit. Fresh wheel and
source-package builds plus new-runtime dependency checks passed with SDK
`2.192.0`. Four actual installed CLI commands passed with cloud access blocked
and zero outbound attempts. SDK serialization showed IMDSv2-only metadata,
1 OCPU/8 GB E5 sizing and a private primary VNIC. Artifact hashes and raw evidence
remain in ignored `work/other-team-orb/20261118/`; these counts are separate from
the earlier 834-test selection.

The remaining prerequisite is a dedicated API-key SDK profile: only browser-token
profiles were found, and the prepared API-key file/profile does not yet exist.
This fork still does not support workstation security-token or broker
instance-principal authentication. A local shell helper and one-E5
create/status/return plus exact worker/boot cleanup commands are ready for the
user. **No new live result is claimed.** No cloud/authentication/IAM changes,
new grants or remote publication occurred. The existing owner-review hold and
overall NETWORK/BOOT-PERF focus remain unchanged.

For API-key setup, the user will obtain/register the key in Console and wants
only CLI instructions for the local dedicated `DEFAULT` profile. It will point
to the downloaded PEM and Console-provided identity/fingerprint values in
`us-phoenix-1`; the dedicated config is still absent. Existing profile inspection
read metadata only. A browser inventory attempt ended at app-approval timeout,
with no browser control or registration. Console is the user-selected workflow;
CLI registration with a suitable valid token remains an unexecuted alternative.
No key/config, authentication or cloud changes occurred. Read-only verification
and the later live lifecycle remain pending; the local build results are unchanged.

Later on 18 November, the user reported `[NCUSATO]` ready. Protected metadata
inspection found the required API-key fields and no security-token file. The key
path had literal surrounding quotes; its unquoted target existed. Neither private
key content nor fingerprint was read. User approval rejected the prepared
activation command, so no backup, path edit, fingerprint check or ORB selection
ran. The agent will not retry or bypass that rejection.

The user then reported manually removing the quotes; this has not been
reverified. The next handoff is PowerShell permission-repair commands for the
exact private PEM and standard SDK config, followed by read-only region
subscriptions and ORB health. Those user-run checks remain pending. ORB still
selects the earlier DEFAULT/dedicated config, which is absent. No authentication
success, configuration change by the agent, new test or live resource result is
claimed. Prior build/offline results and the publication hold remain unchanged.

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
| IMDSv2 launch option incident fix | `139c2753`; #877 draft, approved description verified upstream | Shared CI clearance and maintainer review/merge |
| Launch compatibility preflight | `acf16590`; #879 draft, approved description verified upstream | Shared CI clearance and maintainer review/merge |
| Hardware sizing helper | `1f84d755`; #878 draft, approved description verified; nominal facts acceptance met | Shared CI clearance and maintainer review/merge; HostFactory integration remains separate |
| Full HostFactory/Symphony capacity | Design/proposal; not integrated | Attribute persistence/CPU policy, bootstrap, registration, workload and return |
| Public-IP assignment | Staged local `d837609c`; frozen434offline passes;9/9changed executable lines covered | Owner inspection/approval, publication and controlled live address verification |
| Boot-volume performance | Local `92fedef4`; 541 OCI passes, one skip | Owner inspection, publication and live VPU/performance/cleanup acceptance |
| Placement and defined tags | Planned | Implement and validate individually |
| Extra volumes, SDK, OKE, identity, power, pools/scaling | Design or planned | Their contracts, implementation and operational acceptance |

The original 25 cards now comprise **2 merged cards, 4 additional implemented
follow-ups, 11 design-required, 4 planned and 4 acceptance workstreams**. The IMDS
repair is tracked on the launch incident, outside that original card count.
The 501/502 historical suites share a 399-test baseline; do not add them as
1,003 unique tests. Branch starters are not completed features.

## Next iteration: owner inspection, then `NETWORK` / `BOOT-PERF` acceptance

Deliver the full local review packet. Keep all publication held until explicit
approval of the identified snapshots and destinations. After inspection, plan
bounded live acceptance of public-IP and boot-performance settings independently
from upstream review/merge. Keep the two-file landing correction separate.

Shared CLI acquire-message propagation and generic HostFactory implementation
are outside the current provider-only authorization. This `404` supplies no `OutOfHostCapacity` fixture for #677. Preserve
the original preflight branch and hardware helper provenance: their earlier
baselines differ from the refreshed review candidates. The helper's nominal
review is complete; it has no unresolved design gate. Owner inspection and
publication approval remain pending.

## Update this handoff each iteration

Read this file first, select one card/incident, and append facts/results to the
iteration history. Keep implementation, publication, offline checks and live
acceptance separate. Raw deployment evidence stays ignored; planning summaries
stay on the fork's `codex/oci-feature-roadmap` branch, outside feature PRs.
