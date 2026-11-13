# eBL Traefik 3 production and rollback runbook (2026-11-13)

## Current production state

Traefik 3.7.18 (traefik3parity_proxy) completed a controlled production cutover on November 13, 2026. Trusted HTTPS on all four hostnames, IPv6, HTTP redirects, 12 representative routes, and the distinct production Prometheus target passed. A subsequent ACME-only dynamic configuration successfully issued, persisted and served certificates for all four hostnames.

| Service | Desired replicas | Public ports |
| --- | --- | --- |
| traefik3parity_proxy | 1 | 80/443 host-mode on badwcai-ebl01 |
| traefik-consul_traefik | 0 | 80/443 still configured, emergency rollback only |
| traefik3_proxy | 1 at last inspection | None, older staging service |
| swarmprom_prometheus | 1 | Scrapes Traefik 3 on 9100 and legacy Traefik 1.7 on 8080 |

Do not scale the original Traefik 1.7 service up while Traefik 3 owns 80/443. Increasing Traefik 3 replicas on the single pinned ingress node would conflict with host-mode ports. Do not delete the rollback service or private rollback snapshots.

## Configuration details

Existing external Docker Swarm configs:
- traefik3stage4-static-20261113 mounted at /etc/traefik/traefik.yml
- traefik3acme-dynamic-20261113T205821Z mounted at /etc/traefik/cutover-dynamic.json

Entrypoints: HTTP web :80, HTTPS websecure :443, metrics :9100, health :8090. The two ACME certificate groups are www.ebl.badw.de + ebl.badw.de, and www.ebl.lmu.de + www.ebl.uni-muenchen.de. The current dynamic config uses the letsencrypt resolver; its prior static-certificate predecessor was traefik3stage4-dynamic-20261113.

ACME storage: /home/farhanabdulla/ebl-traefik3-acme/acme.json on badwcai-ebl01, bind-mounted at /var/lib/traefik/acme.json. Parent directory mode 0700 and file mode 0600. Contains ACME account credentials and private certificate keys: NEVER print, email, or commit it. Back it up using approved secret-storage procedures. Pin the Swarm task to the host holding its persistent storage.

**Deployment parity note (2026-11-13):** The live Traefik 3 service limits CPU to 0.5 and memory to 256 MiB, reserves 64 MiB memory, restarts on failure with a 5-second delay, and uses stop-first updates (parallelism 1, pause on failure, 15-second monitor, failure ratio 0). The draft manifest now carries these values. Stack-generated service and container labels are intentionally not hardcoded. The default Docker logging driver is inherited and not overridden. Compare all remaining live fields before the first stack redeploy.

**The new traefik3-production.yml is a review draft reflecting observed runtime configuration, not yet a verified bit-for-bit representation of the active service.** Compare the live task spec (command, ports, labels, secrets, config paths, mounts, networks, restart policy and logging) before any first redeploy. External Swarm config objects are cluster-local; their non-secret source contents still need controlled export, review and versioning before disaster-recovery documentation is complete. NEVER commit raw service snapshots.

## Verify read-only

From badwcai-ebl01:
- docker service ps traefik3parity_proxy --no-trunc
- docker service inspect traefik3parity_proxy
- python3 ~/ebl_traefik_acme_takeover_v2.py --verify

From outside the server, use trusted HTTPS to each of the four hostnames. Do not use insecure TLS flags to claim certificate trust. A known working eBL API request and authenticated administrative sign-in should be validated separately. LAD access must be tested from Luis's real origin in Leipzig (deferred).

ACME renews certificates that it issued itself. Add a monitored certificate-expiry/renewal alert and verify it triggers before deadlines. Legacy static certificate secrets are NOT ACME-renewed; keep them only for the agreed rollback period.

## Monitoring

Swarmprom JOBS temporarily retains both traefik:8080 and traefik3parity_proxy:9100. The checked-in stack now references `task_rules_tls3_20261113T213540Z` to match the live Prometheus rule config. It is expected for the old target to be down with Traefik 1.7 scaled to zero. Require the NEW production scrape target to be up. The checked-in `swarmprom.yml` now **fails closed** unless three private deployment-time environment variables are provided, but do NOT redeploy it until all existing live settings and logging differences are reviewed; the actual credentials are not in Git.

