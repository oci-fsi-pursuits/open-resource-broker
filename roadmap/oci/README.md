# OCI capability roadmap

This fork roadmap turns the **OCI Implementation Gap Assessment** of 27 October
2026 into separate, reviewable workstreams. The canonical backlog is
[backlog.json](backlog.json): 25 cards, 19 feature branches, and 39 coverage
entries. It records dependencies, design decisions, acceptance criteria, rough
effort, and unassigned owner roles. Snapshot date: **28 October 2026**.

Keep the current direct-instance provider and adopt useful capabilities
selectively. Creating a branch does not implement its feature or make an
upstream PR ready. Optional capabilities below do not become prerequisites for
merging the bounded direct-instance contribution.

## Current status

| Card | Status | Evidence and limit |
| --- | --- | --- |
| `BASE` | Implemented, pending merge | [OCI PR #234](https://github.com/finos/open-resource-broker/pull/234), revision `21b3bd05`; local installed-wheel selection: 591 tests passed. Required upstream CI/review remain separate. |
| `DOC-RDMA` | Implemented, pending merge | Signed launch JSON and existing field mappings are documented in the OCI contribution. This does not demonstrate RDMA performance. |
| `HF-FACTS` | Implemented, pending integration | Helper `1befd18b`: 381 offline OCI unit/mocked tests passed, including 103 helper tests. Hardware facts are not yet connected to HostFactory output. |
| Other 22 cards | Design, planned, or validation pending | Their branches are starters, with no feature implementation. See each card's acceptance and design gates. |

Baseline revisions are pinned in the JSON: main `2a772479`, OCI `21b3bd05`, and
capacity helper `1befd18b`. Recheck upstream state before development or review.
The catalog's **25 examples across 23 shapes** are template coverage, not tested
regional availability or live acceptance of every shape.

## Priority and dependency order

1. Preserve and land the current OCI lifecycle/privacy fixes and RDMA guide.
2. Develop CLI launch preflight independently. Agree the generic HostFactory
   attribute representation/persistence contract before integrating OCI capacity.
3. Add optional placement, public-IP, tagging, and boot-performance controls in
   their own provider branches; maintain old templates and defaults.
4. Design larger storage, identity, SDK/OKE, power, and pool capabilities with
   explicit ownership and persistence contracts.
5. Add scheduled scaling only after pool contracts settle scheduler authority,
   draining, scale-in, and changing-capacity accounting. Close the applicable
   operational acceptance before claiming that capability is production ready.

**SDK is optional.** Preflight, placement, networking, tags, storage, and pools can
use the current CLI transport. OKE manifests can advance in parallel with auth
design, but live deployment needs a chosen image, transport, and identity model.
The SDK workload signer depends on both SDK and OKE deployment foundations.

Generic HostFactory, identity, and pool contracts are shared PRs. Their OCI
consumers are provider PRs. Do not merge unlanded shared infrastructure into OCI
#234. Rebase provider follow-ups onto main containing OCI and the accepted
contracts before opening upstream PRs; check that the diff contains only the
intended follow-up.

## Feature branches

`main` below means `upstream/main` at the pinned baseline. `OCI` means the
validated base of [PR #234](https://github.com/finos/open-resource-broker/pull/234).
Branch starting points and design dependencies are different: a starter can be
created now and still require an accepted interface before implementation.

| Fork branch | Starting point | Scope | State |
| --- | --- | --- | --- |
| [codex/hostfactory-template-attributes](https://github.com/oci-fsi-pursuits/open-resource-broker/tree/codex/hostfactory-template-attributes) | main | Shared attribute contract | Existing starter |
| [codex/oci-capacity-helper](https://github.com/oci-fsi-pursuits/open-resource-broker/tree/codex/oci-capacity-helper) | OCI | Provider hardware facts | Implemented foundation |
| [codex/oci-hostfactory-capacity](https://github.com/oci-fsi-pursuits/open-resource-broker/tree/codex/oci-hostfactory-capacity) | Capacity helper | Provider scheduler adapter | Existing starter |
| [codex/oci-launch-preflight](https://github.com/oci-fsi-pursuits/open-resource-broker/tree/codex/oci-launch-preflight) | OCI | Provider launch validation | Existing starter |
| [codex/oci-placement-controls](https://github.com/oci-fsi-pursuits/open-resource-broker/tree/codex/oci-placement-controls) | OCI | Fault domains/reservations | Starter |
| [codex/oci-network-controls](https://github.com/oci-fsi-pursuits/open-resource-broker/tree/codex/oci-network-controls) | OCI | Public-IP controls | Starter |
| [codex/oci-defined-tags](https://github.com/oci-fsi-pursuits/open-resource-broker/tree/codex/oci-defined-tags) | OCI | Defined tags | Starter |
| [codex/oci-boot-performance](https://github.com/oci-fsi-pursuits/open-resource-broker/tree/codex/oci-boot-performance) | OCI | Boot-volume performance | Starter |
| [codex/oci-secondary-volumes](https://github.com/oci-fsi-pursuits/open-resource-broker/tree/codex/oci-secondary-volumes) | OCI | Owned volumes/retention | Starter |
| [codex/oci-sdk-transport](https://github.com/oci-fsi-pursuits/open-resource-broker/tree/codex/oci-sdk-transport) | OCI | Optional SDK transport | Starter |
| [codex/oci-oke-workload-identity](https://github.com/oci-fsi-pursuits/open-resource-broker/tree/codex/oci-oke-workload-identity) | SDK starter | Additional identity mode | Starter |
| [codex/oci-oke-deployment](https://github.com/oci-fsi-pursuits/open-resource-broker/tree/codex/oci-oke-deployment) | OCI | Image/manifests/deployment | Starter |
| [codex/machine-identity-aliases](https://github.com/oci-fsi-pursuits/open-resource-broker/tree/codex/machine-identity-aliases) | main | Shared identity contract | Starter |
| [codex/oci-identity-aliases](https://github.com/oci-fsi-pursuits/open-resource-broker/tree/codex/oci-identity-aliases) | OCI | Provider identity consumer | Starter |
| [codex/oci-power-actions](https://github.com/oci-fsi-pursuits/open-resource-broker/tree/codex/oci-power-actions) | OCI | Provider start/stop | Starter |
| [codex/pool-lifecycle-contracts](https://github.com/oci-fsi-pursuits/open-resource-broker/tree/codex/pool-lifecycle-contracts) | main | Shared pool contract | Starter |
| [codex/oci-instance-pools](https://github.com/oci-fsi-pursuits/open-resource-broker/tree/codex/oci-instance-pools) | OCI | Provider pools | Starter |
| [codex/oci-scheduled-scaling](https://github.com/oci-fsi-pursuits/open-resource-broker/tree/codex/oci-scheduled-scaling) | Pool starter | Provider schedules | Starter |
| [codex/oci-validation-runbooks](https://github.com/oci-fsi-pursuits/open-resource-broker/tree/codex/oci-validation-runbooks) | OCI | Tests and documentation | Starter |

Owners remain **unassigned**. Estimates in the JSON are rough single-engineer
implementation/test sizing, overlap, and exclude external reviews, IAM/quota
waits and live costs. Do not sum them into a delivery forecast.

## Compatibility and template controls

Preserve existing names and precedence; additions below require explicit alias,
validation, persistence, and payload tests. This table describes roadmap coverage,
not a claim that these options are already implemented.

| Fields or behavior | Planned treatment | Cards |
| --- | --- | --- |
| `provider_api`: `ComputeInstance` / `InstancePool` versus `OCICompute` | Keep current OCICompute and persisted IDs; introduce any pool API deliberately. | `BASE`, `SDK`, `POOL-SHARED`, `POOL-OCI` |
| `max_machines`, `max_instances`, `max_capacity` | Preserve existing capacity aliases; distinguish machine count from hardware size and delivered pool capacity. | `BASE`, `POOL-SHARED`, `POOL-OCI` |
| `shape`, `ocpus`, `memory_in_gbs` versus `machine_types`, `shape_config`, `memory_gbs` | Keep launch alias/default precedence and consistent Flex sizing. | `HF-FACTS`, `HF-OCI`, `PREFLIGHT` |
| Explicit scheduler `attributes` | Preserve authored/custom values; recalculate derived values after resizing. A catalog-only attribute addition is insufficient. | `HF-SHARED`, `HF-OCI` |
| `ssh_public_key_path` / `cloud_init` versus inline `ssh_authorized_keys` / encoded `user_data` | Retain current key/bootstrap semantics; any path/raw aliases must be explicit and portable, not forced workstation paths. | `BASE`, `SDK`, `DOC-RUNBOOKS` |
| `credential_source` versus `auth_mode`, `profile`, `config_file` | Preserve API keys, security-token/profile, instance and resource principals; add workload identity as another mode. | `BASE`, `SDK`, `OKE-AUTH` |
| Provider/per-template region, compartment, AD and subnet | Preserve resolved defaults and per-template overrides rather than requiring new provider-level placement everywhere. | `BASE`, `PLACEMENT`, `NETWORK` |
| `fault_domains`, `capacity_reservation_id` | Add optional existing placement controls; direct single-domain and pool multiple-domain behavior are distinct. | `PLACEMENT`, `POOL-OCI` |
| `assign_public_ip`, `nsg_ids` / `security_group_ids` | Add public-IP choice with agreed omission/default behavior; keep existing NSG support. | `NETWORK` |
| `boot_volume_size_in_gbs` / `boot_volume_gbs`, `boot_volume_vpus_per_gb` | Preserve boot size; add performance independently from DenseIO local NVMe. | `BOOT-PERF` |
| `secondary_volumes`: `size_in_gbs`, `vpus_per_gb`, `display_name`, `delete_on_return` | Define owned create/attach/retain/delete/restart behavior and future pool-volume policy. Guest mounting is separate. | `VOLUMES`, `POOL-OCI` |
| Freeform `tags`, `metadata`, and namespaced `defined_tags` | Preserve privacy, input immutability and reserved ownership tags; validate additions without silent key collisions. | `TAGS`, `BASE` |
| `autoscaling_schedules` / nested `autoscaling.schedules`: `name`, `cron`, `target_capacity` | Unique named UTC Quartz schedules within configured capacity limits, with owned cleanup and safe scale-in. | `SCHEDULES` |
| `price_type="spot"` versus `capacity_type="preemptible"` | Preserve current capacity selection, boot preemption policy, and capacity-error-only on-demand fallback; no silent field substitution. | `BASE`, `ACCEPT-AUTH-SHAPES` |

Existing NSGs, Compute Cluster placement and current principal modes remain
supported behavior to preserve. Automatic cluster/network creation is not added
by this roadmap. Power actions use the **existing** generic action interface;
they do not assume another shared interface must be created.

## Acceptance and release boundaries

Every card has concrete acceptance in [backlog.json](backlog.json). Important
cross-cutting work includes:

- Real image/subnet/Flex validation, current auth modes, representative shape
  families, preemptible interruption/fallback and independent resource cleanup.
- Multi-node RDMA agents/drivers/connectivity and a measured workload; instance
  creation or cluster membership alone is not a performance result.
- Actual Symphony bootstrap, registration, advertised-versus-real capacity,
  task execution, draining and return. Unit/mocked workflows are insufficient.
- Durable volume/pool/schedule ownership after restart, pagination, partial
  failure cleanup, controller-versus-member accounting, and scale-out/scale-in.
- Relevant REST fixture coverage, correct pool success percentages and refreshed
  nested lifecycle data; prior evaluation reports must be reproduced rather
  than treated as a current passing full suite.
- A freshly built OCI-capable image, required CLI/SDK dependencies, writable
  state, correct API-only/embedded-UI probes, API authentication and dependency/
  image security. Do not reintroduce obsolete certificate package pins.
- OKE IAM, pod recreation and actual storage recovery. Single-replica/PVC
  scaffolding does not prove HA, database concurrency or production security.
- Current commit/dirty-state/command/result/artifact-hash provenance. Keep local
  configs, credentials, confidential source and raw deployment evidence out of
  public changes and release inputs; confirm permission/attribution before reuse.

Live execution is a separately authorized, bounded activity. This roadmap creates
no cloud resources. Record tested, untested and unavailable combinations rather
than inferring all-shape acceptance from the catalog or a single-worker canary.

## Coverage crosswalk

The JSON `coverage` array maps every entry below to card IDs, and each card's
`source_refs` maps back to those entries. The validator checks that relationship.

| Coverage IDs | Assessment content |
| --- | --- |
| `C01`-`C12` | Transport/auth; direct VMs; preflight; placement/network; storage/tags; pools; schedules; OKE; HostFactory; name/DNS returns; power actions; HPC/preemptible |
| `P01`-`P08` | RDMA text; scheduler capacity; preflight; optional controls; OKE deployment; SDK/identity; volumes; pools then schedules |
| `K01`-`K05` | Provider APIs/IDs; placement/auth; shape/memory; key/bootstrap; network/storage compatibility |
| `S01`-`S03` | Lifecycle/privacy invariants; pool/scale ownership and failure safety; portable secure deployment |
| `E01` | Auth modes and representative all-family sizing |
| `E02` | Preemptible interruption, fallback and retention |
| `E03` | Larger pool counts and pagination |
| `E04` | Real scale-out and scale-in |
| `E05` | REST fixtures, pool percentages and lifecycle freshness |
| `E06` | Measured multi-node RDMA |
| `E07` | Real Symphony acceptance |
| `E08` | OKE identity, restart, persistence, HA/database limits |
| `E09` | Container, release-input privacy, API/dependency security |
| `E10` | Current reproducible evidence and runbooks |
| `E11` | Reuse permission, attribution and confidential-source boundaries |

## External work and review discipline

[OCI #234](https://github.com/finos/open-resource-broker/pull/234),
[Azure #588](https://github.com/finos/open-resource-broker/pull/588), and
[packaging #589](https://github.com/finos/open-resource-broker/pull/589) are open in
this snapshot. [Issue #622](https://github.com/finos/open-resource-broker/issues/622)
tracks maintainer-owned follow-ups; it is a reference, not a request to duplicate
their implementation. Waiting workflows or reviews are not passing CI.

Use the repository's [provider guide](../../docs/root/developer_guide/adding_a_provider.md)
and [multi-provider design](../../docs/root/architecture/multi-provider-design.md).
Provider rules/calculations belong inside the provider; shared adapters remain
generic. Establish exact shared-PR paths after design, review shared metadata
content, and run the final scope/tests against the precise publication commit.
The roadmap itself is fork planning, not a patch to the current OCI feature.

Validate the canonical backlog with:

```sh
python roadmap/oci/validate_roadmap.py
```

To check the local starter refs and their bases in the prepared workspace:

```sh
python roadmap/oci/validate_roadmap.py --check-refs --repo /path/to/checkout
```

This check reads local refs. Fetch or prepare the named refs before using it in a
fresh clone; it does not fetch branches or create them automatically.
