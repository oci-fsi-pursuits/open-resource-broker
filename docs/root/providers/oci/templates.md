# OCI compute templates

The catalog contains 25 examples covering 23 shapes. Both
`config/oci_templates.json` and the packaged
`src/orb/providers/oci/config/oci_templates.json` contain the same definitions.
`orb templates generate` uses the packaged catalog.

For the full handler contract and acquire/status/return workflow, see
[OCI Compute Instances](compute.md).

## Shape coverage

| Processor / family | VM shapes | Bare metal shapes |
| --- | --- | --- |
| AMD E5 Standard | `VM.Standard.E5.Flex` | `BM.Standard.E5.192` |
| AMD E6 Standard | `VM.Standard.E6.Flex`, `VM.Standard.E6.Ax.Flex` | `BM.Standard.E6.256`, `BM.Standard.E6.Ax.192` |
| Intel Standard | `VM.Standard3.Flex`, `VM.Standard4.Ax.Flex` | `BM.Standard3.64`, `BM.Standard4.Ax.120` |
| Intel Optimized | `VM.Optimized3.Flex` | `BM.Optimized3.36` (existing RDMA example) |
| Ampere Standard | `VM.Standard.A1.Flex`, `VM.Standard.A2.Flex`, `VM.Standard.A4.Flex`, `VM.Standard.A4.Ax.Flex` | `BM.Standard.A1.160`, `BM.Standard.A4.48`, `BM.Standard.A4.Ax.48` |
| AMD E5 DenseIO | `VM.DenseIO.E5.Flex` | `BM.DenseIO.E5.128` |
| AMD E6 DenseIO | `VM.DenseIO.E6.Ax.Flex` | `BM.DenseIO.E6.Ax.192` |

These are examples of supported template definitions, not a promise of regional
capacity. Check your region, availability domain, image compatibility, limits,
and access using OCI's `ListShapes` API before requesting workers. The exact E6
DenseIO shape includes `.Ax`; there is no `VM.DenseIO.E6.Flex` example. Current
Intel and Ampere families have Standard examples; current DenseIO examples are
AMD. See [Oracle's shape reference](https://docs.oracle.com/en-us/iaas/Content/Compute/References/computeshapes.htm).

Existing IDs remain valid: `oci-vm-flex-ondemand-small`,
`oci-vm-flex-preemptible-small`, and
`oci-vm-flex-preemptible-fallback-medium` use E6 Standard;
`oci-bm-standard-ondemand` uses E5 Standard. New IDs follow
`oci-<shape-in-lowercase-with-hyphens-without-flex>-ondemand`, for example
`oci-vm-standard-e5-ondemand` and `oci-vm-denseio-e6-ax-ondemand`.

## Flex sizing

Each VM example explicitly declares its CPU and memory. Standard and Optimized
examples start with 1 OCPU / 8 GB; DenseIO examples start with 8 OCPUs / 96 GB.
Clone a template, give it a unique `template_id`, and edit `shape_config`:

```json
{
  "shape_config": {
    "ocpus": 4,
    "memoryInGBs": 32
  }
}
```

This is a sizing fragment for Standard/Optimized Flex, not a complete template.
ORB passes these values to OCI's launch `shapeConfig`. OCI enforces the shape's
CPU/memory limits and permitted ratios; values must be finite and positive.
`machine_types: {"VM.Standard.E5.Flex": 1}` selects the shape; its weight `1`
does not set the CPU count. Use one shape per OCI template, so the image,
architecture, sizing, and scheduling identity are unambiguous. The OCI handler
selects the first entry; the map is not a multi-shape fallback list.

DenseIO Flex uses fixed CPU/memory steps. For both shipped E5 and E6 Ax examples,
the allowed pairs are 8/96, 16/192, 24/288, 32/384, 40/480, and 48/576
(OCPUs/GB). ORB rejects other pairs before provisioning. Local NVMe capacity
follows the selected shape configuration; `boot_volume_gbs` sets the separate
boot disk and does not resize or mount NVMe. Treat local NVMe as temporary worker
storage and configure mounts in your own bootstrap. See
[Oracle's NVMe guidance](https://docs.oracle.com/en-us/iaas/Content/Compute/References/nvmedeviceinformation.htm).

Bare metal examples are fixed shapes. Do not add `shape_config`, `ocpus`, or
`memory_gbs`; ORB rejects Flex overrides on bare metal.

## Images and deployment settings

Keep compartment, subnet, NSGs, SSH public keys, and bootstrap settings in
`provider_defaults.oci.template_defaults`, as described in the
[integration guide](../../deployment/oci-integration.md).

Use a compatible x86_64 image for AMD/Intel. Every Ampere example explicitly has
`image_id: "ocid1.image.oc1..<replace-arm64-image-ocid>"`; replace this on each
chosen template with a compatible ARM64 image before launching. The placeholder
intentionally overrides a shared x86 image default. Your worker software and
bootstrap must also support ARM64. OCPU-to-vCPU conversion differs between A1
and later Ampere families; sizing is always expressed in OCI OCPUs, not an
assumed universal thread count. See
[Arm-based Compute](https://docs.oracle.com/en-us/iaas/Content/Compute/References/arm.htm).

The RDMA example keeps its explicit HPC image, availability domain, cluster ID,
and agent settings. Follow [Compute Clusters and RDMA](compute-clusters.md).
Other new examples launch independent on-demand workers using the same existing
OCI handler. To use preemptible capacity on a compatible VM shape, clone an
existing preemptible example and replace its shape, sizing, and image; fallback
changes capacity type for that same shape, not processor architecture.

Pricing remains an estimate. Shapes without configured reference rates report
unknown compute cost; supply `pricing` overrides for your applicable rates.
Catalog coverage and offline tests do not establish a live launch on every shape.

## Validate a selected template

After filling deployment defaults and the selected template's image/settings:

```bash
orb --config config/oci_config.json templates generate
orb --config config/oci_config.json templates list
orb --config config/oci_config.json templates validate oci-vm-standard-e5-ondemand
orb --config config/oci_config.json machines request oci-vm-standard-e5-ondemand 1 --dry-run
```

Generation writes examples; edit your generated catalog afterward. Do not
regenerate over deployment edits. For a real canary, use the acquire/status/return
procedure in the integration guide and confirm cleanup independently in OCI.
