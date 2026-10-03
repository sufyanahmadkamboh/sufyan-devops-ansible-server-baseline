SHELL := bash
CONTROLLER := server-baseline-controller:dev
# Run a command in a throwaway controller container (no lab needed).
TOOLBOX = MSYS_NO_PATHCONV=1 docker run --rm -v "$(CURDIR):/work" -v /var/run/docker.sock:/var/run/docker.sock \
          -v molecule-cache:/root/.cache $(CONTROLLER)
LABEL ?= manual

.PHONY: help controller lint molecule promtool lab-up lab-down harden audit compare verify drift e2e vm-test

help: ## Show the targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

controller: ## Build the Ansible controller image (all tools, pinned)
	docker build -t $(CONTROLLER) -f lab/controller/Dockerfile .

lint: controller ## Static checks: yamllint, ansible-lint, syntax, ShellCheck, unit tests
	$(TOOLBOX) scripts/lint.sh

promtool: ## Check the alert rules and run their unit tests
	MSYS_NO_PATHCONV=1 docker run --rm -v "$(CURDIR):/w" -w /w --entrypoint promtool prom/prometheus:v3.15.0 \
	  check rules lab/prometheus/rules/server-baseline.yml
	MSYS_NO_PATHCONV=1 docker run --rm -v "$(CURDIR):/w" -w /w/tests/prometheus --entrypoint promtool \
	  prom/prometheus:v3.15.0 test rules server-baseline.test.yml

molecule: controller ## Role tests on Ubuntu 24.04, Debian 12, Debian 13 (converge, idempotence, verify)
	$(TOOLBOX) molecule test

lab-up: ## Start the lab: 2 fresh servers, attacker, controller, Prometheus, Grafana
	scripts/lab-up.sh

lab-down: ## Remove the lab
	scripts/lab-down.sh

harden: ## Apply the baseline to the lab servers
	scripts/harden.sh

audit: ## Lynis audit of the lab servers (LABEL=before|after)
	scripts/audit.sh $(LABEL)

compare: ## Lynis before/after table
	scripts/audit.sh compare

verify: ## Check every control on the lab servers
	scripts/verify.sh

drift: ## Show what differs from the baseline, without changing anything
	scripts/drift-check.sh

e2e: ## Full end-to-end test on a fresh lab (about 10 minutes)
	scripts/e2e.sh

vm-test: ## Harden THIS machine and test it (disposable VMs/CI only)
	scripts/vm-test.sh
