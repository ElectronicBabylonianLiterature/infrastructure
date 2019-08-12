# Electronic Babylonian Literature Infrastructure

## LRZ Server Setup

Each server needs to part of the Docker Swarm.

- [Install Docker Engine - Community from Docker's repositories](https://docs.docker.com/install/linux/docker-ce/debian/#install-using-the-repository) (currently installed `Docker version 19.03.1, build 74b1e89`)
- Perform [post-install steps](https://docs.docker.com/install/linux/linux-postinstall/).
  - Add `ebladmin` to `docker` group. (The group should be already created by install process.)
  - Create `/etc/docker/daemon.json` (https://github.com/ElectronicBabylonianLiterature/infrastructure/blob/master/daemon.json) to set up log rotation and [metrics](https://docs.docker.com/config/thirdparty/prometheus/) (required by swarmprom). If the daemon is already running, it needs to be restarted: `service docker restart`. The log configuration only affects new containers.
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

