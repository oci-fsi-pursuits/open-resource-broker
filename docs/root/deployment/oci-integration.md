# OCI Integration Guide

This guide documents OCI provider support in Open Resource Broker and the
recommended operational flow.

For handler fields, machine data, fulfilment, and release behaviour, see the
[OCI Compute Instances provider reference](../providers/oci/compute.md).

## Overview

OCI support includes:

- template lifecycle operations (validate, create, update, list, show, delete)
- machine acquire and return workflows through OCI compute
- provider routing via `provider_name=oci-default`, `provider_type=oci`,
  `provider_api=OCICompute`

## Installation and initialization

Install ORB from this branch (`pip install -e .`) and install the OCI CLI separately.
The provider uses the `oci` executable on PATH; importing ORB does not require the OCI SDK.
OCI is discovered through the `orb.providers` entry point.

```bash
orb init --non-interactive --provider-type oci --oci-region us-phoenix-1 --oci-credential-source instance_principal
orb templates generate
orb templates list
```

For a workstation, use `--oci-credential-source profile --oci-profile DEFAULT`.
Custom profile names are supported by `--oci-profile`. For Symphony, add
`--scheduler hostfactory` to initialization. With a custom `--config-dir`, pass
`--config /path/to/config.json` to subsequent commands.

### Local browser-session authentication

For an existing OCI CLI session, use its profile name and select `security_token`
explicitly. This passes both `--auth security_token` and `--profile` to OCI CLI:

```bash
oci session authenticate --region us-phoenix-1 --profile-name ORB
orb init --non-interactive --provider-type oci --oci-region us-phoenix-1 --oci-credential-source security_token --oci-profile ORB
```

