# OCI instance-principal authentication

The maintained operator instructions are in the
[OCI deployment and authentication guide](../../docs/root/deployment/oci-integration.md#broker-instance-principal-setup).
It includes the Python 3.12 broker setup, exact-instance dynamic-group matching,
compartment-scoped IAM policy, authentication precedence, and the live validation record.

For template fields and lifecycle semantics, see
[OCI Compute Instances](../../docs/root/providers/oci/compute.md).

The live acceptance tool remains [`run_pre_live_gate.py`](run_pre_live_gate.py).
It requires real instance IDs and verified cleanup; mock IDs and skipped
termination cannot pass. Run it from the broker to test instance-principal
credentials, or from a workstation for a profile/session-based canary, following
the deployment guide's command examples.
