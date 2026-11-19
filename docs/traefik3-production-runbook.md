# Traefik 3 production operations

This guide describes authorized operation and recovery of the eBL reverse proxy. **The running VM/Swarmpit-managed configuration is the operational authority; this public GitHub repository is a documentary reference, not the source used for deployment.** Use it with the [production inventory](production-inventory-2026-11-19.md), [day-to-day operations](day-to-day-operations.md), and [README](../README.md). The reference [Traefik YAML](../traefik3-production.yml) is **not** a replacement for the actual private production definition.

## Service topology

| Service | Role | Expected state |
| --- | --- | --- |
| `traefik3parity_proxy` | Production Traefik 3.7.18 ingress | One replica; host-mode TCP 80/443 |
| `traefik-consul_traefik` | Traefik 1.7 emergency fallback | Zero replicas; retain until rollback window closes |
| `traefik3_proxy` | Separate staging service | No published public ports; review dependencies before retirement |
| `swarmprom_prometheus` | Metrics collection and alert evaluation | One replica; active Traefik 3 scrape target |

Ingress is constrained to `badwcai-ebl01` and attached to `traefik-public` and `traefik3-test`. Fixed host-mode port publishing permits only one ingress task per node on ports 80 and 443. Do not scale the legacy service up while production Traefik 3 holds those ports.

The Consul leader is a separate service. Its lifecycle must not be conflated with the stopped Traefik 1.7 rollback proxy.

## Routing and TLS

Traefik's static configuration defines `web` (:80), `websecure` (:443), a metrics listener (:9100), and health listener (:8090). Dynamic routing is loaded through the file provider. The production Swarm deployment references these immutable external config objects:

| Config resource | Container destination |
| --- | --- |
| `traefik3stage4-static-20261113` | `/etc/traefik/traefik.yml` |
| `traefik3acme-dynamic-20261113T205821Z` | `/etc/traefik/cutover-dynamic.json` |

The public certificate groups are `www.ebl.badw.de` with `ebl.badw.de`, and `www.ebl.lmu.de` with `www.ebl.uni-muenchen.de`. The `letsencrypt` resolver issues and renews ACME-managed certificates; certificate trust and hostname coverage should be verified independently from outside the cluster.

The ACME account and certificates are stored in `acme.json` on a persistent host bind mount at `/var/lib/traefik`. On the storage host, restrict the directory to mode `0700` and the file to `0600`. The file contains account material and private keys: do not print, commit, or distribute it. Maintain an approved encrypted off-host backup and test its restoration procedure. If the ingress task is moved to another node, the ACME storage must be migrated first.

## Routine verification

Read-only checks on the Swarm manager:

~~~sh
docker service ls --filter name=traefik
docker service ps traefik3parity_proxy --no-trunc
docker service inspect traefik3parity_proxy --format '{{json .Spec.EndpointSpec.Ports}}'
docker service inspect traefik3parity_proxy --format '{{.Spec.Mode.Replicated.Replicas}}'
~~~

Verify all four public domains from an independent client with standard TLS trust checks. A successful application status without certificate verification is insufficient. Check a known working API request as well as the homepage, and verify authenticated administration through Swarmpit and Grafana after changes affecting their routes. LAD access should be tested from its originating environment when allowlists or API routing change.

## Monitoring and certificate renewal

Prometheus scrapes production Traefik through `traefik3parity_proxy:9100`. During the fallback retention period, the old `traefik:8080` target can legitimately be down while Traefik 1.7 has zero replicas; this does not mean the production ingress is unhealthy.

Traefik exports `traefik_tls_certs_not_after` for its ACME-managed certificates. The [certificate alert definitions](../prometheus/traefik3-certificate-alerts.yml) cover:

- A certificate with fewer than 30 days remaining.
- Fewer than the expected two certificate-expiration metric series.
- The production Traefik 3 Prometheus scrape target being down or missing.

