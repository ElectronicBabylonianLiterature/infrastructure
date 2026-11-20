# Troubleshooting notes and escalation

> **Operations reference; last reviewed 20 November 2026.** Use the [day-to-day operations guide](day-to-day-operations.md) for current inspection and the canonical eBL Swarmpit deployment procedure. Escalate production changes through authorized maintainers. The notes below were moved from the historical README to preserve context; they are not stand-alone approval to mutate production.
>
> **Source:** former README Section 5, consolidated into this document. See [historical provisioning](historical-provisioning.md) for the former setup section.

## Historical troubleshooting notes

Start with the [day-to-day operations guide](day-to-day-operations.md) and read-only checks. Changes to services, firewall or credentials require an approved operational procedure.
### 5.1. Consul fails to elect a leader

The Consul leader service was 1/1 on VM1 at the audit, separately from the stopped Traefik 1.7 fallback. Check task state and bounded logs privately, then escalate to the owner. Do not treat scaling Consul to zero as a routine repair.

### 5.2. Redeployment in Swarmpit

**Current verified procedure is maintained only in [day-to-day operations](day-to-day-operations.md#deploying-ebl-through-swarmpit).** For the eBL stack, always edit from **Last Deployed**, never **Current Engine**. Do not attempt to recover by deploying the engine-derived representation.

### 5.3. Forgotten Grafana password
Grafana account recovery requires an approved privileged maintenance process. Do not put new passwords into public commands, PRs or ticket logs. Contact the responsible credential owner.

### 5.4. MongoDB exporter errors

A historical Percona exporter issue was tracked under PMM-4375. Similar error messages today should not automatically be attributed to that issue. The deployed exporter is `percona/mongodb_exporter:0.37.0`. Before changing its image, collectors or credentials, inspect its logs, the replica-set connection/TLS state, and the Prometheus `mongodb-exporter:9216` target.

### 5.5. The cluster becomes unresponsive

**Diagnose before restarting Docker.** A daemon restart on a Swarm manager or MongoDB replica-set member can interrupt services and affect quorum. Restarting Docker on all VMs is not a safe blanket recovery step.

With manager SSH access, start with read-only checks:

~~~sh
docker node ls
docker service ls
docker service ps traefik3parity_proxy
docker service ps ebl_api
docker service ps ebl-mongodb_mongo1
~~~

Inspect the affected task logs, host resource usage, disk capacity, network connectivity and MongoDB replica-set state. Preserve diagnostic evidence and coordinate a targeted recovery plan before restarting any production process.

If SSH or console access is unavailable, or Swarm quorum is lost, contact the responsible LRZ/ITG administrators with the affected hosts, errors and last known healthy state.

### 5.6. Low diskspace
Check `df -h /` and relevant volumes/images read-only. On 19 November, root utilization was VM1 44%, VM2 32%, VM3 62%. Never prune images, delete volumes or change retention without service-owner approval; inactive services may still have important data. 

### 5.7. Expired or invalid HTTPS certificate

Production certificates are issued and renewed by Traefik 3's Let's Encrypt ACME resolver, using persistent storage on the ingress node. The Prometheus certificate-expiration alert rules provide advance warning; an Alertmanager connection alone does not guarantee notification delivery.

When investigating a certificate problem:

1. Verify certificate trust and hostname coverage from an independent external client.
2. Check the `traefik3parity_proxy` service state, Traefik logs, and the Prometheus certificate-expiration metrics/alerts.
3. Confirm that the ACME storage directory is still mounted and writable by Traefik, and that HTTP port 80 remains reachable for HTTP-01 validation.
4. Follow the certificate recovery and rollback guidance in the [Traefik 3 operations guide](traefik3-production-runbook.md).

**Do not restart the legacy Traefik 1.7 service as a certificate-renewal procedure.** That service is reserved for a controlled full-ingress rollback after the new proxy has relinquished ports 80/443.
