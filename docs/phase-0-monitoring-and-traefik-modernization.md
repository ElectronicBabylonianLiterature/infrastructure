# Phase 0 — eBL production monitoring and Traefik modernization audit

> **Status:** Planning/audit record; no production changes authorized or performed by this PR.
> **Evidence date:** 2026-11-04 (Europe/Berlin). Observations are time-bounded snapshots, not continuous health guarantees.
> **Repository baseline:** `infrastructure` `master` at `37ae1adb68d2b97de0cf3d1a5fb3d7459f8360c3`.

## Goal and scope

Establish a safe, evidence-led implementation baseline for eBL's monitoring, overload protection, and Traefik replacement. This document consolidates findings from a separately conducted, **read-only** November 4 production investigation and the versioned infrastructure configuration. Treat the live deployment as authoritative for runtime state; this repository describes intended configuration but contains known drift.

**In scope:** inventory, confirmed faults, observability gaps, traffic/route/TLS compatibility checklist, safe change order, outstanding verification, and PR/deployment gates.

**Out of scope:** deployment, restarting tasks, changing rate limits or firewall rules, MongoDB operations, editing secrets, adopting a new proxy, and assuming that unverified causes have been proven.

## 1. Evidence baseline

| Finding | Supporting observation | Confidence / important boundary |
| --- | --- | --- |
| Three Swarm nodes; three API and three frontend replicas | November 4 task inventory: one current API replica per VM; all 3/3 running | Confirmed at observation only; no explicit one-per-node placement policy in checked-in `ebl.yml` |
| Two API out-of-memory events | API containers OOM-killed on caic3 (November 1) and caic2 (November 4) and replaced by Swarm | Confirmed. Exact allocation cause is unknown; exit code 137 **without** `OOMKilled=true` is not sufficient proof |
| Recent API queues on all three replicas | Bounded November 4 log windows: observed maxima 49 (caic1), 40 (caic2), 44 (caic3) | Confirmed for different overlapping windows; these are not simultaneous live gauges or request totals |
| Historical October 26 impairment | 358 API requests in a short 499-record proxy excerpt; 133 API HTTP 499, 118/122 to historical backend on caic2 | Task-to-VM mapping confirmed using retained Swarm history; HTTP 499 means client disconnected, **not** verified human failure; earlier caic2 task was not OOM-killed |
| Current API traffic differs from historical episode | Five-minute November 4 sample: 1,548 API requests, one HTTP 499, approximately balanced across current replicas | Different window and request mix; cannot infer the sinkhole works or the incident is resolved |
| Redis is responding | Existing exporter reported Redis `up=1`, no eviction and low usage in a bounded snapshot | Does not establish that every public API route uses Redis effectively |
| MongoDB exporter scrape broken | Prometheus target attempts port 9104; exporter static listener responded on 9216 | Port mismatch confirmed; database health, primary role and slow queries remain unknown |
| Sinkhole likely excluded from Traefik | Live proxy config constrains provider discovery to `tag==traefik-public`; running sinkhole lacks this tag and is absent from backend metric census | Strongly supported **routing exclusion**, not a verified effective block count or proof about all alternative routes |
| Runtime config drift | `ebl.yml` in Git: API average 5/second, burst 10; live API labels: average 10/second, burst 800 | Observed; threshold appropriateness and actual enforcement require testing |
| No API health probes in current tasks | Current API container inspection found no application health check | Container `Running` does not establish that 12 Waitress threads can serve requests |
| Select slow routes | November 4 five-minute sample: `/api/texts` median ~713 ms (n=90); `/api/fragments/query` median ~3,823 ms (n=8); one text/chapter descendant ~34.7 s | Reverse-proxy residence time, not isolated database or CPU time; sparse query sample |

Do **not** infer that bots are the sole cause of backend congestion or that one VM is permanently defective. A confirmed configuration fault, a likely proxy-routing fault, intermittent worker queues, OOMs, and slow routes are distinct work items.

### Sources and preservation

