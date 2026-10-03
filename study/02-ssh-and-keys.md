# 2. SSH and keys

## What is it?

**SSH** (Secure Shell) is how you log in to a remote Linux server and run commands over an encrypted connection. The program on the server is **sshd** (the SSH daemon); the program you type into is `ssh`.

SSH supports several ways to prove who you are. The two that matter:
- **Password:** you type a secret the server also knows (as a hash).
- **Public key:** you hold a **private key** file; the server holds the matching **public key** in `~/.ssh/authorized_keys`.

## Why this project uses it (and hardens it)

SSH is the front door. It is also how **Ansible** reaches every server, so the hardening must make the door strong **without locking Ansible out**.

| Default on Debian/Ubuntu | After the baseline | Why |
|---|---|---|
| Password login allowed | **Keys only** (`AuthenticationMethods publickey`) | Passwords can be guessed; a 256-bit key cannot |
| `root` may log in with a key | **No root login** at all | Admins log in as themselves and use sudo, so every action has a name |
| Every user may log in | **Only the `ssh-users` group** | A service account with a weak setting cannot become a way in |
| 6 tries per connection | **3 tries**, 30 s to log in | Slows down guessing |
| Tunnels and forwarding allowed | **Off** | A login is a shell, not a path into the internal network |
| Older algorithms allowed | **Modern ciphers, key exchanges and MACs only** | No CBC ciphers, no SHA-1 MACs |

The lab's end-to-end test proves this from the outside: before hardening the server offers `publickey,password`; after, it offers only `publickey`, a correct password is rejected, and even a **valid key copied into root's account is rejected**.

**Alternatives:** a VPN or bastion host in front of SSH, short-lived SSH certificates (for example from HashiCorp Vault or Teleport), or no SSH at all with a cloud session manager (AWS SSM). Those add infrastructure; key-only SSH with fail2ban is the baseline every server needs anyway.

## How key login works

```
your laptop / controller                        server
private key  (never leaves)                     ~/.ssh/authorized_keys: public key
      │  1. "I want to log in as ops with this public key"  ──►
      │  ◄── 2. "prove it: sign this random challenge"
      │  3. signature made with the PRIVATE key ──►
      │                                         4. checks the signature with the PUBLIC key → OK
```
The private key is never sent. A stolen `authorized_keys` file is useless to an attacker.

### sshd_config, drop-ins and "first value wins"

sshd reads `/etc/ssh/sshd_config`. Modern versions start with:
```
Include /etc/ssh/sshd_config.d/*.conf
```
Files in that folder are read **in alphabetical order**, and for most settings **the first value sshd reads wins**. That is why the baseline's file is called `00-server-baseline.conf`: it is read before anything else, including `50-cloud-init.conf` that cloud images ship with `PasswordAuthentication yes`.

### `sshd -t` and `sshd -T`
- `sshd -t` **tests** a configuration and fails on any error. A broken config plus a restart can mean **nobody can log in again**.
- `sshd -T` prints the **effective** settings after reading every file. This is the only reliable answer to "is password login really off?"

### Ubuntu 24.04: socket activation
On Ubuntu 24.04, sshd is started on demand by `ssh.socket`. Debian runs `ssh.service` all the time. The baseline switches Ubuntu to the classic always-running `ssh.service`, so both distributions behave the same and the port lives in one place.

## Where it is integrated

[`roles/ssh_hardening/templates/sshd-baseline.conf.j2`](../roles/ssh_hardening/templates/sshd-baseline.conf.j2) (excerpt):

```
AllowGroups {{ ssh_hardening_allow_groups | join(' ') }}
PermitRootLogin no
PubkeyAuthentication yes
AuthenticationMethods publickey
PasswordAuthentication no
KbdInteractiveAuthentication no
MaxAuthTries {{ ssh_hardening_max_auth_tries }}
AllowTcpForwarding no
KexAlgorithms {{ ssh_hardening_kex_algorithms | join(',') }}
```

[`roles/ssh_hardening/tasks/main.yml`](../roles/ssh_hardening/tasks/main.yml) installs it **only if sshd accepts it**, and reloads sshd through a handler:

```yaml
- name: Install the hardened SSH settings
  ansible.builtin.template:
    src: sshd-baseline.conf.j2
    dest: /etc/ssh/sshd_config.d/00-server-baseline.conf
    mode: "0600"
    validate: /usr/sbin/sshd -t -f %s
  notify: Reload sshd
```

Two **lockout guards** run before that:
- The `common` role refuses to continue if `common_admin_users` is empty or a user has no key.
- The `ssh_hardening` role refuses to restrict SSH to groups that have no members.

The role also removes weak Diffie-Hellman groups (smaller than 3071 bits) from `/etc/ssh/moduli`.

The verification ([`roles/ssh_hardening/tasks/verify.yml`](../roles/ssh_hardening/tasks/verify.yml)) reads `sshd -T` and asserts each setting, for example:

```yaml
      - ssh_hardening_settings.passwordauthentication == 'no'
      - ssh_hardening_settings.permitrootlogin == 'no'
      - "'cbc' not in ssh_hardening_settings.ciphers"
```

## Try it

```bash
# Which login methods does web-01 offer to a stranger? (from the attacker container)
docker compose -f lab/compose.yaml exec attacker \
  ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o PreferredAuthentications=none probe@web-01
# before hardening: Permission denied (publickey,password).   after: Permission denied (publickey).

# The effective settings, straight from sshd
docker compose -f lab/compose.yaml exec web-01 sh -c "sshd -T | grep -E 'passwordauth|permitrootlogin|allowgroups|maxauthtries'"

# Ansible's own key login (from the controller)
docker compose -f lab/compose.yaml exec controller ssh -i /keys/id_ed25519 -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/keys/known_hosts ops@web-01 hostname
```

## Common mistakes

- **Restarting sshd with an untested config.** Always `sshd -t` first; the role does it with `validate:`.
- **Editing `sshd_config` and wondering why nothing changed:** an earlier drop-in already set the value. Check with `sshd -T`.
- **Disabling password login before a key works.** The lockout guards exist for exactly this.
- **Closing your only session** after changing SSH. Keep one session open and test with a second one.
- **Copying the private key to servers.** Only the public key goes onto servers.

## Check yourself

1. Why is the baseline file named `00-server-baseline.conf` and not `99-...`?
2. What is the difference between `sshd -t` and `sshd -T`?
3. An attacker steals a server's `authorized_keys`. Can they log in?
4. Why is root login disabled even with keys?

<details><summary>Answers</summary>

1. For most settings sshd uses **the first value it reads**. `00-` is read first, so other drop-ins (like `50-cloud-init.conf`) cannot override it.
2. `-t` **tests** the configuration for errors; `-T` prints the **effective** settings after all files are combined.
3. **No.** It contains only public keys. Logging in needs the private key, which never leaves the admin's machine.
4. So every action is done by a named person through sudo (and logged), and because `root` is the one account name every attacker knows.
</details>

Next: [3. Ansible](03-ansible.md)
