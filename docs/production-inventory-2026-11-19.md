# Production infrastructure inventory — 19 November 2026

> **Evidence:** Read-only snapshots from badwcai-ebl01 at 13:03 UTC, badwcai-ebl02 at 13:07 UTC, and badwcai-ebl03 at 13:08 UTC.
> **Authority:** Live VM/Docker Swarm specifications and Swarmpit-managed configuration are operationally authoritative. This is a documentation snapshot, **not** an importable manifest or proof of continuous service health.
> **Privacy:** Inventory summaries only; do not commit raw service inspections, dynamic Traefik configuration, credentials, audit JSON, private keys, or access-control rules.

## Hosts and Swarm roles

| VM | Role | OS / kernel at audit | Docker Engine | XFS root space used/free at audit |
| --- | --- | --- | --- | --- |
| `badwcai-ebl01` (VM1) | **Only Swarm manager**, public ingress | Debian 12 / 6.1.0-56-amd64 | 26.1.4 | 44% used / 577 GiB free |
| `badwcai-ebl02` (VM2) | Worker | Debian 12 / 6.1.0-56-amd64 | 26.1.4 | 32% used / 700 GiB free |
| `badwcai-ebl03` (VM3) | Worker | Debian 12 / 6.1.0-56-amd64 | 26.1.3 | 62% used / 390 GiB free |

All three nodes reported `Ready` and `Active`. VM1 being the only manager means management operations have a single-node dependency. Disk and version data are time-bound; use the live system for current state.

## Live service topology

| Service or stack | Snapshot state | Running nodes / notes |
| --- | --- | --- |
| `traefik3parity_proxy` | 1/1, Traefik 3.7.18 | VM1; host-mode TCP 80/443; production ingress |
| `traefik3_proxy` | 1/1, Traefik 3.7.18 | VM1; separate staging service, no public published ports |
| `traefik-consul_traefik` | 0/0 | Retained Traefik 1.7 fallback; **not** another active ingress |
| `traefik-consul_consul-leader` | 1/1 | VM1; separate from stopped legacy proxy |
| `ebl_api` | 3/3 | VM1: one; VM2: two; VM3: zero |
| `ebl_frontend` | 3/3 | VM1: one; VM2: two; VM3: zero |
| `ebl_ai-api` | 1/1 | VM2 |
| `ebl_redis` | 1/1 | VM1 |
| `ebl_sinkhole` | 1/1 | VM2; deployment is real, effective Traefik 3 matching **not verified** |
| `ebl-api_api`, `ebl_api_api` | 0/0 each | Additional, stopped API services; ownership and retirement **not verified** |
| `ebl-mongodb_mongo1/2/3` | 1/1 each | VM1 / VM2 / VM3; one task per node; replica-set health **not queried** |
| `mongosync_mongosync` | 1/1 | VM3 |
| `registry_registry1` | 1/1 | VM1; persistent `registry_registry1` volume |
| `registry_ui` | 1/1 | VM2; persistent `registry_registry-ui` volume |
| `swarmpit_app` | 1/1 | VM1 |
| `swarmpit_agent` | 3/3 | One task per VM |
| `swarmpit_db` | 1/1 | VM2, CouchDB; volume `swarmpit_db-data` |
| `swarmpit_influxdb` | 1/1 | VM2, InfluxDB; volume `swarmpit_influx-data`; **missing from historical reference YAML** |
| `swarmprom_prometheus`, `swarmprom_grafana`, `swarmprom_alertmanager` | 1/1 each | VM1 |
| `swarmprom_mongodb-exporter`, `swarmprom_redis-exporter`, `swarmprom_karma` | 1/1 each | VM2 |
| `swarmprom_node-exporter`, `swarmprom_cadvisor`, `swarmprom_dockerd-exporter` | 3/3 each | One task per VM |
| `swarmprom_unsee` | 1/1 | VM1 |

The application and monitoring replicas may be **rescheduled**; this table records observed placement, not placement guarantees. No Swarm-level container health check was present for the active API, frontend, or AI API. A running task is not proof of application readiness.

