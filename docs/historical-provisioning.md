# Historical provisioning notes (July 2024 onward)

> **Archive / documentation only — not a production procedure.** These notes preserve the earlier README's provisioning account of the 2024 LRZ VM migration and later annotated updates, extracted during the November 2026 documentation cleanup. They contain historical commands and paths, some of which are obsolete or hazardous on a running production cluster. **Do not execute these commands against the current VMs.**
>
> Current authority: [VM access](vm-access.md), [eBL application operations](day-to-day-operations.md), [Traefik 3 runbook](traefik3-production-runbook.md), and the [dated production inventory](production-inventory-2026-11-19.md). Live configuration is managed on the VMs and through Swarmpit; the public GitHub repository is documentary only.
>
> **Provenance:** Extracted from `README.md` on 20 November 2026, with relative links adjusted to their new documentation/reference paths. The original history remains in Git commits.

## Historical setup and configuration
Knowledge about server infrastructure and Docker concepts (containers, images, networks, configs, secrets, etc.) is necessary.

**All subsections below are historical provisioning/reference material, not live production deployment instructions.** Configurations are maintained on the VMs and in Swarmpit. Do not execute setup, initialization, certificate creation or `docker stack deploy` examples against the running cluster. Use the current [SSH procedure](vm-access.md#connect-over-ssh), [operations guide](day-to-day-operations.md) and [Traefik 3 runbook](traefik3-production-runbook.md) for authorized maintenance.

### 4.1. Ordering VMs and DNS setup
The VMs were provisioned through [LRZ VM management](https://vm.lrz.de/). **This paragraph concerns initial VM provisioning, not routine access to existing production machines.** For a newly issued VM, LRZ provides the initial account and access details through its approved channel; change any temporary credentials according to institutional policy and store them securely. For existing eBL VMs, use the [production SSH access procedure](vm-access.md#connect-over-ssh) and your personal authorized account. Do not try the original provisioning credentials or create a new account simply to perform normal maintenance.

Masterusers can request configuration changes (like RAM or storage upgrades) by opening a ticket at the [﻿Service Desk](https://servicedesk.lrz.de/).

Public eBL DNS is managed by the responsible LMU and BAdW hostmasters (see [Vergabe neuer Sub-Domains](https://doku.lrz.de/verwendung-eigener-domainnamen-10745829.html)). The four production HTTPS hostnames are [www.ebl.badw.de](https://www.ebl.badw.de/), [ebl.badw.de](https://ebl.badw.de/), [www.ebl.lmu.de](https://www.ebl.lmu.de/), and [www.ebl.uni-muenchen.de](https://www.ebl.uni-muenchen.de/). All four were verified during the Traefik 3 cutover. Coordinate future DNS changes with the domain administrators.

### 4.2. Preparations
The setup steps must be performed **on each VM individually**.
For most of the commands you will need `sudo`, but once Docker is set up and running the `docker` commands don't require it.

#### 4.2.1. Set up users
**Initial provisioning only:** Connect through the BAdW full-tunnel VPN and use the temporary administrator credentials supplied for a newly provisioned VM by LRZ. For existing production machines, follow [production SSH access](vm-access.md#connect-over-ssh) with your approved personal account instead. Creating users or changing access permissions on an existing VM requires administrator authorization.

For a new VM, create appropriately authorized administrator users according to institutional policy. The historical setup included a shared `ebladmin` account and used the following group commands:

```sh
adduser ebladmin
usermod -aG sudo ebladmin
usermod -aG ssh-login ebladmin
```
You can then switch to the new user with `su ebladmin`.

#### 4.2.2. Set up ssh keys
**Recommended for authorized VM accounts:** Set up SSH public-key authentication instead of repeatedly entering a password. Never copy the private key to the server or commit it to this repository. Your SSH key and account must be authorized for each VM you access.

On Windows, edit `$env:USERPROFILE\.ssh\config` (the OpenSSH config file); on macOS/Linux, edit `~/.ssh/config`. Add the optional aliases below, replacing `your_vm_username` with your personal VM account. Use `IdentityFile ~/.ssh/id_ed25519` (or your actual private-key file) if the identity is not selected automatically. The aliases are local shortcuts; the IP addresses do not depend on short-hostname resolution.

```sh
# CAIC eBL VM1
Host caic1
  HostName 138.246.225.199
  Port 22
  User your_vm_username

# CAIC eBL VM2
Host caic2
  HostName 138.246.225.201
  Port 22
  User your_vm_username

# CAIC eBL VM3
Host caic3
  HostName 138.246.225.202
  Port 22
  User your_vm_username
```
**On each VM (with approval):** Add only the **public** SSH key (for example, the contents of `~/.ssh/id_ed25519.pub`) to your own account's `~/.ssh/authorized_keys`. Restrict the `~/.ssh` directory to mode `0700` and `authorized_keys` to `0600`. Never overwrite other administrators' existing authorized keys or add keys to a shared account without approval.

Reconnect with `ssh caic1`, `ssh caic2` or `ssh caic3` while the BAdW VPN is connected. Visual Studio Code Remote SSH can use the same local OpenSSH aliases. If the short hostname fails, use the IP-backed alias or the explicit IP-based command shown above.

#### 4.2.3. Install Docker
- [﻿Install Docker Engine - Community from Docker's repositories](https://docs.docker.com/install/linux/docker-ce/debian/#install-using-the-repository) 
(current version: `Docker version 26.1.4, build 5650f9b` )
- Follow the [Docker post-installation steps](https://docs.docker.com/engine/install/linux-postinstall/) only when provisioning a **new VM**; do not reinstall or restart Docker on an existing production VM as routine maintenance.
- The `docker` Unix group grants **root-equivalent privileges**. Only authorized administrators should be added; avoid treating it as a harmless convenience.
- The repository's [daemon.json](../reference/host/daemon.json) contains logging and metrics settings. Inspect `/etc/docker/daemon.json` and **merge** settings with the existing JSON; do **not** append another JSON object using `>>`. An invalid daemon configuration can prevent Docker from starting.
- Validate the candidate settings with `sudo dockerd --validate --config-file=/etc/docker/daemon.json` (or a temporary candidate path) before an **authorized** Docker restart. Restarting the daemon may disrupt Swarm tasks and must be coordinated as a separate maintenance operation.
- `sudo systemctl status docker` checks daemon state without changing it.

#### 4.2.4. Set up the firewall
Certain ports need to be opened for Docker to be able to communicate between the VMs. Docker additionally opens up ports via iptables that don't show up in the ufw rules
and that don't need to be configured separately.

For each VM, you need to allow traffic to the other two VMs. For the first VM, run the commands below with the IPs of the 2nd and 3rd VM. Adapt accordingly for the other VMs.

```sh
sudo ufw allow proto tcp from <VM2 IP> to any port 2377,7946 comment 'Docker Swarm'
sudo ufw allow proto udp from <VM2 IP> to any port 7946,4789 comment 'Docker Swarm'

sudo ufw allow proto tcp from <VM3 IP> to any port 2377,7946 comment 'Docker Swarm'
sudo ufw allow proto udp from <VM3 IP> to any port 7946,4789 comment 'Docker Swarm'
```
Additionally, the following port must be opened for metrics. This command is identical on all three VMs:

```sh
sudo ufw allow from 172.18.0.0/16 to any port 9323 comment 'Docker Metrics'
```
#### 4.2.5. Add image pruning
Unused images may consume disk space. The following historical cron example removes **dangling** images older than 24 hours; it does not remove volumes or all unused tagged images. Review disk usage and existing scheduled tasks before installing or modifying a pruning job. The example cron entry is:

```sh
0 4 * * * docker image prune -f --filter "until=24h" 2>&1 | /usr/bin/logger -t docker-pruning
```
The cron entry runs at 04:00 and logs as `docker-pruning`. Without `--all`, `docker image prune` removes only dangling images matching the age filter. It does not prune Docker volumes. Do not assume this schedule is installed on every node without checking the actual crontab.

#### 4.2.6. Disable internal sum checking
On Debian 12, Docker Swarm can sometimes fail due to issues with internal sum
checking. What happens is that after setting up the swarm, it is partially functional
(it can ping but cannot transfer any data). In Swarmpit the nodes show up but remain
in a "Loading..." state indefinitely. If such symptoms occur, you need to disable
internal sum checking with:

```sh
ethtool -K ens192 tx-checksum-ip-generic off
```
See [﻿here](https://github.com/swarmpit/swarmpit/issues/688) for more details.

### 4.3. Docker Swarm Setup
For setting up the infrastructure you need the different YAML and other configuration files from this repository.
It is recommended to download all of it onto the first VM. The following commands will assume you did so from your user directory
(e.g., `cd ~ && git clone https://github.com/ElectronicBabylonianLiterature/infrastructure.git`).

#### 4.3.1. Initialize the swarm
**Historical new-cluster instructions only; do not initialize the existing production Swarm.** On the first VM, [﻿create a new swarm](https://docs.docker.com/engine/swarm/swarm-tutorial/create-swarm/). This turns
the first VM into the manager node of the swarm. It will output a command for joining the swarm which has to be run on
each of the two other VMs which will make them worker nodes. If you need to display the join command again, run
`docker swarm join-token worker` on the manager. Check the status of the swarm by running the command below on the manager node:

```sh
$ docker node ls
ID                            HOSTNAME        STATUS    AVAILABILITY   MANAGER STATUS   ENGINE VERSION
z2hbdfjkyqn3z1b8kmndm7exp *   badwcai-ebl01   Ready     Active         Leader           26.1.4
3bzj3ocpoqy1vvm07l56n7ef0     badwcai-ebl02   Ready     Active                          26.1.4
k5vo2xli9y8b4q9jcirx6byll     badwcai-ebl03   Ready     Active                          26.1.3
```
The node list is a **19 November 2026 snapshot**, not a live guarantee. VM1 is the only manager; check `docker node ls` for the current state.

#### 4.3.2. Optional: Test Swarmpit

**Historical setup note:** The previous standalone Swarmpit installer and port-888 instructions are not the access or upgrade procedure for the existing eBL cluster. Swarmpit is already deployed as the `swarmpit` Swarm stack behind Traefik 3 at [https://www.ebl.badw.de/cluster/swarmpit/](https://www.ebl.badw.de/cluster/swarmpit/).

Use your approved administrative account to inspect running services. Before any stack redeployment, reconcile the live service specification with the repository files; see [Swarmpit deployment](day-to-day-operations.md#deploying-ebl-through-swarmpit) and the [Traefik 3 operations guide](traefik3-production-runbook.md). Do not run the old installer against production simply to troubleshoot access.

### 4.4. SSL Certificates

**MongoDB internal TLS — new-cluster provisioning or authorized certificate rotation only.** These certificates secure the MongoDB replica set and are separate from the public HTTPS certificates managed automatically by Traefik 3.

The active [MongoDB replica-set manifest](../reference/database/mongodb-replica_set.yml) references the Docker secrets `mongoCA.crt`, `ebl01.pem`, `ebl02.pem` and `ebl03.pem`. Individual certificate/key files are mounted in the corresponding MongoDB containers; replica members and clients must trust the CA certificate.

For a **new cluster** or approved renewal, follow the institution's private CA/key-management procedure. MongoDB server certificates must contain the correct DNS **Subject Alternative Names (SANs)** for the respective node hostnames, including `badwcai-ebl01.srv.mwn.de`, `badwcai-ebl02.srv.mwn.de` and `badwcai-ebl03.srv.mwn.de` where applicable. Do not rely solely on the certificate Common Name for hostname verification, and preserve the required x.509 member-authentication properties.

Inspect each certificate privately before use, for example:

~~~sh
openssl x509 -in ebl01.crt -noout -subject -issuer -dates -ext subjectAltName
~~~

Protect the CA key and avoid printing private key material. Coordinate certificate rotation and any MongoDB member restarts using an approved procedure and rollback plan. **Do not regenerate the production CA, overwrite live Docker secrets or redeploy the populated database based on historical bootstrap commands.**

### 4.5. HTTPS and Monitoring
We use a setup based on the (now deprecated) [﻿Docker Swarm Rocks](https://dockerswarm.rocks/).

#### 4.5.1. Traefik and Consul

Public traffic enters eBL through **Traefik 3.7.18**, managed by Docker Swarm. The production service is `traefik3parity_proxy` in the `traefik3parity` stack and listens on host ports 80 (HTTP and ACME HTTP-01) and 443 (HTTPS). It routes requests over the `traefik-public` overlay network to the application and administration services.

The ingress service runs as one replica on the designated ingress node because host-mode ports cannot be published by multiple tasks on that node. The frontend and API have separate application replicas. For the current stack definition, see [traefik3-production.yml](../reference/networking/traefik3-production.yml); for operating procedures, see the [Traefik 3 operations guide](traefik3-production-runbook.md).

**TLS:** Traefik uses Let's Encrypt ACME, with persistent certificate storage on the ingress node. Certificates and account keys must be kept in restricted persistent storage and backed up securely; neither the ACME JSON file nor Docker secret material belongs in Git.

**Deployment:** The production stack refers to versioned external Docker Swarm configs. Before any redeployment, verify that those configs and secrets exist, review the actual running service specification, and follow the deployment checks in the operations guide. Do not run `docker stack deploy` from this repository without completing those checks.

**Legacy support:** The `traefik-consul_traefik` service remains stopped at zero replicas for emergency rollback; its published port definitions remain in its service specification. The Consul leader is a separate service and remains available as required by legacy components. Do not scale up the old reverse proxy while Traefik 3 owns ports 80 and 443.

#### 4.5.2. Swarmpit

Swarmpit is already running behind Traefik 3. The 19 November inventory found **four** services: `swarmpit_app` on VM1, global `swarmpit_agent` on all VMs, and both `swarmpit_db` (CouchDB) and `swarmpit_influxdb` (InfluxDB) on VM2. Their storage uses named local volumes; preserve these during recovery.

The checked-in [swarmpit.yml](../reference/monitoring/swarmpit.yml) is a **historical, incomplete reference**: it omits InfluxDB, and CouchDB placement/resources differ from production. Do not deploy it as a replacement. For the **eBL application**: choose **Stacks → eBL → dropdown next to Edit → Redeploy** for application updates, or **Stacks → eBL → Edit → Last Deployed** to make and deploy configuration changes. **Never deploy `Current Engine`**. The exact [steps and verification safeguards](day-to-day-operations.md#deploying-ebl-through-swarmpit) are in the operations guide.

#### 4.5.3. Swarmprom

[Swarmprom](https://github.com/stefanprodan/swarmprom) provides Prometheus metrics, Grafana dashboards and Alertmanager alerting. The existing monitoring deployment is the `swarmprom` Swarm stack.

The [swarmprom.yml](../reference/monitoring/swarmprom.yml) manifest includes the production `traefik3parity_proxy:9100` scrape target and preserves the legacy `traefik:8080` target during the rollback period. The installed combined task rules use the immutable external config `task_rules_tls3_20261113T213540Z`. The [standalone TLS alert definitions](../reference/monitoring/traefik3-certificate-alerts.yml) are **not** a replacement for the complete rule file.

**Private deployment inputs:** Never put passwords, Slack webhooks or MongoDB connection credentials directly into a commit. The monitoring manifest requires `EBL_ALERTMANAGER_SLACK_URL`, `EBL_GRAFANA_ADMIN_PASSWORD` and `EBL_MONGODB_EXPORTER_URI`, supplied from an approved restricted credential store. Review the **whole rendered stack** against the running services before any redeployment. Do not deploy placeholder values, replace live service settings with historical defaults, or redeploy the entire stack just to change one alert rule.

See the [Traefik 3 operations guide](traefik3-production-runbook.md) for metrics, certificate renewal alerts, validation and rollback. A healthy Alertmanager connection does not on its own prove notification delivery.

On 19 November 2026, Prometheus, Grafana and Alertmanager were on VM1; MongoDB and Redis exporters and Karma on VM2; node-exporter, cAdvisor and dockerd-exporter on all three VMs. The audit confirmed service/config *names*, not effective scrape success or notification delivery. The reference `swarmprom.yml` does not replace the private live configuration.

The Grafana UI is at [https://www.ebl.badw.de/cluster/grafana/](https://www.ebl.badw.de/cluster/grafana/).

Import the [﻿Traefik dashboard](https://grafana.com/grafana/dashboards/4475) to Grafana.

### 4.6. MongoDB initialization

**Fresh-cluster provisioning only — not a production maintenance procedure.** The historical [mongodb.yml](../reference/legacy/mongodb.yml) defines a non-TLS bootstrap used before the TLS-protected [mongodb-replica_set.yml](../reference/database/mongodb-replica_set.yml) was deployed. The existing production cluster is populated and already uses a replica set.

For a brand-new, empty environment, obtain an approved provisioning plan covering MongoDB administrator Docker secrets, certificate lifecycle, node placement and persistent volumes, and the sequence for creating replica-set membership. Do not reuse historical bootstrap credentials or overwrite production secrets.

**Never deploy the non-TLS bootstrap stack against the existing production database or treat database reinitialization as a repair operation.** Consult the diagnostic guidance below and an approved recovery plan instead.

### 4.7. Replica set

The [MongoDB replica-set manifest](../reference/database/mongodb-replica_set.yml) defines three MongoDB 7 services on the three designated VMs, replica-set name `rs-ebl`, and TLS/x.509 member authentication. The host-facing ports are 27017, 27018 and 27019, respectively.

For **existing production**, begin with read-only service inspection on the Swarm manager:

~~~sh
docker service ls --filter name=ebl-mongodb
docker service ps ebl-mongodb_mongo1
docker service ps ebl-mongodb_mongo2
docker service ps ebl-mongodb_mongo3
~~~

Use `mongosh` with an authorized MongoDB account, trusted CA and the appropriate authentication database. For example, **inside an approved MongoDB container where the CA secret is mounted**:

~~~sh
mongosh --host badwcai-ebl01.srv.mwn.de:27017 --tls --tlsCAFile /run/secrets/mongoCA.crt --username <approved-user> --authenticationDatabase admin
~~~

After authentication, inspect `rs.status()` and `db.hello()`. These diagnostic commands do not modify replica-set membership. Avoid `--tlsAllowInvalidCertificates` in routine administration.

**New empty cluster only:** A replica-set administrator initializes membership once using `rs.initiate()` and verified member addresses. **Never call `rs.initiate()` again on an existing production set.**

For TLS or election failures, first examine logs, certificate chains/SANs/expiration, DNS, network connectivity, and replica-set quorum. **Do not redeploy the non-TLS bootstrap, delete the MongoDB or monitoring stacks, remove Docker secrets, or regenerate the CA as a troubleshooting shortcut.** Those operations require a separately approved recovery plan.

### 4.8. Monitoring

The MongoDB exporter runs as `percona/mongodb_exporter:0.37.0`. The reference Prometheus job uses port `9216`. The 19 November audit did **not** verify actual scrapes or MongoDB metrics, so these require separate authorized checks.

The dedicated MongoDB exporter account requires monitoring permissions. Historical provisioning used `clusterMonitor` on `admin` and read access to `local`. These are **not instructions to recreate production users**. Preserve the current approved credentials and reference them through the private `EBL_MONGODB_EXPORTER_URI` deployment input; do not paste them into `swarmprom.yml`.

You can now import the [﻿MongoDB dashboard](https://grafana.com/grafana/dashboards/2583) to Grafana. In Grafana, edit the dashboard JSON and change the metric
prefix from `mongodb_` to `mongodb_mongod_`.

### 4.9. Docker registry

The running registry is `registry_registry1` on VM1 (persistent `registry_registry1` volume), with `registry_ui` on VM2 (persistent `registry_registry-ui` volume). GitHub workflows publish application images, but production updates are coordinated separately through the VMs/Swarmpit. The ingress-published TCP ports 5000 and 8000 require authorized network-filter verification; their publication is not proof of external reachability.

The [registry stack](../reference/registry/registry.yml), [registry config](../reference/registry/registry_config.yml), and [UI config](../reference/registry/docker-registry-ui_config.yml) are **historical references**, not a current deployment or credential source. Do not create/recreate production secrets, change purge policy, or deploy these examples during routine maintenance. Verify actual registry login, tag retention and restore process with the responsible operators.

### 4.10. eBL application

At the 19 November audit, the live `ebl` stack contained `ebl_api` (3/3), `ebl_frontend` (3/3), `ebl_ai-api` (1/1), `ebl_redis` (1/1) and `ebl_sinkhole` (1/1). The API and frontend each had **one task on VM1 and two on VM2**, none on VM3. This is task scheduling at one point in time, not a placement guarantee. No application-level Swarm health checks were declared for these apps.

Two additional historical API services, `ebl-api_api` and `ebl_api_api`, were each at 0/0. Their intended retirement is not established; do not delete them without an owner decision. No active Inception service was observed, although named Inception volumes remain on VM3.

The checked-in [ebl.yml](../reference/application/ebl.yml) lacks the sinkhole and retains Traefik 1.x labels and placeholder settings. It is **not the production deployment source**. The effective Traefik 3 routes and controls reside in the private dynamic configuration, not old labels. See the [operations guide](day-to-day-operations.md). Frontend build-time configuration is handled by its [GitHub workflow](https://github.com/ElectronicBabylonianLiterature/ebl-frontend/blob/master/.github/workflows/main.yml).

### 4.11. Mongosync

The `mongosync_mongosync` service was 1/1 on VM3 in the inventory and supports development database `ebldev`. Its source is the dedicated [mongosync repository](https://github.com/ElectronicBabylonianLiterature/mongosync). The historical Compose file and Docker secret names are reference material only; they are **not** authorization to recreate users, reset credentials or redeploy the live service.

### 4.12 Sitemap
For the sitemap automated and manual update configuration, check the [Sitemap section](https://github.com/ElectronicBabylonianLiterature/ebl-frontend#sitemap) of the Frontend repository documentation.