### Secure deployment inputs (no credentials committed)

For a future full monitoring-stack deployment, `swarmprom.yml` now requires three variables: `EBL_ALERTMANAGER_SLACK_URL`, `EBL_GRAFANA_ADMIN_PASSWORD`, and `EBL_MONGODB_EXPORTER_URI`. These are **the existing live values**, not new passwords or new endpoints. Source them only from an institution-approved protected credential store into a restricted deployment environment; never add them to a commit, transcript, or CI log. Do not pass them as shell arguments that may appear in process listings.

**This is a deployment input guard, not a secrets migration.** The current monitoring images consume those values as environment variables or command arguments, which remain readable to suitably privileged Docker administrators. A subsequent secrets-management migration requires verifying exporter and Alertmanager image support and a separate controlled deployment.

Before any `docker stack deploy`, compare the entire rendered monitoring stack against the live services. The evidence report notes that the live monitoring tasks report the default logging driver whereas the historical manifest specifies `json-file`. Private values and other runtime drift were withheld, so that comparison is still incomplete.

## Certificate expiry alerting

Prometheus exports `traefik_tls_certs_not_after{job="traefik3parity_proxy"}` for both ACME-managed certificate groups. The source rules in [`prometheus/traefik3-certificate-alerts.yml`](../prometheus/traefik3-certificate-alerts.yml) define a warning at <30 days remaining, an alert when the two expected expiry series go missing, and a critical alert when the Traefik 3 scrape target is unavailable.

**Installed 2026-11-13:** Live Prometheus now mounts versioned Swarm rules config `task_rules_tls3_20261113T213540Z` at `/etc/prometheus/swarm_task.rules.yml`. The existing rules were preserved, `promtool` accepted the combined file, all three Traefik 3 alert rules were verified in Prometheus, and the new Traefik scrape target remained healthy. The previous task rules config `task_rules_inf04_20261111_v2` and private snapshot remain available for rollback. The GitHub source rule snippet is not a replacement for the entire deployed combined rules file. **Do not deploy the checked-in `swarmprom.yml` without first sourcing the correct private runtime values and checking every current service setting.**

Before claiming alert delivery works, check the Prometheus-to-Alertmanager connection and independently test routing/notification delivery without disturbing real workloads. The expiry warnings can remain inactive until the threshold is reached.

## Full-ingress rollback (authorized incident only)

1. Stop new proxy: docker service update --detach=true --replicas 0 traefik3parity_proxy
2. Confirm no Traefik 3 tasks are running and its host-mode ports have been released.
3. Restore old proxy: docker service update --detach=true --replicas 1 traefik-consul_traefik
4. Test trusted public HTTPS, relevant API routes, and monitoring; do not start both proxies with the same host ports.

For a TLS-only failure, prefer carefully switching the dynamic config back to the preserved static-certificate config instead of a full-ingress rollback. Review active config names first; retain the pre-change service snapshot and original Swarm secrets.

## Recorded server evidence and unresolved parity

The [sanitized November 13 server evidence](traefik3-sanitized-evidence-20261113.md) records exact configuration names and SHA-256 hashes, network and secret attachments, resource and update/rollback policies, and which monitoring services still receive credentials in the environment or command arguments. It contains **no** secret payloads and **no** raw Swarm config bodies. The active Traefik 3 rollback policy monitor is 5 seconds (the update monitor is 15 seconds); the draft manifest has been updated to match. Existing monitoring stack credentials and config body export remain blockers for an authoritative full-stack redeploy.

## Outstanding work

- [x] Production Traefik 3 cutover / TLS, routing, IPv6 acceptance
- [x] ACME issuance and persistent certificate verification for four hostnames
- [x] Distinct production Prometheus scrape target healthy
- [ ] Verify production manifest against ALL current live Swarm fields before any stack deploy
- [ ] Export, sanitize and review static/dynamic config sources for Git
- [x] Install and verify three certificate-expiry/missing-metrics/target-down alert rules (2026-11-13)
- [ ] Verify Alertmanager notification delivery with an authorized synthetic test
- [ ] Independently verify authenticated admin routes and a real API workflow
- [ ] Validate LAD-origin requests with Luis in Leipzig (deferred)
- [ ] Retire older staging service and legacy scrape job only after dependencies are cleared
