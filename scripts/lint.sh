#!/usr/bin/env bash
# Every static check, in the order CI runs them. Needs the tools from requirements.txt
# (they are all in the controller image: `make lint` runs this script there).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
export ANSIBLE_CONFIG="$PWD/ansible.cfg"

step() { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }

step "yamllint"
yamllint --strict .

step "ansible-lint (production profile)"
ansible-lint --offline

step "Playbook syntax"
for p in playbooks/*.yml; do
  ansible-playbook -i inventories/lab/hosts.yml --syntax-check "$p" >/dev/null && echo "ok $p"
done

step "ShellCheck"
shellcheck -S style -x scripts/*.sh

step "Unit tests (Lynis report converter)"
python3 -m pytest -q tests
