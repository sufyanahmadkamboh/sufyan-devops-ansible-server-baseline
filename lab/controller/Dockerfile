# Ansible control node: every tool the project needs, pinned, in one image.
# Used by the local lab and by CI, so both run exactly the same versions.
FROM python:3.13-slim-trixie

ARG DOCKER_CLI_VERSION=29.4.3
ARG TARGETARCH

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ANSIBLE_CONFIG=/work/ansible.cfg \
    ANSIBLE_COLLECTIONS_PATH=/opt/ansible/collections

RUN apt-get update \
 && apt-get install -y --no-install-recommends openssh-client curl ca-certificates make git shellcheck \
 && rm -rf /var/lib/apt/lists/*

# Docker CLI only (no daemon): Molecule's docker connection uses `docker exec` against the host socket.
RUN case "${TARGETARCH:-amd64}" in arm64) arch=aarch64 ;; *) arch=x86_64 ;; esac \
 && curl -fsSL "https://download.docker.com/linux/static/stable/${arch}/docker-${DOCKER_CLI_VERSION}.tgz" \
    | tar -xz -C /usr/local/bin --strip-components=1 docker/docker \
 && docker --version

COPY requirements.txt requirements.yml /tmp/
RUN pip install -r /tmp/requirements.txt \
 && ansible-galaxy collection install -r /tmp/requirements.yml -p "${ANSIBLE_COLLECTIONS_PATH}"

WORKDIR /work
CMD ["sleep", "infinity"]
