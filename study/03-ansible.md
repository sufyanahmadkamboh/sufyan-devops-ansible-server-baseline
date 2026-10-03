# 3. Ansible

## What is it?

**Ansible** is a tool that configures computers from a description written in YAML. You describe the **desired state** ("package fail2ban is installed", "this file has this content", "this service is running"), and Ansible connects to each server over **SSH**, compares, and changes only what differs.

It is **agentless**: nothing needs to be installed on the servers except SSH and Python.

## Why this project uses it

Hardening is a long list of small settings that must be **identical on every server** and **stay that way**. Ansible gives:
- **Repeatability:** the same playbook produces the same server every time.
- **Idempotence:** running it again changes nothing if nothing drifted. That makes the playbook double as a **drift check**.
- **Review:** the security baseline is code in Git, reviewed in pull requests and tested in CI.

**Alternatives:**
- **Shell scripts:** quick, but not idempotent without a lot of care, and hard to test.
- **Chef / Puppet / Salt:** need an agent or server on each machine.
- **Golden images (Packer):** good for new servers, but don't fix drift on running ones. Many teams combine Packer *and* Ansible.
- **CIS benchmark roles (e.g. ansible-lockdown):** very complete, but hundreds of controls. This project builds a smaller baseline you can read in an afternoon, and measures it with Lynis.

## How it works: the vocabulary

| Term | Meaning | In this repo |
|---|---|---|
| **Control node** | The machine that runs Ansible | The `controller` container ([`lab/controller/Dockerfile`](../lab/controller/Dockerfile)) |
| **Inventory** | The list of servers, in groups, with variables | [`inventories/lab/hosts.yml`](../inventories/lab/hosts.yml): group `baseline` with web-01 and db-01 |
| **Playbook** | A YAML file with one or more **plays**: "on these hosts, do this" | [`playbooks/site.yml`](../playbooks/site.yml), [`verify.yml`](../playbooks/verify.yml), [`audit.yml`](../playbooks/audit.yml) |
| **Task** | One step, calling one **module** (`apt`, `template`, `user`, `systemd_service`, ...) | Every file in `roles/*/tasks/` |
| **Role** | A folder of tasks, defaults, templates, handlers for one job | 9 roles in [`roles/`](../roles/) |
| **Variables / defaults** | Values tasks use. `defaults/main.yml` = lowest priority, easy to override | `roles/*/defaults/main.yml`, overridden in `inventories/lab/group_vars/baseline.yml` |
| **Facts** | Information Ansible collects about each server first (OS, CPU, virtualization) | `ansible_facts['distribution']`, `ansible_facts['virtualization_type']` |
| **Template** | A file with `{{ variables }}` and `{% loops %}` (Jinja2) | `roles/*/templates/*.j2` |
| **Handler** | A task that runs **only if notified** by a task that changed something, once, at the end | `Reload sshd`, `Reload firewall`, `Restart fail2ban` |
| **Tags** | Labels to run only part of a playbook | `--tags ssh`, `--tags firewall` |

### The playbook of this project

From [`playbooks/site.yml`](../playbooks/site.yml):

```yaml
- name: Apply the server baseline
  hosts: baseline
  become: true
  # One server at a time: a mistake stops after the first server instead of all of them.
  serial: "{{ baseline_serial | default(1) }}"
  max_fail_percentage: 0

  roles:
    - role: common
      tags: [common]
    - role: kernel_hardening
      tags: [kernel]
    - role: ssh_hardening
      tags: [ssh]
    ...
```

- `become: true` = use sudo on the server.
- `serial: 1` = a **rolling** change: one server at a time. With `max_fail_percentage: 0`, the first failure stops the whole run, so a bad change breaks one server, not the fleet.
- At the end, `post_tasks` run `meta: reset_connection` and `wait_for_connection`: a **brand-new SSH connection** proves that SSH and the firewall still let the admin in.

### Idempotence: "changed" must mean something

Ansible reports every task as `ok` (already right), `changed` (fixed now), `skipped` or `failed`. The rule in this project: **a second run must report 0 changes**. The Molecule test, the lab end-to-end test and the CI VM test all check it.