Use an existing session profile instead of `ORB` if one is already configured.
Session tokens expire; reauthenticate when needed. Provider health checks validate
configuration structure, so verify a read-only OCI API call before provisioning.
See [Oracle's token authentication guide](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/clitoken.htm).

## Provider configuration

Choose exactly one OCI config baseline:

```bash
# Remote/production: ORB runs on OCI Compute with instance principal auth.
cp config/oci_config.remote.example.json config/oci_config.json

# Local/dev: ORB runs on a workstation with an OCI CLI profile.
cp config/oci_config.local.example.json config/oci_config.json
```

Remote instance-principal config uses `credential_source: instance_principal` and must not set `profile`. Local profile config uses `credential_source: profile` and `profile: DEFAULT`; `DEFAULT` is the standard OCI CLI profile name and can be replaced with another `~/.oci/config` profile.

Remote provider block:

```json
{
  "provider": {
    "providers": [
      {
        "name": "oci-default",
        "type": "oci",
        "enabled": true,
        "config": {
          "region": "us-phoenix-1",
          "credential_source": "instance_principal"
        }
      }
    ]
  }
}
```

OCI templates keep compute-grid choices in `config/oci_templates.json`. Deployment-specific values such as image OCID, subnet OCID, compartment OCID, NSGs, SSH keys, tags, and user data live in `provider_defaults.oci.template_defaults` in the config file.

### Broker instance-principal setup

Use Python 3.12 for the broker's virtual environment. The current branch imports
newer typing features during startup; Ubuntu 22.04's default Python 3.10 fails
before OCI provisioning even though package metadata currently permits 3.10.
This runtime requirement concerns the broker; worker images need the runtime
required by their own workload and bootstrap.

Create a dynamic group matching the broker instance explicitly, for example:

```text
ALL {instance.id = '<broker-instance-ocid>'}
```

For a broker provisioning into one compartment, the tested policy grants are:

```text
Allow dynamic-group <broker-group> to manage instance-family in compartment id <worker-compartment-ocid>
Allow dynamic-group <broker-group> to use volume-family in compartment id <worker-compartment-ocid>
Allow dynamic-group <broker-group> to use virtual-network-family in compartment id <worker-compartment-ocid>
Allow dynamic-group <broker-group> to use compute-clusters in compartment id <worker-compartment-ocid>
```

The compute-cluster grant is needed for RDMA cluster placement. These statements
assume the worker subnet, NSGs, custom image, and cluster are in that compartment;
adjust policy scope when resources are elsewhere. Membership must not include
workers merely because they share the broker's compartment. See
[Oracle's instance-principal guide](https://docs.oracle.com/en-us/iaas/Content/Identity/Tasks/callingservicesfrominstances.htm).

Install ORB and OCI CLI in virtual environments on the broker, configure
`credential_source: instance_principal`, and verify API access there before a live
canary. No OCI profile, user private key, or workstation session token is needed
on the broker. A profile-based workstation canary does not validate this path.
Use the one-machine gate below from the broker itself, then independently inspect
worker termination and boot-volume cleanup. Remove temporary validation IAM grants
when retiring a disposable test broker.

#### Validation record: 2026-10-16 UTC

A fresh core wheel passed the one-worker lifecycle gate from a private Ubuntu
24.04 broker in Phoenix AD-2, using Python 3.12.3 and OCI CLI 3.94.1. The broker
ran with an empty home directory, no OCI config/profile, and no OCI credential
environment variables. ORB generated all 25 templates, acquired a
`VM.Standard.E5.Flex` worker with 1 OCPU / 8 GB, reported its private IP/DNS name,
and returned it successfully. OCI independently confirmed termination; the worker
needed no fallback termination. A 100 GB boot disk matched the existing custom
image's minimum size. OCI Audit recorded the broker instance as the principal for
the worker's successful `LaunchInstance` and `TerminateInstance` calls, with auth
type `instance`. Both VMs and their boot volumes were removed after validation,
along with the temporary dynamic group, policy, NSG, and Bastion session; the
existing Bastion egress rules were restored.

Instance-principal preflight also read the existing RDMA compute cluster and
listed its members. This verifies cluster visibility; RDMA worker launch and
RDMA/MPI performance were tested separately using workstation authentication.
Actual Symphony registration remains a separate acceptance test.

## Authentication precedence

OCI CLI auth selection order:

1. provider config `credential_source`
2. `ORB_OCI_CREDENTIAL_SOURCE`
3. `OCI_CLI_AUTH`
4. profile fallback

Supported credential source values:

- `instance_principal`
- `resource_principal`
- `api_key`
- `security_token` (requires a session profile)
- `profile`
- `default`

## Template contract (OCI)

See [Compute templates and Flex sizing](../providers/oci/templates.md) for AMD
E5/E6, Intel, Ampere, Standard, and DenseIO coverage, including image architecture
and DenseIO sizing requirements.

Required fields for reliable launches:

- `image_id` from template defaults
- `subnet_ids[0]` from template defaults
- `compartment_id` from template defaults
- shape from the template `machine_types`, `shape`, `instance_type`, or defaults

Recommended:

- `ssh_authorized_keys`
- `user_data` (base64 cloud-init)

## Runtime flow

For `BM.Optimized3.36` workers in an RDMA network group, see
[Compute Clusters and RDMA](../providers/oci/compute-clusters.md). The
`oci-bm-optimized3-rdma` example requires its own HPC image, compute cluster OCID,
and matching availability domain; replace its placeholders before requesting nodes.

After filling the deployment defaults in `config/oci_config.json`, generate and
list templates. Generation writes the provider-owned catalog into the configured
template directory; defaults are resolved when those templates are loaded.

```bash
orb --config config/oci_config.json templates generate
orb --config config/oci_config.json templates list
orb --config config/oci_config.json templates validate oci-vm-flex-ondemand-small
```

The following commands provision and terminate real instances:

```bash
orb --config config/oci_config.json machines request oci-vm-flex-ondemand-small 1 --provider-name oci-default
orb --config config/oci_config.json requests status <request-id>
orb --config config/oci_config.json machines return <instance-ocid> --provider-name oci-default
```

`templates create --file` and `templates update --file` accept a single template
object, not the full `{"templates": [...]}` catalog. The pre-live gate script
selects the requested catalog entry and resolves its defaults before calling them.

## Integration notes

- OCI-specific defaults, CLI options, template fields, and HostFactory mappings
  are registered by `OCIPlugin`; shared bootstrap and orchestration require no
  OCI-specific branches.
- Template input accepts canonical `machine_image`, `machine_type`, and
  `machine_disk_size_gb` as well as the existing OCI catalog fields.
- Live launch results require asynchronous polling. Status and resource discovery
  return ORB's flat instance-list format, normalized machine states, and the
  `ProviderFulfilment` verdict required by the current request state machine.
- Template create/update uses the registered provider extension before saving.
  OCI fields round-trip through `provider_config`; explicit saved fields take
  precedence over provider defaults when the catalog is reloaded.
- Dry-run operations never invoke the OCI CLI. Unit tests mock cloud responses;
  they do not establish that IAM, quotas, images, or network configuration work
  in a particular tenancy.
- API-key configuration is forwarded via documented child-process
  [OCI CLI environment variables](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/clienvironmentvariables.htm).
  NSGs are forwarded using the documented
  [instance launch options](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/compute/instance/launch.html).
- Pricing figures are static estimates inherited from the original implementation;
  use template pricing overrides for your applicable rates.

## Validation checklist

- run OCI unit tests and provider registration tests
- verify request status transitions complete successfully
- confirm routing fields are OCI:
  - `provider_type=oci`
  - `provider_api=OCICompute`

### Live one-machine canary

Use an isolated default-scheduler config and generated template catalog. Fill in
the real image, subnet, compartment, shape, and availability domain first. Run this
from the repository root, with the built ORB CLI and OCI CLI available on PATH:

```bash
python dev-tools/oci/run_pre_live_gate.py --config /path/to/config.json --template-file /path/to/oci_templates.json --provider oci-default --counts 1 --report-file work/oci-canary-report.json
```

Replace the provider name with the name from your config. The script updates the
selected template with a unique `orb_canary_run` tag, requests one machine, checks
its routing and private IP, verifies OCI reports it running, then returns it and
waits for OCI to confirm termination. It needs permission to list instances in the
test compartment for tag-scoped recovery after partial launches or lost responses.
Running status resolves the primary VNIC's addresses and, when configured, its
private DNS name using the subnet's real DNS domain.

Failures and interrupts trigger cleanup of this run's tagged instances and write a
`hold` report. Direct OCI termination is attempted if ORB return fails; such a
fallback keeps the gate failed. Cleanup failures are recorded for manual recovery.
The default count is one; mock IDs and skipped cleanup cannot pass this gate.
This check does not establish bootstrap completion, workload execution, or actual
Symphony worker registration; verify those separately before production use.

## Troubleshooting

- `...config/config.json not found` is informational when `--config` is
  passed explicitly.
- `ocid1.instance...mock...` should only appear in explicit test/dry-run mode.
  In live mode, OCI launch failures are returned as provider errors.
- auth, region, subnet/AD, or policy mismatches can surface as
  `NotAuthorizedOrNotFound` during OCI CLI verification.
