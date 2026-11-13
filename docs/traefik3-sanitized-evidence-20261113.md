# Safe eBL Swarm evidence — PR #6

Collected read-only from `badwcai-ebl01` at **2026-11-13 21:56:54 UTC**. This document records a sanitized evidence report, **not** any raw Docker service JSON, certificates, credentials, or configuration file contents. Production services were not modified to collect it. This snapshot can become stale; verify fresh service state before deploying.

## External Swarm config inventory

| Swarm config name | Size (bytes) | SHA-256 |
| --- | ---: | --- |
| `traefik3stage4-static-20261113` | 905 | `3626b400694fa70027b35b5c896e6f72249814ad916b849c7a0e9948111fdba5` |
| `traefik3acme-dynamic-20261113T205821Z` | 13,019 | `7df7c0bb447daadcba39019cb58062f256af95125c8043a0e10c4fa20281eeb7` |
| `task_rules_tls3_20261113T213540Z` | 5,183 | `f268c5e5be3e682c537b72dba7f45e98e2933a1feb4df7511301af52f18cee83` |
| `node_rules` | 1,894 | `6bebbf49ba711cdb5acdabf183152a47fdc1eba21a77a7fc65d5f634508b7583` |

The dynamic config has **12 HTTP routers, 13 middlewares, 11 services, and zero static TLS certificates**. The combined task rules contain **11 alert definitions**, including `EBLTraefik3CertificateExpiringSoon`, `EBLTraefik3CertificateMetricsMissing`, and `EBLTraefik3MetricsUnavailable`.

The private extracted files are on the server under:
`~/ebl-traefik-v3-stage4-prep/pr6-evidence/20261113T215654Z/PRIVATE-DO-NOT-SHARE/`.
They have 0600 permissions and have **not been reviewed for public distribution**. The dynamic config was flagged for potential sensitive vocabulary. The flag is not proof of a leaked secret, but **blocks automatic publication**. Review its contents privately, then export/version only approved non-secret configuration sources. Do not commit raw ACME storage, secret payloads, private keys or raw service snapshots.

## Traefik production service parity

`traefik3parity_proxy` is part of Swarm stack `traefik3parity`, desired replicas **1**, image **traefik:v3.7.18** (digest pinned in draft), on `badwcai-ebl01`.

- Ports **80/tcp and 443/tcp** published in **host** mode
- Networks `traefik-public` and `traefik3-test`; service alias `proxy` on both
- Static and dynamic config targets: `/etc/traefik/traefik.yml` and `/etc/traefik/cutover-dynamic.json`; config file modes decimal 292 (= octal 0444)
- Container config argument `--configFile=/etc/traefik/traefik.yml`
- Bind directory `/home/farhanabdulla/ebl-traefik3-acme` to `/var/lib/traefik`, writable
- Secret references: `basic_auth_users`, `traefik3stage3_badw_cert`, `traefik3stage3_badw_key`, `traefik3stage3_lmu_cert`, `traefik3stage3_lmu_key`, all mounted using their own names at mode 0444
- Limits: **0.5 CPU, 256 MiB memory**, reservation **64 MiB memory**
- Restart on failure with **5-second delay** and zero max-attempt override
- Update policy: **stop-first**, parallelism 1, pause on failure, 15-second monitor, max failure ratio 0
- Rollback policy: **stop-first**, parallelism 1, pause on failure, **5-second monitor**, max failure ratio 0
- Logging driver: Docker default, with no specific options; no healthcheck or environment variable names
- Only Swarm-generated service/container label keys were observed

The draft `traefik3-production.yml` now records the policy settings and references; but **equivalence is not fully proven** until the deployment-rendered spec is compared against the live service (including Docker's exact CLI Command/Args split, secret/config paths and attachment metadata, and any defaults). Do not run `docker stack deploy` until that comparison is accepted.

## Monitoring service and credential handling

The active `swarmprom_prometheus` task is at **1 replica** and mounts `node_rules` plus `task_rules_tls3_20261113T213540Z`; dual scrape jobs are `traefik:8080`, `traefik3parity_proxy:9100`, `mongodb-exporter:9216` and `redis-exporter:9121`.

The report **withheld actual environment values**. Service metadata confirms these credential-bearing interfaces:

| Service | Credential exposure mechanism | Preserve before redeploy |
| --- | --- | --- |
| `swarmprom_grafana` | `GF_SECURITY_ADMIN_PASSWORD` environment value | Yes; do not replace with checked-in placeholder |
| `swarmprom_alertmanager` | `SLACK_URL` environment value | Yes; do not replace with checked-in placeholder |
| `swarmprom_mongodb-exporter` | `--mongodb.uri` command argument, redacted in report | Yes; do not replace with placeholder |
| `swarmprom_prometheus` | `JOBS` (only non-secret endpoints shown); basic-auth secret reference | Preserve dual scraping and secret reference |

The checked-in `swarmprom.yml` was changed to fail closed on missing `EBL_ALERTMANAGER_SLACK_URL`, `EBL_GRAFANA_ADMIN_PASSWORD`, or `EBL_MONGODB_EXPORTER_URI` rather than substituting historical credential placeholders. This does not supply or migrate secrets. Several checked-in `swarmprom.yml` services specify `json-file` logging, whereas these live service specs reported the default driver. **The complete monitoring stack must not be blindly redeployed from GitHub.** A protected deployment-time credential source and complete live parity check are prerequisites.

## Remaining gates

1. Privately review/sanitize the original Swarm config bodies, confirm actual SHA-256 hashes and either version approved non-secret sources or document a secure provisioning process. Without those bodies, this repository cannot reconstruct a fresh cluster.
2. Render and compare the proposed Traefik 3 stack against live service metadata; document any intentional differences and test in staging before first redeploy.
3. Reconcile monitoring credentials and service defaults before any full Swarmprom stack deployment. No environment or URI values were collected in this safe report.
4. Verify Alertmanager notification delivery with a controlled synthetic alert; LAD-origin API validation is deferred as agreed.
