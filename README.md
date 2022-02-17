# Electronic Babylonian Literature Infrastructure

The Electronic Babylonian Literature application is hosted on Heroku and the database on Docker Swarm in LRZ.

## LRZ Server Setup

Each server needs to part of the Docker Swarm.

- [Install Docker Engine - Community from Docker's repositories](https://docs.docker.com/install/linux/docker-ce/debian/#install-using-the-repository) (currently installed `Docker version 19.03.1, build 74b1e89`)
- Perform [post-install steps](https://docs.docker.com/install/linux/linux-postinstall/).
  - Add `ebladmin` to `docker` group. (The group should be already created by install process.)
  - Copy [daemon.json](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/daemon.json) to `/etc/docker/daemon.json`  to set up log rotation and [metrics](https://docs.docker.com/config/thirdparty/prometheus/) (The metrics are required by swarmprom.). If the daemon is already running, it needs to be restarted: `service docker restart`. The log configuration only affects new containers.
  - Configure Docker to start on boot. Check status `sudo service docker status`
- Configure the firewall. (Published ports are opened automatically by Docker with iptables and not appear in ufw rules.)
  - Allow connections from all other nodes:
    ```
    sudo ufw allow proto tcp from <node IP> to any port 2377,7946 comment 'Docker Swarm'
    sudo ufw allow proto udp from <node IP> to any port 7946,4789 comment 'Docker Swarm'
    ```
  - Allow metrics:
    ```
    sudo ufw allow from 172.18.0.0/16 to any port 9323 comment 'Docker Metrics'
    ```
- On the first VM, [create a new swarm](https://docs.docker.com/engine/swarm/swarm-tutorial/create-swarm/)
- On the other VMs, join the swarm. (See the output from creating the swarm or run `docker swarm join-token worker` on the manager.)
- On all VMs add pruning old Docker images to crontab: `0 4 * * * docker image prune -f --filter "until=24h"`.

## Docker Swarm Setup

### Swarm Manager

- On a manager node install [Swarmpit](https://swarmpit.io) with default options:
  ```
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
- Create a config `traefik-config-v2` from [traefik.toml](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/traefik.toml).
- Create a secret `basic_auth_users_v2` containing the basic auth users. A hashed password can be created with `openssl passwd -apr1 <password>`
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

## MongoDB

- Create secrets `mongo_admin_user` and `mongo_admin_password` which will be used to create the admin user on the first deploy.
- Create stack `ebl-mongodb` from [mongodb.yml](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/mongodb.yml). Initdb functionality does not work well with SSL, so we enable it in the next step. See: https://github.com/docker-library/mongo/issues/239 and https://github.com/docker-library/mongo/issues/172.

### Replica Set and SSL

See: [Deploy a Replica Set](https://docs.mongodb.com/manual/tutorial/deploy-replica-set/), [Configure mongod and mongos for TLS/SSL](https://docs.mongodb.com/manual/tutorial/configure-ssl/), and [Use x.509 Certificate for Membership Authentication](https://docs.mongodb.com/manual/tutorial/configure-x509-member-authentication/).

- Create certificates for the root CA and all of the servers. See: [MongoDB: Deploy a Replica Set With Transport Encryption: Part 3](https://dzone.com/articles/mongodb-deploy-a-replica-set-with-transport-encryp-1).
- Create secrects `mogoCA.crt`, `ebl01.pem`, and `ebl02.pem` from the respective certificates.
- Redeploy stack with replica set and SSL enabled from [mongodb-replica_set.yml](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/mongodb-replica_set.yml).
- Initiate the replica set. Login to mongo and run (The hosts must have full address, otherwise it is not possible to connect to the replica set from outside the stack):
  ```
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
  ```
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
    ```
      mongodb-exporter:
        image: eses/mongodb_exporter
        secrets:
         - mongoCA.crt
        command: '-mongodb.tls -mongodb.uri mongodb://mongodb_exporter:<password>@lmkwitg-ebl01.srv.mwn.de:27017,lmkwitg-ebl02.srv.mwn.de:27018 -mongodb.tls-ca /run/secrets/mongoCA.crt'
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
    ```
          JOBS: traefik:8080 mongodb-exporter:9104
    ```
  - Add `mongoCA.crt` to `secrets`.
- Import [MongoDB dashboard](https://grafana.com/grafana/dashboards/2583) to Grafana.
- Edit dashboard JSON and change metric prefix from `mongodb_` to `mongodb_mongod_`.

## Docker registry

Create configs `registry_config` and `docker-registry-ui_config` from [registry_config.yml](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/registry_config.yml) [docker-registry-ui_config](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/docker-registry-ui_config.yml). 

Create secrets:

* `httpass` bcrypt encrypted httpasswd file with users for the registry.
* `registry_htpasswd` password of the regisry user used by the registry UI.

Create stack from [registry.yml](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/registry.yml).

## eBL application

Create stack from [ebl.yml](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/ebl.yml). The Docker images should be in the registry before deploying the stack.
[Ai-api](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/ebl.yml) service is optional and could be left out. The **EBL_AI_API** environment variable on the [api](https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/ebl.yml) has to be present.
The **ebl-ai-api repository** is [here](https://github.com/ElectronicBabylonianLiterature/ebl-ai-api).

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

Diskspace can be freed by removing old Docker images etc. See: https://stackoverflow.com/questions/32723111/how-to-remove-old-and-unused-docker-images/32723127#32723127
