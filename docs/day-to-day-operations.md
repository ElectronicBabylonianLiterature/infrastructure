# eBL day-to-day operations and handover

> **Audience:** Authorized eBL infrastructure maintainers.
> **Operating model:** Production Docker Swarm is configured and maintained on the three LRZ VMs and in Swarmpit. The GitHub `infrastructure` repository is a **read-only documentary reference**, not a deploy target, config registry, or one-command disaster-recovery source. Verify actual running state before an operational decision.
> **Evidence baseline:** [19 November 2026 VM inventory](production-inventory-2026-11-19.md). Times and task locations are snapshots, not guarantees.

## Access and responsibility

1. Obtain your **individual authorized VM account** and BAdW full-tunnel VPN access through the institute's approved administrators. The [README SSH section](../README.md#accessing-the-production-vms-over-ssh) contains hostnames/IPs and Windows/macOS/Linux examples. Aliases such as `caic1` work only after being configured on the local workstation.
2. VM1 (`badwcai-ebl01`) is the **single Swarm manager** and public Traefik 3 ingress node. VM2 and VM3 are workers. Use VM1 for Swarm-wide commands; a worker cannot provide the manager's service inventory.
3. Swarmpit is the day-to-day UI for seeing Swarm stacks, services, replicas, logs, and authorized redeployments: [Swarmpit](https://www.ebl.badw.de/cluster/swarmpit/). Access requires the appropriate account/controls; do not infer that every publicly routed admin page is safe to use without checking authentication.
4. Credentials, private Swarm configs, network access lists, and ACME private material remain in the institution's approved restricted stores/on the hosts. Do not copy them into GitHub, PR comments, incident tickets, or chat.

## Routine, read-only inspection

From the **manager VM**, inspect health without changing services:

~~~sh
docker node ls
docker stack ls
docker stack services ebl
docker service ls
docker service ps ebl_api
docker service ps ebl_frontend
docker service ps traefik3parity_proxy
docker service ps ebl-mongodb_mongo1
docker service ps ebl-mongodb_mongo2
docker service ps ebl-mongodb_mongo3
~~~

On **each individual VM**, inspect host-local state:

~~~sh
docker version --format '{{.Server.Version}}'
docker info --format '{{.Swarm.LocalNodeState}}'
df -h /
sudo systemctl is-active docker
~~~

These commands display limited metadata, but review their outputs before sharing them. A `Running` task and `1/1` replica count do not establish API readiness, database primary state or reachable HTTPS.

For troubleshooting, view bounded task logs **privately** through Swarmpit or approved CLI procedures. Logs may contain sensitive material, including request headers, IDs or access information; do not paste unredacted logs into the public repository.

## Deploying eBL through Swarmpit

> **Critical production safeguard — use `Last Deployed`, NEVER `Current Engine` for stack configuration edits.** The `Current Engine` representation has caused broken/mis-serialized configurations when redeployed, particularly with commands and escaped variables. For eBL, edit only the **`Last Deployed`** stack definition. Do not use the `Current Engine` representation as a starting point, and do not deploy it.

These are the current operator-reported steps for the **eBL application stack** in Swarmpit. They are two different workflows; use **Redeploy** for an application update and **Edit** only when changing the actual stack configuration. Both are production-changing actions and require authorization and post-deployment verification.

### Redeploy application changes (without editing the stack configuration)

1. Confirm the relevant frontend or API change has been merged, its CI build/publish succeeded, and the intended image is available in the private registry. Merging alone does not update running containers.
2. Open [Swarmpit](https://www.ebl.badw.de/cluster/swarmpit/) with the appropriate administrative permissions.
3. Navigate to **Stacks → eBL** (the running `ebl` application stack).
4. Find **Edit** and click the **dropdown arrow next to Edit** — **not** the Edit action itself.
5. Select **Redeploy** from the dropdown to redeploy the existing eBL stack definition. Complete the UI confirmation if prompted. **Do not switch to Current Engine or edit/recreate a stack definition for a routine image redeploy.**
6. Monitor service tasks and replicas during the rollout; verify that the intended image is actually running, the frontend and API respond correctly, HTTPS works, and no unexpected task failures occur. Escalate if the image has not changed or service health deteriorates; do not repeatedly redeploy blindly.

### Edit and deploy eBL stack configuration

1. Obtain approval for the configuration change and retain a restricted, recoverable copy of the last known-good deployment definition. Review impacts on credentials, volumes, networks, health, replicas and routing before editing.
2. Open **Swarmpit → Stacks → eBL → Edit**.
3. In the editor, **select `Last Deployed`**, **NOT `Current Engine`**. Confirm the selected source **before making changes and again before deploying**. If `Last Deployed` is missing or cannot be selected, **stop** and contact the infrastructure maintainer rather than deploying `Current Engine`.
4. Make the intended, minimal configuration changes **in `Last Deployed`**. Preserve existing service definitions, variables, secrets and escape sequences unless the change explicitly calls for modifying them. **Do not paste `ebl.yml` from GitHub**; it is a historical reference, not the running stack configuration.
5. Deploy the edited stack configuration using Swarmpit's deployment action only after reviewing the diff and confirming `Last Deployed` is still the selected source.
6. Monitor task rollout, replica counts, service image/settings and real frontend/API behavior. If the result is unsafe, follow the approved recovery procedure using the last known-good configuration; do not attempt to recover by deploying `Current Engine`.

**Keep these workflows distinct:** **Stacks → eBL → dropdown next to Edit → Redeploy** for routine published application changes; **Stacks → eBL → Edit → Last Deployed → edit → Deploy** for deliberate configuration changes.

The checked-in `swarmpit.yml`, `ebl.yml`, registry and monitoring YAML are historical references and may omit live services or contain Traefik 1.x labels. The steps above are specifically for the **eBL** application stack; do not assume other infrastructure stacks have identical deployment requirements.

## Triage map

| Symptom | Non-destructive first checks | Escalation / caution |
| --- | --- | --- |
| Public site, API or TLS outage | `docker service ps traefik3parity_proxy`; API/frontend service state; independent TLS and a known API request | Ingress runs on VM1 only. Use the [Traefik runbook](traefik3-production-runbook.md); never start the legacy proxy while Traefik 3 owns ports 80/443. |
| API slow / queues / memory pressure | API task placement, bounded application logs, host memory/disk and Grafana | API replicas may cluster on VM2. Do not infer bot causation or use restarts as generic remediation. |
| Database errors | Three MongoDB task statuses, host/network health and TLS expiry | Replica-set primary/lag require separate authorized diagnostics; never reinitialize or redeploy non-TLS bootstrap against production. |
| Missing metrics or notifications | Prometheus targets, exporter task states, loaded rule references, Alertmanager | A running exporter is not necessarily collecting useful metrics; test notification delivery only through approved channels. |
| Registry push/pull failure | Registry and registry-UI task states, known auth/registry endpoint behavior, remaining storage | Avoid printing registry credentials and do not alter stored images/tag retention without authorization. |
| Disk pressure | `df -h /` on all VMs; approved volume/image inventory | Do not run bulk pruning, delete volumes, or assume every local volume is unused. |
| Swarmpit unavailable | `swarmpit_app`, `swarmpit_db`, `swarmpit_influxdb`, and global agent state | Live stack includes InfluxDB, omitted by old reference YAML. Avoid replacing live stack with it. |

## Backups and recovery

LRZ backup coverage has been **confirmed by the eBL operator** as of 19 November 2026. The README retains its recorded schedule and retention period. This inventory did not exercise a restore or establish a safe MongoDB-consistent recovery procedure. Coordinate any recovery with LRZ/institute maintainers and the database owner. In particular, do not casually restore one MongoDB member or all members without assessing replica-set consistency and the chosen recovery method.

## Open verification, not automatic remediation

- **Network filtering:** Swarm ingress publishes MongoDB ports 27017–27019 and registry/UI ports 5000/8000; Docker metrics listen on 9323 across all interfaces. Published/listening is **not proof of external exposure**. Host firewall inspection lacked permission on each audited VM; verify effective host and LRZ filtering with authorized administrators. Never publish private ACLs.
- **Traefik rules:** Private dynamic config is authoritative for Traefik 3; check real routes, API/registry/admin authentication, and whether the sinkhole matches anything. Do not infer effectiveness from a running sinkhole container or old Traefik labels.
- **MongoDB:** Verify primary/replication with a read-only, credentialed diagnostic under database-owner supervision.
- **Monitoring:** Verify actual Prometheus scrape success, certificates/rules coverage and authorized synthetic Alertmanager delivery. Current deployment references `task_rules_tls3_20261113T213540Z`, whose private complete source is not in Git.
- **Ownership/retirement:** Legacy API services at 0/0, staging Traefik 3 at 1/1, legacy Traefik 1.7 at 0/0, and Inception volumes require an explicit owner decision before removal. There is no cleanup authorization from this documentation review.
- **Management availability:** VM1 is the sole manager and ingress node. Consider recovery procedures separately; this PR does not change the number of managers or ingress placement.

## Handover checklist

Before another administrator takes responsibility, have them independently confirm **account/VPN access**, VM1 manager access, Swarmpit and Grafana permissions, where private credentials/config sources are held, who approves rollouts, how to reach LRZ, where backup/restore procedures live, and who owns databases, DNS/TLS and monitoring alerts. Record contacts and sensitive access paths in an approved **private** institutional channel rather than this public repository.
