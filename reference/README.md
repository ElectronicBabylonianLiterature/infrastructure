# Historical and documentary configuration references

> **Not a deployment source.** This directory collects Git-tracked **examples and snapshots**, organized by their subject. eBL production configuration lives on the LRZ VMs and is maintained through Swarmpit. The directory **must not** be used to bootstrap, redeploy, or roll back a running stack. Confirm versions, secrets, ports, placement, and config objects against the authorized private VM/Swarmpit state.
>
> **Context:** Reorganized on 20 November 2026 using the [19 November read-only VM inventory](../docs/production-inventory-2026-11-19.md). Moving files does **not** confirm the referenced manifests match the running services. Git history retains their former root locations and provenance.

## Index

| Area | Reference file | Status / use |
| --- | --- | --- |
| Application | [`application/ebl.yml`](application/ebl.yml) | Historical four-service app sample. The live `ebl` stack also contains a sinkhole, and the Traefik 1.x labels shown are **not** active Traefik 3 routing rules. |
| Database | [`database/mongodb-replica_set.yml`](database/mongodb-replica_set.yml) | TLS replica-set topology reference, not a recovery or reinitialization procedure. |
| Networking | [`networking/traefik3-production.yml`](networking/traefik3-production.yml) | Versioned production-topology **documentation**; private dynamic config is authoritative for routing. |
| Registry | [`registry/registry.yml`](registry/registry.yml), [`registry/registry_config.yml`](registry/registry_config.yml), [`registry/docker-registry-ui_config.yml`](registry/docker-registry-ui_config.yml) | Historical setup examples; do not paste live credentials or apply tag retention/purge settings without authorized review. |
| Monitoring | [`monitoring/swarmprom.yml`](monitoring/swarmprom.yml), [`monitoring/swarmpit.yml`](monitoring/swarmpit.yml) | Reference stacks, **not** faithful exports. The live Swarmpit stack has InfluxDB, omitted by its example. |
| Monitoring | [`monitoring/swarm_node.rules.yml`](monitoring/swarm_node.rules.yml), [`monitoring/swarm_task.rules.yml`](monitoring/swarm_task.rules.yml) | Historical Prometheus rule **sources**; rule-group names retain historical Vagrant paths. Do not assume exact match with currently loaded rules. |
| Monitoring | [`monitoring/traefik3-certificate-alerts.yml`](monitoring/traefik3-certificate-alerts.yml) | Standalone Traefik 3 certificate-alert rule **excerpt**, not an independently deployed Prometheus rules file. |
| Host | [`host/daemon.json`](host/daemon.json) | Logging/metrics settings example. Its safe fields matched the November VM inspection; **do not** overwrite a live Docker daemon JSON file. |
| Legacy | [`legacy/traefik-consul.yml`](legacy/traefik-consul.yml), [`legacy/traefik.toml`](legacy/traefik.toml) | Traefik 1.7/Consul rollback-era references. The old proxy is currently stopped, but retention is intentional until fallback retirement is approved. |
| Legacy | [`legacy/mongodb.yml`](legacy/mongodb.yml) | Historical **non-TLS bootstrap**; unsafe to deploy against the populated production database. |
| Legacy | [`legacy/inception-annotation-tool.yml`](legacy/inception-annotation-tool.yml) | No active Inception Swarm service was observed on 19 November; Inception volumes remain on VM3. Ownership/retention needs verification before cleanup. |

## Source of truth and maintenance rules

1. **For users/operators:** follow [day-to-day operations](../docs/day-to-day-operations.md), [VM access](../docs/vm-access.md), and [Traefik operations](../docs/traefik3-production-runbook.md).
2. **For authors:** explain each reference's origin and evidence date. Avoid silently replacing historical values with guessed modern ones. Superseded configuration can remain here for traceability without being suitable for deployment.
3. **For safety:** never add actual secret values, raw Docker service inspect outputs, private network ACLs, passwords, ACME account files or production audit dumps to this public repository.
4. **For integration:** the `prometheus` and `swarmprom` sources are examples and are not a complete export of the external immutable Swarm configs. The installed combined Traefik TLS task-rule config was named `task_rules_tls3_20261113T213540Z` in the November inventory; private bodies and notification delivery were not inspected.
5. **For changes:** the production eBL stack is managed through **Stacks → eBL** in Swarmpit. For configuration edits choose **Last Deployed**, **never Current Engine**. The [canonical step-by-step procedure](../docs/day-to-day-operations.md#deploying-ebl-through-swarmpit) is maintained outside this reference directory.
