# Research list

Questions the sources do not answer, or answer wrongly. Each item has: why it matters, how to test it, and what a good answer looks like. Nothing below has been verified on a real cluster yet; the state is `open`.

---

## R1 — Does `minikube mount` survive, and does it update live? (priority: blocking)

**Why:** A1 and A7 both require "edit on the host, see it in the pod". If the 9p mount is one-way, stale, or dies when the terminal closes, both exercises fail.

**Test:**
```bash
minikube mount "$PWD/site:/mnt/site" &   # keep it running
kubectl run t --rm -it --image=busybox -- sh -c 'cat /mnt/site/index.html'
echo change > site/index.html
kubectl run t --rm -it --image=busybox -- sh -c 'cat /mnt/site/index.html'
```

**Also test:** `minikube start --mount --mount-string="$PWD/site:/mnt/site"` — does it replace the foreground `minikube mount`?
**Good answer:** uid/gid mapping, write permissions, propagation direction, latency, what happens on `minikube stop`.

---

## R2 — Which port actually reaches the LAN? (priority: blocking for A4)

**Why:** The whole point of A4 is another computer, not another terminal. `minikube service --url` and `minikube tunnel` are host-local.

**Test:**
```bash
ss -ltnp | grep 8080
curl http://127.0.0.1:8080
curl http://$(hostname -I | awk '{print $1}'):8080
# then from a phone or a second laptop
```
Repeat for: `kubectl port-forward --address 0.0.0.0 svc/web 8080:80`, `minikube tunnel` + LB IP, `minikube service --url`, NodePort.

**Also answer:** does the docker driver publish ports to the host at all? Is `minikube start --ports=8080:30080` a real flag in the installed version, and what does it map?
**Good answer:** a table: mechanism → host-only / LAN / needs root / survives restart.

---

## R3 — ConfigMap propagation latency and what blocks it (priority: high)

**Why:** A2 turns on "it updates by itself". That claim needs a number.

**Test:** `kubectl edit configmap web-index`, then poll the file from inside the pod every 5 s. Repeat with `subPath`, with `immutable: true`, and with the pod on a different node (if multi-node).
**Good answer:** typical sync interval, the reason (kubelet sync period + cache TTL), and the exact list of cases where it never updates.

---

## R4 — Is the Bitnami chart in the PDF still installable as written? (priority: high for the Helm lab)

**Why:** the PDF pins `bitnami/nginx`, `mariadb 18.x`, `opensearch 10.x`, `redis 17.x`. Bitnami has changed its image catalogue and chart values over time.

**Test:**
```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm search repo bitnami/nginx --versions | head
helm show values bitnami/nginx | head -60
helm template t bitnami/nginx --set service.type=LoadBalancer | head -40
```
**Good answer:** whether the chart still exists and under which tags, which value keys changed, and a tested fallback (e.g. a local chart with `nginx:alpine`, or `bitnamilegacy`).

---

## R5 — SQLite over a host mount: safe for how long? (priority: high for A7)

**Why:** A7 asks for a SQLite file on disk whose changes affect the running deployment. That is a filesystem contract, and 9p/virtiofs are not POSIX-perfect.

**Test:** with a single replica, write from the host and from PHP alternately; check `PRAGMA journal_mode`, try WAL, kill the pod mid-write, run a small loop of 10k inserts from both sides and look for `database is locked` or corruption.
**Good answer:** which journal mode to use (`DELETE` is the safe demo choice), whether WAL works at all, and the exact rule ("one writer, one replica, stop before bulk edits").

---

## R6 — Which image tags to pin? (priority: medium)

**Why:** runbooks rot. `nginx:alpine`, `postgres:alpine`, `php:8.3-fpm-alpine` move.

**Test:** `docker manifest inspect` for the candidate tags; check the current stable nginx minor, the supported PHP versions in 2026, and postgres majors.
**Good answer:** a small table of tags, the date checked, and where the tags live in the kit (one place, not scattered).

---

## R7 — PHP-FPM permissions and uid on a host mount (priority: medium, A7)

