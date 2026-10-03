#!/usr/bin/env bash
# Starts the lab: two fresh "servers", an attacker, the Ansible controller, Prometheus and Grafana.
# Then does what a cloud provider does for a new server: creates the user `ops` with our SSH key.
# shellcheck source=lib.sh
source "$(dirname "$0")/lib.sh"

mkdir -p "$ROOT/.lab"
if [[ ! -s "$ROOT/.lab/grafana-admin-password" ]]; then
  log "Generating a Grafana admin password (.lab/grafana-admin-password, git-ignored)"
  head -c 18 /dev/urandom | base64 | tr -d '/+=' > "$ROOT/.lab/grafana-admin-password"
fi

log "Building images and starting the lab"
compose up -d --build --wait --wait-timeout 180 controller attacker prometheus grafana
compose up -d --build web-01 db-01

log "Creating the controller's SSH key (Docker volume, never in git)"
ctl sh -c 'test -f /keys/id_ed25519 || ssh-keygen -q -t ed25519 -N "" -C ansible-controller -f /keys/id_ed25519'
ctl rm -f /keys/known_hosts
pubkey="$(ctl cat /keys/id_ed25519.pub)"

for host in web-01 db-01; do
  log "Waiting for $host to boot"
  wait_for 120 on "$host" sh -c 'systemctl is-system-running | grep -qE "running|degraded"' >/dev/null \
    || die "$host did not finish booting"
  log "Bootstrapping $host like cloud-init would (user ops + SSH key + sudo)"
  on "$host" sh -c "
    id ops >/dev/null 2>&1 || useradd -m -s /bin/bash ops
    install -d -m 700 -o ops -g ops /home/ops/.ssh
    echo '$pubkey' > /home/ops/.ssh/authorized_keys
    chown ops:ops /home/ops/.ssh/authorized_keys && chmod 600 /home/ops/.ssh/authorized_keys
    echo 'ops ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/00-bootstrap && chmod 440 /etc/sudoers.d/00-bootstrap"
done

log "Checking Ansible can reach both servers over SSH"
wait_for 60 ctl ansible baseline -m ansible.builtin.ping >/dev/null || ctl ansible baseline -m ansible.builtin.ping
ok "Lab is up"
cat <<EOF

  Servers:     web-01 (Ubuntu 24.04) 172.30.0.21   db-01 (Debian 12) 172.30.0.22
  Prometheus:  http://localhost:9090
  Grafana:     http://localhost:3000  (anonymous view; admin password in .lab/grafana-admin-password)

  Next: make audit LABEL=before   then   make harden
EOF
