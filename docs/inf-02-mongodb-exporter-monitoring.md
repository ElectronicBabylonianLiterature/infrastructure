# INF-02 — Restore MongoDB exporter monitoring safely

**Scope:** Changes to the **monitoring stack configuration only**. This PR does not deploy, restart, scale, or modify any production service or MongoDB data. It is independent of the unmerged Phase 0 documentation PR #4.

## Incident evidence

Verified by the operator using existing authorized access on **2026-11-11 (Europe/Berlin)**:

- `swarmprom_prometheus` runs on **caic1**, and `swarmprom_mongodb-exporter` runs on **caic2** (both 1/1 tasks running).
- Prometheus `up{job="mongodb-exporter"}` returned **0** for `10.0.38.39:9104`.
- Prometheus target API reported: **`dial tcp 10.0.38.39:9104: connect: connection refused`**.
- From inside the Prometheus container, the exporter **static homepage** at `http://mongodb-exporter:9216/` responded.
- The homepage check establishes the HTTP listener and Docker-network reachability; it **does not** establish successful MongoDB authentication, successful collection, or acceptable collection overhead.
- A separate, read-only production investigation on November 4 observed the same mismatch and recorded the operational risk of enabling the checked-in `--collect-all` option against the production database.

All command results are summarized here; no raw logs, user identities, secrets, credentials, connection strings or private network dumps are committed.

## Configuration change

In `swarmprom.yml`:

1. Update the existing Prometheus `JOBS` environment entry from `mongodb-exporter:9104` to **`mongodb-exporter:9216`**. Keep the Traefik and Redis scrape entries unchanged.
2. Replace exporter `--collect-all` with two explicit collectors:
   - `--collector.diagnosticdata` — diagnostic data used for MongoDB health and performance statistics.
   - `--collector.replicasetstatus` — replica-set status information.

Percona's **v0.37.0** exporter source declares these exact flag names, a default HTTP listener on `:9216`, and `--collect-all` as enabling all collectors: <https://github.com/percona/mongodb_exporter/blob/v0.37.0/main.go>.

The restricted collector selection intentionally omits `collstats`, `indexstats`, `dbstats`, and `topmetrics` until an operator has independently measured their cost, verified privileges, and justified a need. This does **not** guarantee that the selected collectors are cost-free.

No image upgrade, MongoDB credential change, API modification, deployment, or change to unrelated exporters is included.

## Validation and production prerequisites

1. **Code review first.** Confirm the selected flags are supported by `percona/mongodb_exporter:0.37.0` and the Prometheus JOBS setting is the active scrape discovery source in the currently deployed image/configuration.
2. **Staging/local verification.** Validate the Swarm YAML with the deployment tool's parser on an isolated environment; if feasible, connect the restricted exporter to a representative **nonproduction** MongoDB replica set with a dedicated least-privileged monitoring account. Do not run a production `/metrics` scrape under the original `--collect-all` configuration just to test this PR.
3. **Explicit production approval.** Verify a fresh deployment backup, live configuration drift, account privileges, network access and authorized deployment window. The checked-in stack includes placeholders/credentials and may differ from the production Swarmpit state; never deploy it blindly from GitHub.
4. **Controlled activation.** Apply the reviewed exporter and Prometheus changes together under the approved operational procedure, not through this PR merge alone. Record pre/post image digests and service tasks. Use existing metrics to check for significant MongoDB load changes.
5. **Health acceptance.** Confirm `up{job="mongodb-exporter"} == 1` at the **9216** target, and independently verify that expected MongoDB metrics (including replica-set state, if authorized) are present. `up=1` by itself does not prove MongoDB monitoring is functional.
6. **Cost and safety acceptance.** Monitor `scrape_duration_seconds`, `scrape_samples_scraped`, `scrape_timeout_seconds`, exporter errors, MongoDB CPU/memory, and relevant API latency for a representative observation period. Abort/roll back if scrape latency, authorization errors, MongoDB overhead or application performance become unacceptable.
7. **Rollback.** Restore the previously saved known production exporter configuration and scrape target together through an approved change. The prior target was down, so returning to `up=0` is a known monitoring limitation, **not** an acceptable long-term fix. Investigate separately before reactivating expensive collectors.

## Non-goals and follow-up

- No new Grafana dashboards or alerting rules here (planned **INF-03/INF-04**).
- No unrelated monitoring-image upgrades; the existing Prometheus/Grafana versions and dashboard compatibility must be reviewed before their own migration.
- No runtime permission or TLS changes.
- No claims about MongoDB primary health or root cause of the API queue/OOM events until successful authorized MongoDB metrics are available.

## Review checklist

- [ ] Minimal collector policy and privileges reviewed by the infrastructure/DB administrator
- [ ] Staging/config validation completed
- [ ] Existing production stack drift and secrets handling reviewed
- [ ] Deployment/rollback approach approved
- [ ] Verify correct target, real MongoDB metrics and bounded scrape cost after authorized activation

**Status:** Implementation proposal committed; production has **not** been changed or tested by this PR.