- Baseline configs: [`ebl.yml`](../ebl.yml), [`traefik-consul.yml`](../traefik-consul.yml), [`traefik.toml`](../traefik.toml), [`swarmprom.yml`](../swarmprom.yml), [`swarm_task.rules.yml`](../swarm_task.rules.yml), [`swarm_node.rules.yml`](../swarm_node.rules.yml), [`registry.yml`](../registry.yml), [`swarmpit.yml`](../swarmpit.yml), [`inception-annotation-tool.yml`](../inception-annotation-tool.yml).
- Historical mitigation proposal: [infrastructure PR #3](https://github.com/ElectronicBabylonianLiterature/infrastructure/pull/3) (README-only; does **not** itself deploy the sinkhole).
- Production observations: separately prepared, sanitized read-only diagnostic report dated November 4, 2026. Raw logs, client IPs, credentials, container secrets, and service environment dumps are intentionally **not** reproduced in this public repository.
- The source code and Docker image currently deployed must be mapped explicitly: mutable `:master` tags and an image digest alone do not identify a Git commit.

## 2. Existing monitoring: inventory and limitations

| Component | Defined in repository | Phase 0 conclusion | Follow-up |
| --- | --- | --- | --- |
| Prometheus / retention | `swarmprom.yml`; checked-in image `stefanprodan/swarmprom-prometheus:v2.5.0` | Runtime indicates seven-day retention; useful historical context can expire quickly | Versioned dashboard/metric inventory; consider longer retention after storage sizing |
| Grafana | `swarmprom.yml`; checked-in image `stefanprodan/swarmprom-grafana:5.3.4` | Health endpoint responds; **dashboard contents and alert delivery not inspected** | Inventory existing dashboards and data sources before building duplicates |
| MongoDB exporter | `swarmprom.yml`: `percona/mongodb_exporter:0.37.0`, `--collect-all`; Prometheus job `mongodb-exporter:9104` | Confirmed scrape/listener mismatch; simply pointing Prometheus at `/metrics` could initiate broad collection work | Review collectors, authentication, and expected overhead; use a minimal approved collector set |
| Redis exporter | `swarmprom.yml` | Responds and supplies aggregate cache metrics; file contains duplicated `redis-exporter` YAML service key | Remove ambiguity in an independently reviewed config fix; distinguish aggregate Redis hits from API-route coverage |
| Node and container exporters | `swarmprom.yml` and Swarm alert rules | VM/container CPU, memory and disk data available | Add clear OOM/restart/replica dashboards and tested alerts |
| Traefik metrics/access log | `traefik.toml`, `swarmprom.yml` | Backend-level status/latency exists; attribution to routes/tasks and sinkhole coverage is incomplete | Add low-cardinality route/per-replica visibility, verify match counters and deny reasons |
| Python API | `ebl-api` | No discovered dedicated API scrape job; Waitress queues currently inferred from bounded log summaries | Add lightweight request/queue/dependency signals; decide whether Waitress exposes reliable queue measurement before promising a metric |
| Alertmanager and rules | `swarmprom.yml`, `swarm_node.rules.yml`, `swarm_task.rules.yml` | Checked-in rules cover host and task resources; no named queue/latency/499/sinkhole/scrape/replication alerts in runtime inventory | Calibrate and test delivery after source signals are reliable |

**Never show missing metrics as green.** Separate `unknown`, `not scraped`, `healthy`, and `degraded`. Dashboard data must be clearly labeled by timestamp/window and respect metric cardinality/privacy.

### Proposed minimum eBL System Health panels

1. **Coverage:** monitoring target health, data age, exporter scrape failure; alert delivery.
2. **Availability:** Swarm desired/current replicas, API readiness/liveness (once instrumented), task replacements and OOM flags.
3. **API:** request rate, normalised route and status family, p50/p95 latency, active/queued work where measured, 499/429/503, errors.
4. **Infrastructure:** each VM's CPU, RAM, disk; per-container memory versus *configured cgroup limit*, CPU throttling where available.
5. **Database/cache:** MongoDB primary/secondary state, replication lag, connections and expensive operations **after safe exporter restoration**; Redis usage/hit/miss/eviction and API cache coverage.
6. **Traffic protection:** admitted versus rejected requests, sinkhole route matches, throttled requests, verification that legitimate crawler/research flows still work.

Do not label HTTP 499 events as a percentage of failed researchers. Avoid raw URLs, user IDs, IP addresses and bearer tokens in metric labels or public dashboards.

## 3. Traefik migration audit and compatibility checklist

### Known baseline

- `traefik-consul.yml` pins `traefik:v1.7` on a node labeled `consul-host`; runtime binary version observed `1.7.34`.
- `traefik.toml` uses the v1 Docker/Swarm provider, provider tag constraint `tag==traefik-public`, Consul-backed ACME settings, HTTP→HTTPS redirection, a legacy `/fragmentarium`→`/library` redirect, and a metrics endpoint.
- Services use v1 labels such as `traefik.frontend.rule`, `PathPrefixStrip`, `traefik.port`, `traefik.frontend.auth.basic.usersFile`, and `traefik.frontend.rateLimit.*`.
- DNS, certificate paths and persisted ACME state need an explicit inventory before adopting a supported modern Traefik release. **Do not perform an image-tag-only upgrade.**
- The proxy, Swarm manager, and Consul leader are documented on one VM. This is an availability design constraint, not a proven current incident cause.

### Routing and feature-compatibility matrix (must be filled out before cutover)

| Current route/feature | Current configuration location | Must be validated in staging |
| --- | --- | --- |
| Public frontend `/` and SPA fallback | `ebl.yml` | Root and nested routes, status codes, static assets, authentication callbacks; both eBL hostnames |
| API `/api/` stripping | `ebl.yml` | Correct path mapping, methods, CORS/auth, upload sizes, cache headers, errors |
| Sinkhole priority and matching | **live** Swarm labels (not fully committed) and `traefik.toml` constraint | Provider inclusion, precedence, rejected response, normalized route scope, verified forwarded-client trust, legitimate researchers and crawler false positives |
| HTTP→HTTPS and TLS | `traefik.toml`, Docker config, Consul-backed ACME | All current domains/SANs, cert renewal, persisted ACME state, challenge paths, rollback and certificate file access |
| `/fragmentarium`→`/library` | `traefik.toml` | Redirect status, query/fragment preservation, SEO canonicals |
| Swarmpit, Grafana, Prometheus, Alertmanager, Consul and other `/cluster/` UIs | `swarmpit.yml`, `swarmprom.yml`, `traefik-consul.yml` | Auth, path prefix stripping, dashboard access restrictions, host-specific rules |
| Registry `/v2/` and registry UI | `registry.yml` | CI push/pull compatibility, authentication, non-public administration paths |
| Optional annotation tool `/inception` | `inception-annotation-tool.yml` | Path and authentication behavior if deployed; no assumed live activation |
| Docker overlay networks and placement | all stacks | Explicit Swarm provider/network selection, task discovery, replica health/recovery |
| Per-client and total admission limits | live service labels; `ebl.yml` | Distinguish rate versus concurrency, trusted client identity, bursts for real browsers, rate-limit error semantics and telemetry |

### Required design decisions (not preselected)

- Supported Traefik version and exact migration sequence based on maintained vendor documentation, plugin compatibility, Docker/Swarm version, ACME and Consul migration requirements.
- How to handle certificate state without exposing private keys in version control, and how to reverse an unsuccessful cutover.
- Whether to retain a single ingress instance for the first cutover or design external multi-ingress failover as a separately scoped project.
- Where admission controls live (proxy versus app), including service-wide in-flight ceilings across distributed clients, trusted forwarding headers, and safely scoped research/crawler exemptions.
- Whether old 0/0 services expose any residual routing labels or conflicting paths; audit live effective routes rather than assuming they are unreachable.

### Staging acceptance requirements

- New config builds and serves all paths in the matrix using test DNS/certificates; verify routing, auth, redirects, TLS, API calls, static assets and user-facing error behavior.
- Confirm sinkhole matches only reviewed rules, proxy client-IP handling cannot be bypassed by spoofed headers, and rate/concurrency controls do not block normal institutional NAT/shared-IP traffic.
- Verify metrics and dashboards on the proposed proxy; prove that an unhealthy API replica can be removed from the active route set safely and recovered.
- Prove a rollback to the previous deployment and valid certificate state with reproducible steps, not just a promise to revert a Git commit.
- Obtain explicit institute/IT approval before any production deployment.

## 4. Priorities, repository ownership, and PR handoff

| Order | Proposed PR | Repository | Concrete deliverable / acceptance |
| --- | --- | --- | --- |
| P0 | **INF-02: Restore MongoDB monitoring safely** | `infrastructure` | Correct the scrape target only with a reviewed minimal collector policy; validate monitored DB state and collector overhead. |
| P0 | **INF-05: Reconcile and validate sinkhole inclusion** | `infrastructure` | Correct verified provider-tag exclusion after reviewing full effective rules and false-positive policy; capture matches and rejected status. Coordinate with open PR #3. |
| P0 | **API-01 + INF-06: API latency/queue/memory telemetry** | `ebl-api`, then `infrastructure` | Privacy-safe normalized routes, workload, process saturation and per-replica metrics; add Prometheus scrape and Grafana graphs. |
| P1 | **INF-03/04: Grafana baseline panels and alerts** | `infrastructure` | Versioned dashboards for existing signals first; tested exporter/OOM/replica alerts with delivery verification. |
| P1 | **API perf: targeted analysis and bounded operations** | `ebl-api` | Start with `/api/texts`, `/api/fragments/query`, large text/chapter operations, external AI HTTP timeouts; instrument and test before changing query plans. |
| P1 | **FRONT-01: lazy text-catalogue loading** | `ebl-frontend` | Remove avoidable startup `/api/texts` calls while retaining existing promise caching and editor compatibility. |
| P2 | **INF-07/08/09: staged modern Traefik migration** | `infrastructure` | New isolated proxy config; label/middleware/route translation across stack files; certificate/rollback playbook and integration tests. |
| P2 | **INF-10/11: approved cutover and capacity policy** | `infrastructure` | Controlled deployment and proven rollback; calibrated route-sensitive admission limits with real researcher/crawler compatibility. |
| P3 | **INF-12/13: versioned monitoring upgrade and runbook** | `infrastructure` | Separate Grafana/Prometheus upgrades, retention review and incident response procedures. No concurrent major proxy/monitoring cutovers. |

**Emergency exception:** repairing an actively unsafe production incident may proceed separately via the appropriate approval process; a documentation PR must not delay recovery.

## 5. Unresolved investigation items and owner questions

- [ ] Identify deployed API and frontend image-to-source commit provenance (immutable digests are known, commit labels missing).
- [ ] Confirm MongoDB primary/secondary status, connection pressure, replication lag, and safe profile of expensive query activity with authorized read-only access.
- [ ] Determine which operations occupy Waitress threads when queues grow; keep historical 87-depth process attribution unresolved unless traceable.
- [ ] Characterize memory growth/peak allocations leading to the confirmed caic2 and caic3 OOM events. Do not assume a memory leak or blindly raise container limits.
- [ ] Audit actual existing Grafana dashboards, alert receivers, delivery tests, and exporter collector configuration/overhead.
- [ ] Inventory all **effective** public routes, service aliases, real production DNS/certificate ownership and renewal strategy.
- [ ] Determine exact upstream forwarding trust chain, sinkhole match scope, block rates and false-positive risks for institutions and real crawlers.
- [ ] Confirm operational availability and data retention for incident logs outside Prometheus's seven-day history.
- [ ] Assign deployment approvers for DNS, certificate, Docker Swarm, monitoring and security policy changes.

## 6. Phase 0 done criteria

- [x] Record existing repo-defined architecture and live differences from November 4 read-only investigation.
- [x] List confirmed incidents separately from suspected causes and unmeasured security/bot attribution.
- [x] Specify the required dashboard signals, missing metrics and safe Mongo exporter repair.
- [x] Inventory versioned routes/components known to require migration, plus explicit unknowns.
- [x] Define implementation PR boundaries, dependencies, rollback/testing gates and owners.
- [ ] Have infrastructure maintainers confirm the still-unverified routes, certificate access, monitoring receiver ownership, and required approval process.
- [ ] Have a maintainer review/approve the Phase 0 plan before proceeding with sensitive production changes.

## Change safety / privacy

This PR is intentionally **documentation-only**. It does not run MongoDB queries, install software, add secrets, execute against production, change application/runtime code, or activate any new blocking rule. The data summarized here were collected separately via low-impact, read-only commands; production interventions require independent review and approval.
