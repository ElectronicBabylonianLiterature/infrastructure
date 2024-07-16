# Electronic Babylonian Library Infrastructure

This repository describes the architecture of the Electronic Babylonian Library, a Dockerized cuneiform editing platform hosted on three VMs at the [Leibniz Supercomputing Centre (Leibniz Rechenzentrum, LRZ)](https://www.lrz.de/english/) of the [Bavarian Academy of Sciences and Humanities (Bayerische Akademie der Wissenschaften, BAdW)](https://badw.de/en/the-academy.html).

## General Architecture

The system consists of a Docker Swarm distributed over three Debian VMs. The web app is built in React/TypeScript and communicates with a Python backend and a MongoDB database. When a PR is merged into the master branch of the ebl-api or ebl-frontend repositories, a new Docker image is built and pushed to our own private Docker registry. The next time the ebl-stack is re-deployed (either via the commandline or the Swarmpit UI), the new image is pulled and goes live.

<!-- todo: add system architecture graph -->

Each component of the system is implemented as a Docker stack that is configured with a YAML-file and optionally some other configuration
files or secrets (passwords and api keys). Each stack is deployed in a Docker swarm that distributed all services across the three VMs.
Changes to the swarm are only made on the main node (the manager) which delegates the tasks to the other nodes as appropriate. This way, if
one task fails (e.g., due to an error), the other nodes take over, reducing downtime to a minimum.

The MongoDB database follows a similar concept in that it is replicated. Each of the three VMs hosts one full copy of the entire data, and
read and write operations are distributed across and synchronized between the three replica members. One member of this replica set is the
primary, and the others are secondaries. If the primary fails, the remaining nodes perform a voting and elect a new primary that takes over
the function of the former primary. Though similar, the Docker swarm and the replica set are two different concepts (e.g., the Docker swarm
manager and the MongoDB primary node can be on separate VMs).

Networking is handled by Traefik, a reverse proxy that allows our Docker services to talk to each other and to become accessible from outside the server.

## Monitoring and Maintenance

Monitoring and basic maintenance is primarily done via [Swarmpit](https://swarmpit.io/). Our instance is accessible at <https://www.ebl.lmu.de/cluster/swarmpit/> and allows you to check the system status, view logs, and (re-)deploy services.

<!-- todo: add swarmpit screenshot -->

For more complex tasks you need to access the servers via ssh. For that, you need to activate the BAdW full-tunnel VPN and log into the server
with your username and password. It is recommended to add the three nodes to your ssh config and set up ssh keys which greatly simplifies
access which is especially convenient for setting up the database which requires you to perform steps on each machine individually.

Additional information and statistics about the system are displayed in our Grafana instance [here](https://www.ebl.badw.de/cluster/grafana/). Traefik also comes with a UI that can be accessed at <https://www.ebl.badw.de/cluster/traefik/>. Our private Docker registry has a basic UI, too.

## Backup copies

6 daily backup images of the servers are made, at 02:20, 06:20, 10:20, 14:20, 18:20 and 22:20 hrs. The images are kept for 14 days. The images
can be restored by the LRZ on short notice by opening a ticket on their [Service Desk](https://servicedesk.lrz.de/). If it is necessary to
restore a backup copy, the images of all nodes of the Replica Set should be restored, not just one of the nodes, as otherwise they will be out
of sync.

## Setup

Note that the steps describe the state of the system right after the migration to newer and more powerful VMs in July 2024. We cannot
guarantee that the configuration reflects the latest state of the setup (though we do our best to keep everything up to date). The most
recently deployed versions of each component can be seen in the Swarmpit UI. Whenever changes are made via Swarmpit, the corresponding file in
this repository should be updated accordingly. The local commands are also the MacOS variants which should mostly work on other operating
systems but may differ slightly.

### Preparations

First, the VMs must be prepared for setting up the Docker swarm. The following steps must be performed **on each VM individually**. For most of the commands you will need sudo, but once Docker is set up and running and you are in the `docker` group, you can run all `docker` commands without sudo.

#### 1. Set up users

Activate the BAdW full-tunnel VPN. This has to be done even if you are at the academy.

<!-- todo: add commands -->

Using the default sudo user and password provided by LRZ, ssh into the VM and create a user for yourself
and add it to the sudoer and ssh groups. You also need to create the shared `ebladmin` user.

```sh
adduser ebladmin
usermod -aG sudo ebladmin
usermod -aG ssh-login ebladmin
```

You can then switch to the new user with `su ebladmin`.

#### 2. Set up ssh keys

This step is optional (but you will soon regret it if you skip it): Set
up an ssh key for your user by following these steps
(please find any of the countless online ssh tutorials for more details):

- On your local machine: Either create a new ssh key pair or use an
existing one. Create or edit your .ssh/config file and add the following
contents. You may also need to add a line `IdentityFile ~/.ssh/my_id_rsa`
to each entry if you're using a custom private key name/path.

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

- On the VM: Add the contents of your **public** key file you created locally (e.g., ~/.ssh/id_rsa.pub) to the ~/.ssh/known_hosts file on the VM (create the file if it doesn't exist yet). One way to do this is to open the file (`nano ~/.ssh/knownhosts`)and paste the key contents into it.

If everything is set up correctly you should be able to access each VM by running, e.g., `ssh caic1` from your commandline. The configuration is also automatically discovered by Visual Studio Code and other IDEs, allowing you to connect to the servers from within your IDE.

#### 2. Install Docker

- [Install Docker Engine - Community from Docker's repositories](https://docs.docker.com/install/linux/docker-ce/debian/#install-using-the-repository) (currently installed `Docker version 26.1.4, build 5650f9b`)
- Perform the [post-install steps](https://docs.docker.com/install/linux/linux-postinstall/).
  - Add `ebladmin` and your own user to the `docker` group:

    ```sh
    usermod -aG docker your_user
    usermod -aG docker ebladmin
    ```

  - Copy [daemon.json](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/daemon.json) to `/etc/docker/daemon.json`  to set up log rotation and [metrics](https://docs.docker.com/config/thirdparty/prometheus/) (required by swarmprom). Restart the daemon with `service docker restart`. The log configuration only affects new containers.
  - `sudo service docker status` should show that Docker is active.

#### 3. Set up the firewall

Certain ports need to be opened for Docker to be able to communicate between the VMs.
Docker (Traefik) also opens up ports via iptables that don't show up in the ufw fules
and that don't need to be configured separately. You can find the IP addresses in the
initial e-mail by LRZ.

For each VM, you need to allow traffic to the other two VMs, i.e., for the first VM:

<!-- todo: add third port? -->

```sh
sudo ufw allow proto tcp from <VM2 IP> to any port 2377,7946 comment 'Docker Swarm'
sudo ufw allow proto udp from <VM2 IP> to any port 7946,4789 comment 'Docker Swarm'

sudo ufw allow proto tcp from <VM3 IP> to any port 2377,7946 comment 'Docker Swarm'
sudo ufw allow proto udp from <VM3 IP> to any port 7946,4789 comment 'Docker Swarm'
```

Additionally, for metrics the following port must be opened. This command is identical on all three VMs:

```sh
sudo ufw allow from 172.18.0.0/16 to any port 9323 comment 'Docker Metrics'
```

#### 4. Disable internal sum checking

On Debian 12, Docker Swarm can sometimes fail due to issues with internal sum
checking. What happens is that after setting up the swarm, it is partially functional
(it can ping but cannot transfer any data). In Swarmpit the nodes show up but remain
in a "Loading..." state indefinitely. If such symptoms occur, you need to disable
internal sum checking with:

```sh
ethtool -K ens192 tx-checksum-ip-generic off
```

See [here](https://github.com/swarmpit/swarmpit/issues/688) for more details.

### Docker Swarm Setup

- On the first VM, [create a new swarm](https://docs.docker.com/engine/swarm/swarm-tutorial/create-swarm/)
- On the other VMs, join the swarm. (See the output from creating the swarm or run `docker swarm join-token worker` on the manager.)
- On all VMs add pruning old Docker images to crontab: `0 4 * * * docker image prune -f --filter "until=24h"`.

### Swarm Manager

- On a manager node install [Swarmpit](https://swarmpit.io) with default options:

  ```sh
  docker run -it --rm \
    --name swarmpit-installer \
    --volume /var/run/docker.sock:/var/run/docker.sock \
  swarmpit/install:1.8
  ```

  Swarmpit is now accessible at port 888.
- Login to create a admin user.
- Add placement to the `db` and `influxdb` services so it will have the access to the original volumes (both are currently on `lmkwitg-ebl02`).
- The following steps can be performed via the swarm manager or command line as preferred.

### HTTPS and Monitoring

We use a setup based on [Docker Swarm Rocks](https://dockerswarm.rocks).

#### [Traefik](https://traefik.io/) and [Consul](https://www.consul.io/)

See: [Traefik Proxy with HTTPS](https://dockerswarm.rocks/traefik/)

- Setup the DNS to send `*.cluster.ebabylon.org` to the swarm.
- Create a network `docker network create --driver=overlay traefik-public`.
- Create a config `traefik-config` from [traefik.toml](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/traefik.toml).
- Create a secret `basic_auth_users` containing the basic auth users. A hashed password can be created with `openssl passwd -apr1 <password>`
- Create stack `traefik-consul` from [traefik-consul.yml](https://github.com/ElectronicBabylonianLiterature/infrastructure/tree/master)

#### Swarmpit

Setup Swarpit to use Traefik. See: [Swarmpit web user interface for your Docker Swarm cluster](https://dockerswarm.rocks/swarmpit/).

- Remove ports from stack config.
- Add Traefik network and labels as in [swarmpit.yml](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/swarmpit.yml).

#### [Swarmprom](https://github.com/stefanprodan/swarmprom)

See: [Docker Swarm Rocks Swarmprom for real-time monitoring and alerts](https://dockerswarm.rocks/swarmprom/).

- Create a [webhook](https://api.slack.com/incoming-webhooks) in Slack.
- Create netwrok `docker network create --driver=overlay monitoring`.
- Create the configs:
  - `dockerd_config` from [swarmprom Caddyfile](https://github.com/stefanprodan/swarmprom/blob/master/dockerd-exporter/Caddyfile).
  - `node_rules` from [swarm_node.rules.yml](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/swarm_node.rules.yml).
  - `task_rules` from [swarm_task.rules.yml](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/swarm_task.rules.yml).
- Create stack `swarmprom` from [swarmprom.yml](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/swarmprom.yml). Because [swarmproms Dockerfile](https://github.com/stefanprodan/swarmprom/blob/master/grafana/Dockerfile) defines `GF_SECURITY_ADMIN_PASSWORD` it is not possible to use `GF_SECURITY_ADMIN_PASSWORD__FILE`.
- Import [Traefik dashboard](https://grafana.com/grafana/dashboards/4475) to Grafana.

## Frontend Environment

- Define frontend environment variables directly in [`main.yml`](https://github.com/ElectronicBabylonianLiterature/ebl-frontend/blob/master/.github/workflows/main.yml). [Put](https://github.com/ElectronicBabylonianLiterature/ebl-frontend/settings/secrets/actions) sensitive values to secrets.

## MongoDB

- Create secrets `mongo_admin_user` and `mongo_admin_password` which will be used to create the admin user on the first deploy.
- Create stack `ebl-mongodb` from [mongodb.yml](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/mongodb.yml). Initdb functionality does not work well with SSL, so we enable it in the next step. See: <https://github.com/docker-library/mongo/issues/239> and <https://github.com/docker-library/mongo/issues/172>.

### Replica Set and SSL

See: [Deploy a Replica Set](https://docs.mongodb.com/manual/tutorial/deploy-replica-set/), [Configure mongod and mongos for TLS/SSL](https://docs.mongodb.com/manual/tutorial/configure-ssl/), and [Use x.509 Certificate for Membership Authentication](https://docs.mongodb.com/manual/tutorial/configure-x509-member-authentication/).

- Create certificates for the root CA and all of the servers. See: [MongoDB: Deploy a Replica Set With Transport Encryption: Part 3](https://dzone.com/articles/mongodb-deploy-a-replica-set-with-transport-encryp-1).
- Create secrects `mogoCA.crt`, `ebl01.pem`, and `ebl02.pem` from the respective certificates.
- Redeploy stack with replica set and SSL enabled from [mongodb-replica_set.yml](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/mongodb-replica_set.yml).
- Initiate the replica set. Login to mongo and run (The hosts must have full address, otherwise it is not possible to connect to the replica set from outside the stack):

  ```sh
  rs.initiate( {
     _id : "rs-ebl1",
     members: [
        { _id: 0, host: "lmkwitg-ebl01.srv.mwn.de:27017" },
        { _id: 1, host: "lmkwitg-ebl02.srv.mwn.de:27018" }
     ]
  })
  ```
  
### Monitoring

See: [eses/mongodb_exporter
](https://hub.docker.com/r/eses/mongodb_exporter) and [](https://www.percona.com/doc/percona-monitoring-and-management/section.exporter.mongodb.html).

- Create a user for the exporter.

  ```sh
  db.getSiblingDB("admin").createUser({
      user: "mongodb_exporter",
      pwd: "<password>",
      roles: [
          { role: "clusterMonitor", db: "admin" },
          { role: "read", db: "local" }
      ]
  })
  ```

- Update the `swarmprom` stack:
  - Add `mongodb-exporter` service:

    ```yml
      mongodb-exporter:
        image: bitnami/mongodb-exporter
        command:
         - --mongodb.direct-connect=false
         - --mongodb.uri=mongodb://<user>:<passwordd>@lmkwitg-ebl01.srv.mwn.de:27017,lmkwitg-ebl02.srv.mwn.de:27018/?tls=true&tlsCAFile=/run/secrets/mongoCA.crt
        secrets:
         - mongoCA.crt
        networks:
         - net
        deploy:
          resources:
            reservations:
              memory: 64M
            limits:
              memory: 128M
    ```

  - Add `mongodb-exporter` job to `prometheus`:

    ```yml
          JOBS: traefik:8080 mongodb-exporter:9104
    ```

  - Add `mongoCA.crt` to `secrets`.
- Import [MongoDB dashboard](https://grafana.com/grafana/dashboards/2583) to Grafana.
- Edit dashboard JSON and change metric prefix from `mongodb_` to `mongodb_mongod_`.

## Docker registry

Create configs `registry_config` and `docker-registry-ui_config` from [registry_config.yml](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/registry_config.yml) [docker-registry-ui_config](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/docker-registry-ui_config.yml).

Create secrets:

- `httpass` bcrypt encrypted httpasswd file with users for the registry.
- `registry_htpasswd` password of the regisry user used by the registry UI.

Create stack from [registry.yml](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/registry.yml).

## eBL application

Create stack from [ebl.yml](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/ebl.yml). The Docker images should be in the registry before deploying the stack.
[Ai-api](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/ebl.yml) service is optional and could be left out. The **EBL_AI_API** environment variable on the [api](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/ebl.yml) has to be present.
The **ebl-ai-api repository** is [here](https://github.com/ElectronicBabylonianLiterature/ebl-ai-api).

- Update the `swarmprom` stack:
  - Add `redis-exporter` service:

    ```yml
    redis-exporter:
      image: bitnami/redis-exporter:1
      environment:
        REDIS_ADDR: redis://redis:6379
      networks:
       - net
       - monitoring
    ```

  - Add `redis-exporter` job to `prometheus`:

    ```yml
          JOBS: traefik:8080 mongodb-exporter:9216 redis-exporter:9121
    ```

## Troubleshooting

### Consul fails to elect a leader

- Scale replicas to 0.
- Scale replica back to desired value.

When the new replicas join Consul should clean up old nodes and elect a new leader. To avoid stale nodes in the config the replicas should be shut down before the leader.

### Redeployment fails

Long commands (e.g. `node-exporter`) get messed up and `$` is unescaped in the "Current engine state". If you have to redeploy a service/stack edit the "Last deploeyd instead" or copy the correct values this repository.

### Forgotten Grafana password

The Grafana admin password is set up only on first run. It can be resetted later vie the CLI `docker exec -ti <container id> grafana-cli admin reset-admin-password <new password>`.

### "invalid memory address or nil pointer dereference" from mongodb_exporter

There is a bug in the exporter ([PMM-4375](https://jira.percona.com/browse/PMM-4375)). We should update it as soon as the fix is released. The exporter has been updated.

### The cluster becomes unresponsive

Docker can be restarted from the commandline by running `sudo service docker restart` in all the affected instances. If it is not possible to connect with SSH, ask ITG to reboot/investigate.

### Low diskspace

Diskspace can be freed by removing old Docker images etc. See: <https://stackoverflow.com/questions/32723111/how-to-remove-old-and-unused-docker-images/32723127#32723127>

### Expired certificate

The certificates are handled automatically by [Let's Encrypt](https://letsencrypt.org/) and `certbot` (managed in the Traefik configuration, cf.
the [Traefik docs](https://doc.traefik.io/traefik/v1.7/configuration/acme/)).
In case if fails the website becomes unavailable via https once the certificate expires. It might be necessary to manually restart the
`traefik-consul_traefik` service in swarmpit or via the server.