Modules like `template` and `apt` are idempotent on their own. Raw commands are not, so the project writes them carefully. From [`roles/kernel_hardening/tasks/main.yml`](../roles/kernel_hardening/tasks/main.yml), read first, then write only what differs:

```yaml
- name: Read the running kernel values
  ansible.builtin.command: sysctl -n {{ item.key }}
  register: kernel_hardening_current
  changed_when: false        # reading never "changes" anything
  check_mode: false          # also read during --check

- name: Apply kernel values that differ
  ansible.builtin.command: sysctl -w {{ item.item.key }}={{ item.item.value }}
  when: item.stdout | trim != item.item.value | string
```

### Check mode and diff mode: the drift check

`ansible-playbook --check --diff` **pretends**: modules report what they *would* change and show a diff, but change nothing. [`scripts/drift-check.sh`](../scripts/drift-check.sh) uses this: exit 0 means every server matches the baseline; exit 2 means drift, with the diff showing what and where. It lists the *tasks* that would change (`server | task`) and does not count the handlers they would trigger: one drifted SSH setting also "changes" the `Reload sshd` handler, but that is a consequence, not a second drift.

### `validate:`: never install a broken file

Several templates have a `validate:` command. Ansible writes the new file to a temporary path, runs the command with `%s` replaced by that path, and **only installs the file if the command succeeds**:

| File | Validated with |
|---|---|
| `/etc/sudoers.d/90-server-baseline` | `visudo -cf %s` |
| `/etc/ssh/sshd_config.d/00-server-baseline.conf` | `sshd -t -f %s` |
| `/etc/nftables.d/server-baseline.nft` | `nft -c -f %s` |

### Verification as code

Each role also has `tasks/verify.yml`, and [`playbooks/verify.yml`](../playbooks/verify.yml) runs them all with `include_role ... tasks_from: verify.yml`. The same checks run in Molecule, in the lab test and on the CI VM.

### Why Ansible runs in a container here

The `controller` image pins `ansible-core 2.21.4`, `ansible-lint`, `molecule`, the collections (`ansible.posix`, `community.general`, `community.docker`) and the Docker CLI ([`requirements.txt`](../requirements.txt), [`requirements.yml`](../requirements.yml)). Everyone, and CI, runs the same versions. Ansible's control node also does not run natively on Windows.

## Try it

```bash
make lab-up
docker compose -f lab/compose.yaml exec controller ansible baseline -m ansible.builtin.ping
docker compose -f lab/compose.yaml exec controller ansible web-01 -m ansible.builtin.setup -a 'filter=ansible_distribution*'
make harden                         # first run: many "changed"
make harden                         # second run: changed=0 on both servers
scripts/harden.sh --limit web-01 --tags ssh      # only one role, one server
make drift                          # check mode: what differs? (nothing)
```

## Common mistakes

- **Using `command`/`shell` for everything:** it always reports "changed" and breaks idempotence. Use a module, or set `changed_when` honestly.
- **Restarting services in every run:** use handlers, which run only when something changed.
- **Putting secrets in variables in Git:** this project generates the SSH key at runtime in a Docker volume, never in the repo.
- **Inventory variables for play keywords:** `serial` is evaluated before hosts exist, so it cannot come from `group_vars`; Molecule passes it as an extra var.
- **Testing only the first run.** The second run is where bugs in idempotence show up.

## Check yourself

1. What is the difference between a task and a handler?
2. Why does `site.yml` use `serial: 1` with `max_fail_percentage: 0`?
3. What does `--check --diff` do, and how does this project use it?
4. Why do the "read" tasks have `check_mode: false`?

<details><summary>Answers</summary>

1. A task always runs. A handler runs **only if a task notified it and that task changed something**, and only once, after the tasks (or at `flush_handlers`).
2. To roll the change out one server at a time and stop at the first failure, so a mistake affects one server instead of all of them.
3. It runs the playbook without changing anything and shows what would change. `scripts/drift-check.sh` uses it to detect drift: 0 changes means "matches the baseline".
4. In check mode, `command` tasks are normally skipped. A read-only command must still run, otherwise the next tasks have no data to compare and the drift check would miss differences.
</details>

Next: [4. Firewall with nftables](04-firewall-nftables.md)