**Why:** `permission denied` on `storage/` and `database/` is the single most likely A7 failure.

**Test:** `docker run --rm php:8.3-fpm-alpine id www-data`; then mount a host dir owned by the local user at `/var/www/html/database`, write from PHP, read from the host.
**Good answer:** uid/gid (`82` on Alpine), the two possible fixes (chown on the host vs `securityContext.fsGroup`), and which one is less surprising.

---

## R8 — Does the Ingress addon work without `minikube tunnel`? (priority: medium)

**Why:** the PDF enables `ingress` and then assumes a reachable IP.

**Test:** `minikube addons enable ingress`, create the Ingress from the PDF, `kubectl get ingress` (ADDRESS empty or 192.168.49.2?), then `curl -H 'Host: app.example.com' http://<addr>`; repeat with `minikube tunnel` running.
**Good answer:** the address, who can reach it, and the minimal working `curl` line.

---

## R9 — K3s / MicroK8s / k3d as the "real LAN" alternative (priority: medium, feeds A4)

**Why:** the source asks "would switching from minikube help?" — that needs evidence, not opinion.

**Test on a scratch VM or after `minikube delete`:** install K3s with `INSTALL_K3S_EXEC="--disable=traefik"`, deploy the A6 manifest, curl from the LAN. Then MicroK8s with `microk8s enable dns hostpath-storage ingress`.
**Good answer:** time to install, RAM used, whether NodePort/LoadBalancer is reachable from another machine, and the cleanup procedure that leaves the host as it was.

---

## R10 — Secret visibility and "encryption at rest" per distro (priority: medium)

**Why:** A5 is about Secrets, and the honest answer includes where they are stored.

**Test:** `kubectl get secret -o yaml` (is it base64 only?), read the etcd data dir if accessible, check minikube/K3s docs for encryption providers and the `EncryptionConfiguration` flag.
**Good answer:** what an attacker with cluster-admin sees, what a user with `get secrets` sees, and what "encryption at rest" changes.

---

## R11 — Zero-downtime update requires a readiness probe (priority: medium, A6)

**Why:** the update step should demonstrate a rolling update, and the PDF mentions probes but never uses them.

**Test:** `lab-rollout.sh a6 image <tag>` with no probe (count failed requests with a `curl` loop) and with a readiness probe (`/` returning 200).
**Good answer:** number of 5xx during a rollout in both cases, plus the `RollingUpdate` settings that produced it.

---

## R12 — Does `kubectl port-forward` survive a pod restart? (priority: low)

**Why:** the LAN tunnel in A4 is a background process; if the pod is replaced, the tunnel dies silently.

**Test:** start the forward, delete the pod, curl again.
**Good answer:** whether to forward a Service instead of a Pod, and how to keep it alive (systemd unit vs a `while true` loop).

---

## R13 — Where should the kit live long-term? (priority: low, decision)

**Why:** `paczki` and Coat are versioned in the dotfiles repo. A kit that lives only under `07__WorkShops/k8s` cannot be installed by `paczek` from anywhere.

**Test:** install a symlink into `$PACZEK_FILLINGS/k8s`, run `paczek k8s` from an unrelated folder, and check that templates land correctly.
**Good answer:** keep the runbooks here, put `paczki/k8s` and the Coat module in `dots/.coat` (or a separate repo) and link back.

---

## R14 — Does the fake kubectl hide real bugs? (priority: low, honesty)

**Why:** `docs/example-runs.md` is produced with a shim. A shim that always says "3/3 ready" proves nothing about the scripts' error paths.

**Test:** make the shim fail (`FAKE_KUBECTL_FAIL=apply`), run every script, confirm each one exits non-zero and prints the right message.
**Good answer:** a list of failure modes the scripts are known to handle, and the ones only a real cluster can reveal.

---

## R15 — Are the distribution commands the PDF added actually correct? (priority: high, raised by the outline)

**Why:** the outline contains no code, so every command in the PDF — including the K3s and MicroK8s installs — is an addition by the report, not the author's verified notes. Two of them are already suspect.