No active Inception application service was observed in the cluster-wide inventory. Named Inception application/database volumes were present on VM3. **Do not infer the tool is operational, or that these volumes are safe to remove.** Inception ownership and storage retention are unverified.

## Networking and TLS

- Production Traefik 3 publishes TCP 80/443 in **host** mode on VM1.
- MongoDB services publish TCP 27017, 27018, 27019 through Swarm **ingress** mode; the registry publishes TCP 5000, and its UI TCP 8000, also through ingress.
- Docker metrics listen on TCP 9323 bound to **all interfaces** on each VM.
- These facts describe service publication and local listeners, **not** Internet reachability or an authentication bypass. All three optional UFW checks failed or lacked permission. LRZ upstream filtering is not established by this inventory.
- Four public hostnames (the BAdW and LMU names listed in the [README](../README.md)) passed independent-chain and hostname TLS checks at the audit time. Two certificate groups expire **11 February 2027 UTC**. Renewal behavior and notifications remain separate verification tasks.

## Reference files and operational drift

- [`ebl.yml`](../reference/application/ebl.yml) is a historical/reference example and lacks the live sinkhole. Its Traefik v1 routing labels do not express the effective Traefik 3 dynamic-file routes. Do not use it as an exact production export.
- [`swarmpit.yml`](../reference/monitoring/swarmpit.yml) predates the live InfluxDB service and differs from live CouchDB placement/resource settings. It must not be deployed as a replacement for the actual Swarmpit-managed stack.
- [`swarmprom.yml`](../reference/monitoring/swarmprom.yml) is a reference, not a secret-complete live deployment source. The active Prometheus service mounts `node_rules` and `task_rules_tls3_20261113T213540Z`; the audit did **not** read the config bodies or prove alert delivery.
- [Traefik 3 runbook](traefik3-production-runbook.md) correctly identifies active production, staging and stopped fallback services. The production service references `traefik3stage4-static-20261113` and `traefik3acme-dynamic-20261113T205821Z`. The full private dynamic routing content was intentionally not collected.
- This repository is **documentation only**: configuration changes, rollouts and rollbacks are coordinated on the VMs/in Swarmpit under maintainer authorization.

## Verification ledger

| Subject | Status on 19 November 2026 | Safely scoped next step |
| --- | --- | --- |
| LRZ VM backup coverage | **Confirmed by eBL operator.** The six daily snapshot times and 14-day retention are retained from the existing README; the read-only VM audit cannot inspect LRZ hypervisor policies. | No repeat backup verification requested. Any actual restore test / MongoDB-consistent recovery plan is a separate authorization. |
| Firewall and ingress exposure | **Unverified**: listener and published-port metadata only; UFW inspection unavailable on all three VMs. | Authorized, read-only host and LRZ perimeter review; sanitize private rule details. |
| MongoDB replica-set health | **Unverified**: three tasks running is not a primary election, lag, or health check. | Authorized, bounded `rs.status()` / `db.hello()` diagnostics; do not change replica membership. |
| Effective Traefik 3 routing / sinkhole | **Unverified**: secret-bearing dynamic configuration not extracted. | Restricted route inventory and benign, authorized test cases for API, admin, registry and sinkhole behavior. |
| Monitoring scrape/alert delivery | **Unverified**: target and ruleset references exist; notification delivery not exercised. | Inspect target success, actual MongoDB metrics, and one approved synthetic notification. |
| Registry/admin UI authentication and retention | **Unverified**: services/volumes present but login, tag purge and recovery were not tested. | Authorized access and non-destructive retention review. |
| Inception volumes and inactive API services | **Unverified** ownership/retirement. | Ask maintainers before cleanup; no removal implied. |
| Archived Eraser diagrams and screenshots | Historical presentation may not reflect this snapshot. | Use the live topology summary and README Mermaid diagram for current handover. |

## Read-only follow-up and handover

See [day-to-day operations](day-to-day-operations.md) for safe inventory commands, Swarmpit workflows, evidence handling, and escalation. Preserve date-qualified evidence; do not copy production secrets, raw environment variables, firewall ACLs, user IPs or raw logs into this **public** repository.
