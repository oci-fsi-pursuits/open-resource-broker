# OCI Integration Guide

This guide documents OCI provider support in Open Resource Broker and the
recommended operational flow.

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
- `profile`
- `default`

## Template contract (OCI)

Required fields for reliable launches:

- `image_id` from template defaults
- `subnet_ids[0]` from template defaults
- `compartment_id` from template defaults
- shape from the template `machine_types`, `shape`, `instance_type`, or defaults

Recommended:

- `ssh_authorized_keys`
- `user_data` (base64 cloud-init)

## Runtime flow

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
orb --config config/oci_config.json machines request oci-vm-flex-ondemand-small 1 --provider oci-default
orb --config config/oci_config.json requests status <request-id>
orb --config config/oci_config.json machines return <instance-ocid> --provider oci-default
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
  return ORB's flat instance-list format and normalized machine states.
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

## Troubleshooting

- `...config/config.json not found` is informational when `--config` is
  passed explicitly.
- `ocid1.instance...mock...` should only appear in explicit test/dry-run mode.
  In live mode, OCI launch failures are returned as provider errors.
- auth, region, subnet/AD, or policy mismatches can surface as
  `NotAuthorizedOrNotFound` during OCI CLI verification.