**Test:**
```bash
# the PDF says SH_K3S_EXEC; the installer reads INSTALL_K3S_EXEC
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--disable=traefik" sh -
systemctl status k3s
kubectl get pods -A | grep -i traefik   # should be empty

# MicroK8s addon names and behaviour
sudo snap install microk8s --classic --channel=1.28/stable
microk8s status --wait-ready
microk8s enable dns hostpath-storage ingress
microk8s kubectl get sc            # is the class named microk8s-hostpath?
```
**Good answer:** the correct variable name, whether `--disable=traefik` takes effect, the real StorageClass names, and a cleanup that restores the host.

---

## R16 — Is a Magento chart worth one experiment? (priority: low, raised by the outline)

**Why:** the outline names Magento as one of the two deployment tests, but none of the seven prompts mentions it. It is the only evidence of "complex, multi-dependency Helm" in the sources.

**Test (no install):**
```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm search repo magento --versions | head
helm dependency update ./magento-stack
helm template store ./magento-stack -f values-production.yaml > /tmp/magento.yaml
```
**Good answer:** whether the chart and its dependency versions still resolve, how large the rendered output is, and whether it teaches anything that H1 (single chart, one dependency) does not. If the answer is no, record it as out of scope in `docs/coverage-matrix.md` and stop.

---

## R17 — What does the observability stack really cost here? (priority: blocking for T3)

**Why:** 6 GiB of cluster and 64 GiB of disk are the budget. The defaults of `kube-prometheus-stack` do not fit.

**Test:** install Prometheus + Grafana + node-exporter only, measure `kubectl top pod -A` and disk after 24 h; then add Loki and Tempo single-binary; then decide retention.
**Good answer:** MiB per component at idle and under a 1 req/s load, and the retention numbers that survive a week.

---

## R18 — pgvector + Apache AGE vs Neo4j for the graph layer (priority: high for T5)

**Why:** one Postgres keeps the backup and the memory small; a separate graph DB may be easier to query.

**Test:** load 10k chunks and 50k edges into pgvector+AGE and into Neo4j Community; run the same 2-hop and hyperedge queries; measure RAM, disk and p95 latency.
**Good answer:** whether the single-Postgres option is enough for the corpus size, and where AGE's Cypher subset hurts.

---

## R19 — Is a hyperedge just a join table? (priority: medium, design)

**Why:** there is no small, maintained OSS hypergraph database. The model needs a defensible encoding.

**Test:** encode "A, B and C jointly define P" as one `edges` row plus three `edge_nodes` rows; run "all relations involving C", "relations whose members are all in this set", and "shortest path A→P"; compare with a pairwise graph.
**Good answer:** the queries that are simpler or harder, and the one case where pairwise edges lose information.

---

## R20 — Can the host GPU serve the cluster cleanly? (priority: high for T5)

**Why:** 8 GiB of VRAM is enough for embeddings and a small chat model, but passthrough into minikube is not worth it.

**Test:** run llama.cpp/Ollama on the host bound to `0.0.0.0`; call it from a pod by the host IP; measure tokens/s and VRAM; then try the same with `host.docker.internal`-style routing on Linux.
**Good answer:** the exact address a pod must use, the latency penalty, and how to keep the model process alive across cluster restarts.

---

## R21 — Do the free tiers still exist in 2026? (priority: medium for T6)

**Why:** every free-tier table on the internet is stale. The plan must not depend on a retired offer.

**Test:** for each row in the T6 table, sign up (or read the current pricing page), note the quota, the expiry, the card requirement and the teardown steps.
**Good answer:** a dated table with only verified rows, and one provider that is "always free" without a trial clock (today: Oracle's Ampere offer is the candidate).

---

## R22 — Which recovery assets are worth automating? (priority: medium for T2)

**Why:** backups that are never restored are decoration.

**Test:** schedule `pg_dump`, delete the database, restore it, and time the whole thing. Repeat for a PVC (`tar` from a helper pod) and for etcd (`etcdctl snapshot save/restore` inside minikube).
**Good answer:** restore time per asset, what is lost between backups, and the drill that must run monthly.