The installed Prometheus task rules use the versioned Swarm config `task_rules_tls3_20261113T213540Z`, mounted at `/etc/prometheus/swarm_task.rules.yml`. It includes the existing monitoring rules as well as the certificate alerts. Its complete source must be reviewed and preserved through the approved configuration-management process; the individual alert file in Git is not a complete replacement for the task rules.

An Alertmanager connection is necessary but does not, by itself, prove that notifications are delivered. Test notification routing with an authorized synthetic alert. Monitor certificate-expiration metrics and ACME errors over time; static legacy certificate secrets do not renew automatically.

## Deployment and configuration management

**Production changes are made on the VMs and through Swarmpit under an approved operator process.** The reference [Traefik 3 YAML](../traefik3-production.yml) documents a previously observed topology; it is **not** the deployment source and must not be used for a one-command disaster-recovery rollout. For a separately authorized incident response or change, confirm the following against the private live configuration:

1. Confirm that every referenced external Swarm config, network, and secret exists on the target cluster, and that approved copies of configuration sources are available to authorized operators.
2. Compare the rendered stack specification with the current Swarm service, including command/arguments, labels, networks/aliases, mounted config and secret paths, volumes, resource limits, restart and update/rollback policies, logging, and published ports.
3. Ensure the ACME data is securely backed up and available on the designated ingress host.
4. Record the intended change and rollback procedure, and obtain authorization for any change affecting public ingress.
5. Verify independent public HTTPS, API routes, admin access and the **new** Prometheus target after deployment.

Swarm config objects are immutable; create new versioned objects rather than modifying an existing one in place. Source files may contain internal service addresses or access-control ranges and require private review before publication. Never commit Docker secret contents, raw service snapshots, private keys or ACME storage.

For the monitoring stack, `swarmprom.yml` requires protected deployment-time values for `EBL_ALERTMANAGER_SLACK_URL`, `EBL_GRAFANA_ADMIN_PASSWORD`, and `EBL_MONGODB_EXPORTER_URI`. The values must come from an approved credential store. Review the entire live monitoring specification before redeploying that stack: the repository file must not overwrite working runtime settings through an incomplete configuration.

## Incident recovery

### Certificate or route failure

First inspect production Traefik logs, recent config changes, mounted dynamic config, TLS certificate state, upstream service health and Prometheus metrics. When the issue is limited to dynamic TLS or routing configuration, prefer a controlled rollback to a previously verified versioned dynamic config rather than replacing the entire public ingress. Preserve and verify the old config objects before making any change.

### Full ingress rollback

**Incident procedure only, under authorized operator supervision.** Traefik 3 and Traefik 1.7 cannot simultaneously bind host-mode ports 80/443 on the ingress node.

1. Stop the Traefik 3 service: `docker service update --detach=true --replicas 0 traefik3parity_proxy`.
2. Confirm the new proxy's tasks have fully stopped and ports 80 and 443 have been released; do not proceed merely because desired replicas show zero.
3. Restore the retained proxy: `docker service update --detach=true --replicas 1 traefik-consul_traefik`.
4. Verify trusted HTTPS, frontend and API routing, protected services, and monitoring. Investigate any failure before attempting another cutover.

Do not delete rollback images, Docker secrets, or legacy config resources until an agreed retirement date and a tested alternative recovery path exist.

## Operational handover

Production cutover, external HTTPS, ACME persistence, and Traefik 3 Prometheus/alert-rule loading were verified during the November 2026 migration. LAD subsequently confirmed normal API connectivity. These results establish past acceptance, not guaranteed future health.

**Do not declare this repository a full recovery source.** Store authoritative VM/Swarmpit configuration and sensitive values in approved restricted systems, verify operator-controlled recovery, and independently exercise alert notification delivery and secure off-host ACME restoration. The 19 November 2026 read-only audit confirmed production/staging/legacy task states and mounted config *names*, not private dynamic route bodies or notification delivery.
