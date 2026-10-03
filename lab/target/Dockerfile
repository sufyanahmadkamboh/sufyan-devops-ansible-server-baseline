# A lab "server": a systemd container with the distribution's default OpenSSH setup.
# Nothing is hardened here on purpose; it represents a freshly installed machine.
ARG BASE=geerlingguy/docker-ubuntu2404-ansible:latest
FROM ${BASE}

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends openssh-server sudo python3 \
 && rm -rf /var/lib/apt/lists/* \
 # Every container must get its own host keys, so none are baked into the image.
 && rm -f /etc/ssh/ssh_host_*

# Generate missing host keys right before sshd checks its config. Doing it inside ssh.service
# (not in a separate unit) means it also works when Ubuntu's ssh.socket starts sshd early in boot.
COPY --chmod=0644 ssh-hostkeys.conf /etc/systemd/system/ssh.service.d/lab-hostkeys.conf

CMD ["/lib/systemd/systemd"]
