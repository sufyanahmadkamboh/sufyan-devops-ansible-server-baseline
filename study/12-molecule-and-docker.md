# 12. Molecule and Docker

## What is it?

- **Docker** runs programs in **containers**: isolated processes with their own filesystem, started from an **image**. Here, containers play the role of servers.
- **Molecule** is the testing framework for Ansible. It creates throwaway machines, applies your roles, runs them a second time to prove idempotence, runs your checks, and deletes the machines.

## Why this project uses them

A hardening change that works on Ubuntu can break on Debian (different package names, different SSH start-up, a file that doesn't exist). Molecule tests **every role on three distributions** on every change, at no cloud cost:

| Platform | Image |
|---|---|
| Ubuntu 24.04 | `geerlingguy/docker-ubuntu2404-ansible` |
| Debian 12 | `geerlingguy/docker-debian12-ansible` |
| Debian 13 | `geerlingguy/docker-debian13-ansible` |

These images are widely used for Ansible testing because they start **systemd** inside the container, so services and timers behave like on a real server.

**Alternatives:** Vagrant with virtual machines (closer to reality, much slower), cloud VMs (real, but cost money and time), Testinfra or Goss for the checks. Docker is fast and free; the parts containers cannot test (auditd, global kernel settings) are covered by the CI `vm` job instead.

## How it works: the scenario lifecycle

[`molecule/default/molecule.yml`](../molecule/default/molecule.yml) defines the test sequence:

```yaml
scenario:
  test_sequence:
    - destroy        # remove leftovers from an earlier run
    - syntax         # ansible-playbook --syntax-check
    - create         # start the three containers
    - converge       # apply the baseline (molecule/default/converge.yml → playbooks/site.yml)
    - idempotence    # apply again: ANY "changed" task fails the test
    - verify         # molecule/default/verify.yml → playbooks/verify.yml
    - destroy
```

`converge.yml` and `verify.yml` simply import the real playbooks, so **Molecule tests exactly what production runs**:

```yaml
- name: Apply the baseline
  ansible.builtin.import_playbook: ../../playbooks/site.yml
```

### Why the containers are privileged
```yaml
    privileged: true
    cgroupns_mode: host
    volumes:
      - /sys/fs/cgroup:/sys/fs/cgroup:rw
    command: ""          # keep the image's default start command: systemd
```
systemd needs access to the host's control groups (cgroups) to manage services, and the firewall needs to create nftables rules in the container's network namespace. **Privileged containers are a test-lab pattern, not a production one:** they have almost all of the host's capabilities.

### Test data without secrets
The admin key in `molecule.yml` is a real public key whose private half was thrown away when it was created. It only has to exist, because the lockout guard requires an admin with a key; nobody logs in with it. Molecule connects with `docker exec`, not SSH.

### `serial` in Molecule
`site.yml` hardens one server at a time. Molecule runs all three at once by passing an extra variable, because `serial` is a play keyword that cannot come from the inventory:
```yaml
  options:
    extra-vars: baseline_serial=0
```

## The lab is Docker too

The lab ([`lab/compose.yaml`](../lab/compose.yaml)) uses the same idea, but over **real SSH**:

| Container | Address | Role |
|---|---|---|
| `controller` | 172.30.0.5 | Ansible + tools, SSH key in a Docker volume |
| `web-01` | 172.30.0.21 | Ubuntu 24.04 server, distribution defaults ([`lab/target/Dockerfile`](../lab/target/Dockerfile)) |
| `db-01` | 172.30.0.22 | Debian 12 server |
| `attacker` | 172.30.0.66 | brute force and port probes in the tests |
| `prometheus` | 172.30.0.10 | the only address allowed to reach port 9100 |
| `grafana` | 172.30.0.11 | dashboard on `localhost:3000` |

Each server generates its **own SSH host keys at first boot** (a drop-in for `ssh.service`, `lab/target/ssh-hostkeys.conf`, runs `ssh-keygen -A` just before sshd starts), because keys baked into an image would be identical on every container. A first version used a separate unit and lost a race against Ubuntu's early `ssh.socket`. The story is in `docs/troubleshooting.md`.

## Try it

```bash
make molecule                     # the full test sequence; or step by step:
MSYS_NO_PATHCONV=1 docker run --rm -it -v "$PWD:/work" -v /var/run/docker.sock:/var/run/docker.sock \
  server-baseline-controller:dev bash
#   inside: molecule create; molecule converge; molecule idempotence; molecule verify
#           molecule login -h debian12      # a shell in one test container
#           molecule destroy
```

## Common mistakes

- **Testing only `converge`.** The idempotence step finds the bugs that make re-runs noisy and drift checks useless.
- **Starting the container with `bash` as command** instead of systemd: every service task fails.
- **Expecting everything to work in containers:** auditd and global kernel settings need a VM.
- **Editing a role while Molecule runs:** role defaults are read at play start, so a mid-run change gives confusing errors.

## Check yourself

1. Which Molecule step fails if a task reports "changed" every time?
2. Why do `converge.yml` and `verify.yml` import `playbooks/site.yml` and `playbooks/verify.yml` instead of having their own tasks?
3. Name two things this project cannot test in containers, and where they are tested instead.

<details><summary>Answers</summary>

1. **idempotence**: it runs the playbook a second time and fails on any changed task.
2. So the test runs exactly the code production runs. Separate test playbooks could pass while the real one is broken.
3. auditd (kernel audit is host-wide) and global kernel settings (`kernel.*`, `fs.*`). Both are tested by the CI `vm` job on a real GitHub runner VM.
</details>

Next: [13. GitHub Actions](13-github-actions.md)
