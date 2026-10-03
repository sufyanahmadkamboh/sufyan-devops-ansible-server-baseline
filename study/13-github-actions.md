# 13. GitHub Actions

## What is it?

**GitHub Actions** is GitHub's built-in automation. A **workflow** file in `.github/workflows/` says *when* to run (on push, on pull request, by hand) and *what* to run: **jobs** made of **steps**, each job on a fresh virtual machine called a **runner**.

## Why this project uses it

Every change to a security baseline must be proven not to break servers. CI runs **all** tests on every push and pull request, so a mistake is caught before anyone applies it.

**Alternatives:** GitLab CI, Jenkins, CircleCI. GitHub Actions is built into the place where the code lives and is free for public repositories.

## How it works: the four jobs

[`.github/workflows/ci.yaml`](../.github/workflows/ci.yaml):

```
            ┌──────────► molecule  (3 distros: converge, idempotence, verify)
 static ────┼──────────► lab-e2e   (scripts/e2e.sh: real SSH, attacks, drift, monitoring)
            └──────────► vm        (scripts/vm-test.sh: harden the runner VM itself)
```

| Job | What it runs | Why |
|---|---|---|
| **static** | `scripts/lint.sh` (yamllint, ansible-lint production profile, syntax check, ShellCheck, pytest), `promtool check config` + `promtool test rules`, `docker compose config`, JSON check of the dashboard | Fast feedback; the other jobs only start if it passes (`needs: static`) |
| **molecule** | `molecule test` | Roles work and are idempotent on Ubuntu 24.04, Debian 12, Debian 13 |
| **lab-e2e** | `scripts/e2e.sh` | The full story over real SSH: before/after Lynis, idempotence, access tests, brute force, drift, safety nets, metrics. Uploads `reports/` as an artifact |
| **vm** | `scripts/vm-test.sh` | auditd and **every** kernel setting on a real kernel; Lynis before/after on a VM |

### The VM job: hardening the runner
A GitHub runner is a **throwaway virtual machine**, deleted after the job. That makes it a free, real Linux VM to test what containers cannot. [`scripts/vm-test.sh`](../scripts/vm-test.sh) applies the baseline to `localhost` with [`inventories/local/hosts.yml`](../inventories/local/hosts.yml) (`ansible_connection: local`), checks idempotence, runs the verify playbook, proves auditd records a change, and writes the results to the job summary.

Because it hardens the machine it runs on, the script refuses to run outside CI unless you pass `--yes-harden-this-machine`. The admin key it needs is generated per run and deleted afterwards.

### Details worth knowing
- `permissions: contents: read`: the workflow token can only read the repository (least privilege).
- `concurrency: cancel-in-progress`: a new push cancels the old run of the same branch.
- Tools are installed from the **pinned** [`requirements.txt`](../requirements.txt) and [`requirements.yml`](../requirements.yml), the same versions as the local controller image.
- `if: always()` on the report upload and `make lab-down` steps: they run even when the test failed, which is exactly when you need the logs.

## Try it

Run the same checks locally:
```bash
make lint          # static checks inside the controller image
make promtool
make molecule
make e2e           # builds a fresh lab and runs the full end-to-end test
```
On GitHub: open the repository's **Actions** tab, pick a run, and open the **Summary**: the e2e and VM jobs write their results there.

## Common mistakes

- **CI that only lints.** Linting proves the YAML is valid, not that SSH still lets you in.
- **Different tool versions locally and in CI.** Pin them in one place.
- **Running a "harden this machine" script on your laptop.** The guard flag exists for this.
- **Not keeping logs of failed runs:** upload artifacts with `if: always()`.

## Check yourself

1. Why do the molecule, lab-e2e and vm jobs have `needs: static`?
2. Why is it safe to harden the CI runner, but not your laptop?
3. Which job proves that auditd really records events?

<details><summary>Answers</summary>

1. So a simple lint error fails fast and cheaply, without starting the long jobs.
2. The runner is a throwaway VM deleted after the job. Your laptop would keep the firewall, SSH and kernel changes.
3. The **vm** job (`scripts/vm-test.sh`): it changes `/etc/hosts` and checks `ausearch -k network` finds the event.
</details>

Next: [14. How everything fits together](14-how-it-fits-together.md)
