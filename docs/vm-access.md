# Accessing the eBL production VMs

> **Last verified:** read-only SSH access on all three VMs, 19 November 2026. Use an approved individual account and the BAdW full-tunnel VPN. Credentials, personal keys and private access-control configuration must not be committed or shared in the public repository.

## Connect over SSH

For host-level administration (Docker, filesystem, networking or recovery), use an **approved personal VM account** and connect to the **BAdW full-tunnel VPN** before SSH. This VPN is also required for access from networks where the VMs are otherwise unreachable; the original deployment required it even on the academy network. Do not rely on the public eBL website URL for SSH access.

| SSH alias | VM hostname | IP address | Role |
| --- | --- | --- | --- |
| `caic1` | `badwcai-ebl01` | `138.246.225.199` | Docker Swarm manager / production ingress |
| `caic2` | `badwcai-ebl02` | `138.246.225.201` | Swarm node |
| `caic3` | `badwcai-ebl03` | `138.246.225.202` | Swarm node |

From Windows PowerShell, macOS Terminal or a Linux shell, use OpenSSH. Substitute the username of your **existing authorized VM account**:

```sh
ssh <your-vm-username>@138.246.225.199
ssh <your-vm-username>@138.246.225.201
ssh <your-vm-username>@138.246.225.202
```

**Name resolution:** The short hostname `badwcai-ebl01` may not resolve on a Windows workstation (`Could not resolve hostname`). Use the IP above or a locally configured SSH alias instead. The full internal DNS names are `badwcai-ebl01.srv.mwn.de`, `badwcai-ebl02.srv.mwn.de` and `badwcai-ebl03.srv.mwn.de`, but do not assume your workstation's DNS can resolve them. The IP-based connection to VM1 was verified from Windows during the Traefik migration. Confirm changes to VM addresses with the system administrators rather than guessing.

For a one-line file transfer from **Windows PowerShell**:

```powershell
scp "$env:USERPROFILE\Downloads\example.txt" "<your-vm-username>@138.246.225.199:/home/<your-vm-username>/"
```

Use a single line in PowerShell; a trailing Linux-style backslash is **not** a PowerShell continuation character. When a transfer fails, first confirm that SSH works with the same VPN connection, destination IP and account. Use an SSH key where authorized and do not share private keys or account passwords. The optional `caic1`/`caic2`/`caic3` aliases are documented in [SSH key setup](#ssh-aliases-and-public-key-authentication).

Grafana, Traefik and registry administrative UIs are available to authorized maintainers. Their current authentication and end-to-end access behavior were **not** tested in this inventory; do not assume a link proves access.

**Network boundary:** MongoDB publishes 27017–27019/tcp, registry 5000/tcp and registry UI 8000/tcp through Swarm ingress. Docker metrics listen on port 9323 on all VM interfaces. These observations **do not prove Internet exposure**; UFW inspection failed or lacked permission on every VM, and LRZ perimeter filtering remains unverified. See the [verification ledger](production-inventory-2026-11-19.md#verification-ledger).



## SSH aliases and public-key authentication

Aliases such as `caic1` are **local OpenSSH configuration**, not network DNS names. On Windows, edit `$env:USERPROFILE\.ssh\config`; on macOS/Linux edit `~/.ssh/config`. Replace the placeholder username with your approved VM account:

```sshconfig
Host caic1
  HostName 138.246.225.199
  User your_vm_username

Host caic2
  HostName 138.246.225.201
  User your_vm_username

Host caic3
  HostName 138.246.225.202
  User your_vm_username
```

After saving the file, use `ssh caic1`, `ssh caic2`, or `ssh caic3` while on the VPN. When authorized, use SSH **public-key** authentication; keep your private key local, set appropriate permissions for your own `~/.ssh/authorized_keys`, and do not overwrite existing keys. This repository does not provision or manage accounts. The former setup discussion is preserved in [historical provisioning](historical-provisioning.md#422-set-up-ssh-keys).

For cluster-wide Swarm inspection, connect to VM1 (the only manager). VM2 and VM3 are workers. See [day-to-day operations](day-to-day-operations.md#routine-read-only-inspection).
