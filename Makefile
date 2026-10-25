# k8s lab kit — one entry point for the checks and the real runs.
#
#   make            list the targets
#   make check      syntax, shellcheck, YAML, dry-runs (never touches a cluster)
#   make tools      install the CLI tools into ~/.local/bin
#   make cluster    create the minikube cluster with the doctor's sizing
#   make demo       the offline transcript used in docs/example-runs.md
#   make up         the real A6 scenario
#   make verify     the real checks for A6
#
# The real targets require kubectl and a cluster. The check targets do not.

SHELL := /bin/bash
.DEFAULT_GOAL := help

KIT := $(CURDIR)
SCRIPTS := $(wildcard scripts/*.sh scripts/lib/*.sh tests/*.sh) scripts/demo/kubectl \
  setup/install-tools.sh observability/install.sh clusters/k3s/install.sh \
  bastion/host/setup.sh bastion/host/audit.sh bastion/k8s/entrypoint.sh
DEMO_KUBECTL := $(KIT)/scripts/demo/kubectl
SCENARIO ?= a6
PROFILE ?= minimal
CLUSTER_ARGS ?=

.PHONY: help check test doctor tools tools-check cluster cluster-delete obs drills \
  syntax shellcheck yaml dryrun demo up down status scale rollout verify tunnel clean

# show the available targets
help:
	@printf '%s\n' \
	  'make check        syntax + shellcheck + YAML + dry-runs (no cluster needed)' \
	  'make tools        install kubectl, minikube, helm, k3d, kind, sqlite3' \
	  'make tools-check  report which tools are present' \
	  'make doctor       check tools, RAM, disk, ports, GPU, and print sizing' \
	  'make cluster      create minikube with the doctor sizing' \
	  'make cluster-delete  delete the minikube profile' \
	  'make obs          observability/install.sh --profile $(PROFILE)' \
	  'make drills       run all T1 failure drills (inject → verify → recover)' \
  'make syntax       bash -n on every script' \
	  'make shellcheck   shellcheck at warning level on every script' \
	  'make yaml         parse every manifest, values file and cluster config' \
	  'make dryrun       run every script with --dry-run' \
	  'make demo         run the scripts against the fake kubectl' \
	  'make up           lab-up.sh $(SCENARIO) --mount' \
	  'make down         lab-down.sh $(SCENARIO)' \
	  'make status       lab-status.sh $(SCENARIO)' \
	  'make scale        lab-scale.sh' \
	  'make rollout      lab-rollout.sh history' \
	  'make verify       lab-verify.sh $(SCENARIO)' \
	  'make test         offline test suite (tests/run.sh)' \
	  'make tunnel       lab-tunnel.sh --background' \
	  'make clean        remove the demo state and logs'

# the full offline gate: nothing here talks to a cluster
check: syntax shellcheck yaml dryrun
	@printf 'check ok\n'

# the offline test suite: scripts, manifests, fake-cluster flows
test: check
	@TEST_FILTER="$(TEST_FILTER)" tests/run.sh

# what this machine can host, with a recommended minikube command
doctor:
	@scripts/lab-doctor.sh

# the clients, without root where possible
tools:
	@setup/install-tools.sh

tools-check:
	@setup/install-tools.sh --check

# create or delete the default cluster
cluster:
	@scripts/cluster-create.sh $(CLUSTER_ARGS)

cluster-delete:
	@scripts/cluster-delete.sh $(CLUSTER_ARGS) --yes

# observability, one profile at a time
obs:
	@observability/install.sh --profile $(PROFILE)

# recovery drills: inject failures, verify state, recover
drills:
	@scripts/lab-drill.sh all --inject
	@printf '\n=== Failures injected. Verify states manually if needed. ===\n\n'
	@scripts/lab-drill.sh all --recover
	@printf '\ndrills ok\n'

# parse every script before running anything
syntax:
	@bash -n $(SCRIPTS)
	@printf 'syntax ok (%s scripts)\n' "$(words $(SCRIPTS))"

# static analysis; the scripts should be clean
shellcheck:
	@shellcheck -S warning -x $(SCRIPTS)
	@printf 'shellcheck ok\n'

# parse every YAML file, including the multi-document ones
yaml:
	@python3 -c 'import glob, yaml; \
files = [f for p in ("manifests/**/*.yaml", "observability/**/*.yaml", "observability/**/*.yml", "clusters/**/*.yaml", "bastion/**/*.yaml") for f in glob.glob(p, recursive=True)]; \
docs = [d for f in files for d in yaml.safe_load_all(open(f)) if d]; \
print("yaml ok (%d documents, %d files)" % (len(docs), len(files)))'

# every script must survive --dry-run without a cluster
dryrun:
	@scripts/lab-up.sh a6 --dry-run >/dev/null
	@scripts/lab-down.sh a6 --dry-run >/dev/null
	@scripts/lab-status.sh a6 --dry-run >/dev/null
	@scripts/lab-scale.sh --dry-run >/dev/null
	@scripts/lab-rollout.sh status --dry-run >/dev/null
	@scripts/lab-tunnel.sh --dry-run >/dev/null
	@scripts/lab-verify.sh a2 --dry-run >/dev/null
	@scripts/cluster-create.sh --dry-run >/dev/null
	@observability/install.sh --dry-run >/dev/null
	@bastion/host/setup.sh --dry-run >/dev/null
	@printf 'dry-run ok\n'

# the offline transcript: proves the script flow, not the cluster
demo:
	@PATH="$(KIT)/scripts/demo:$$PATH" FAKE_KUBECTL_STATE="$${TMPDIR:-/tmp}/k8s-lab-fake-state-demo" \
	  scripts/lab-up.sh a6 --dry-run >/dev/null
	@PATH="$(KIT)/scripts/demo:$$PATH" FAKE_KUBECTL_STATE="$${TMPDIR:-/tmp}/k8s-lab-fake-state-demo" \
	  scripts/lab-status.sh a6
	@PATH="$(KIT)/scripts/demo:$$PATH" FAKE_KUBECTL_STATE="$${TMPDIR:-/tmp}/k8s-lab-fake-state-demo" \
	  scripts/lab-scale.sh --delta 1
	@PATH="$(KIT)/scripts/demo:$$PATH" FAKE_KUBECTL_STATE="$${TMPDIR:-/tmp}/k8s-lab-fake-state-demo" \
	  scripts/lab-verify.sh a6
	@printf 'demo ok (this is a fake cluster)\n'

# real runs; these need kubectl and a reachable cluster
up:
	@scripts/lab-up.sh $(SCENARIO) --mount

down:
	@scripts/lab-down.sh $(SCENARIO)

status:
	@scripts/lab-status.sh $(SCENARIO)

scale:
	@scripts/lab-scale.sh

rollout:
	@scripts/lab-rollout.sh history

verify:
	@scripts/lab-verify.sh $(SCENARIO)

tunnel:
	@scripts/lab-tunnel.sh --background

# remove what the demo and the dry-runs left behind
clean:
	@rm -f "$${TMPDIR:-/tmp}/k8s-lab-fake-state"* "$${TMPDIR:-/tmp}/k8s-lab-fake.log" \
	  "$${TMPDIR:-/tmp}/k8s-lab-mount.pid" "$${TMPDIR:-/tmp}/k8s-lab-forward-"*.pid
	@printf 'cleaned demo state\n'
