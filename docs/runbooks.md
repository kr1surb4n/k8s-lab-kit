# Runbooks — the step-by-step lab

Each section is self-contained: goal, commands, what you should see, and what
will bite. Commands assume you are in the kit root:

```bash
cd ~/00___Castle/07__WorkShops/k8s
```

---

## Common setup (do this once)

**1. Check the machine.**

```console
$ make doctor
```

Read the `tier:` line and the recommended `minikube start` command. Stop if a
`FAIL` line appears.

**2. Install the missing clients.**

```bash
sudo apt-get update
sudo apt-get install -y kubectl minikube helm sqlite3 apache2-utils
```

`minikube` from Debian can lag; the upstream binary is fine too. Verify:

```console
$ kubectl version --client
$ minikube version
$ helm version --short
```

**3. Start the cluster** (use the doctor's numbers if they differ).

```bash
minikube start --driver=docker --cpus=6 --memory=6144 --disk-size=15g
kubectl get nodes -o wide
```

Expected: one node, `Ready`.

**4. Mount the host folder** (needed by A1 and A7 only).

```bash
scripts/lab-up.sh a1 --mount
```

or run it yourself in a second terminal:

```bash
minikube mount "$PWD:/mnt/lab"
```

The mount is a foreground process; when it stops, the pods that need it stop
seeing changes. `scripts/lab-up.sh --mount` detaches it and records the pid.

**5. Never work in `default`.** Every script uses `k8s-lab`.

---

# A1 — nginx serving a directory from disk

**Done when:** editing `site/index.html` on the host changes the page without a
restart, and `site/images/logo.svg` is downloadable.

### Steps

```bash
scripts/lab-up.sh a1 --mount
scripts/lab-tunnel.sh --background
curl -s http://127.0.0.1:8080 | head -5
curl -sI http://127.0.0.1:8080/images/logo.svg | head -3
```

Expected: the HTML from `site/index.html`, and
`Content-Type: image/svg+xml` for the image.

Now prove it is live:

```bash
sed -i 's/replace-me-by-hand/edited-at-'"$(date +%H:%M:%S)"'/' site/index.html
curl -s http://127.0.0.1:8080 | grep edited-at
```

### Why it works

`minikube mount` exposes the host folder inside the node at `/mnt/lab`. The
Deployment mounts `/mnt/lab/site` into `/usr/share/nginx/html` as a **hostPath**
volume. nginx reads whatever is there, on every request.

### Answering the original question

**Can I download images that live in the same directory?** Yes. nginx serves any
file under the document root by URL path, so `site/images/logo.svg` becomes
`/images/logo.svg`. The caveat belongs to A2, not here: this works because the
files are on a **volume**, not in a ConfigMap (which is text-only, 1 MiB).

### Pitfalls

- `ContainerCreating` forever → the mount is not running, `/mnt/lab/site` does
  not exist inside the node.
- The page does not change → check you are editing `site/index.html`, not a copy.
- Permission denied → host files must be world-readable (`644`/`755`).

### Cleanup

```bash
scripts/lab-down.sh a1
```

---

# A2 — `index.html` from a ConfigMap

**Done when:** `kubectl edit configmap web-index` changes the page within about a
minute, with no pod restart.

### Steps

```bash
scripts/lab-up.sh a2
scripts/lab-tunnel.sh --background
curl -s http://127.0.0.1:8080 | head -5
```

Edit the ConfigMap:

```bash
kubectl edit configmap web-index -n k8s-lab
# change the <h1> line, save, quit

# watch the file inside the pod change (about 30-60 s)
kubectl exec deploy/web -n k8s-lab -- sh -c 'while true; do grep -o "<h1>.*</h1>" /usr/share/nginx/html/index.html; sleep 5; done'
```

Expected: the pod name does not change, the file does.

### Why it works, and where it does not

A ConfigMap mounted as a **directory** is a projected volume; the kubelet syncs
it periodically. Two things break the magic:

- `subPath: index.html` — a subPath mount is a bind mount, never updated.
- an env var (`valueFrom.configMapKeyRef`) — env vars are fixed at container
  start; only a new pod sees a new value.

### The limits

```bash
# a file over 1 MiB is rejected by the API server
head -c 2M /dev/urandom > /tmp/big.bin
kubectl create configmap too-big --from-file=/tmp/big.bin -n k8s-lab
# error: ConfigMap "too-big" is invalid: data: Too long: must have at most 1048576 bytes
rm -f /tmp/big.bin
```

A binary or a large file belongs on a volume (A1/A7), not in a ConfigMap.

### Cleanup

```bash
scripts/lab-down.sh a2
```

---

# A3 — environment variables: who, when, where, how

**Done when:** the page shows values that came from the ConfigMap, the pod spec
and the Downward API, and you can explain which one wins.

### Steps

```bash
scripts/lab-up.sh a3
scripts/lab-tunnel.sh --background
curl -s http://127.0.0.1:8080 | grep -E 'APP_ENV|LOG_LEVEL|GREETING|POD_NAME|COMPOSED'
curl -s http://127.0.0.1:8080/env.txt | sort | head -20
```

Expected: `APP_ENV = from-pod-spec` — the explicit `env` entry beats the
`envFrom` value `from-configmap`. `COMPOSED = from-pod-spec-debug`, because
`$(VAR)` expands from earlier entries in the same list.

The host-side mechanics:

```bash
scripts/env-demo.sh
```

### The four questions, answered

**Who uses these variables?** The container's main process and everything it
starts: nginx entrypoint scripts, PHP-FPM workers, a Node/Python app reading
`process.env`/`os.environ`, a shell inside `kubectl exec`. Also the kubelet
itself reads the pod spec, and image `ENV` values come from the Dockerfile.

**When?** At container creation. The values are frozen into the process
environment. A ConfigMap or Secret change does not update a running container;
the pod must be recreated. Volume-mounted files are the exception.

**Where do they live?** In the container's process environment (`/proc/1/environ`),
inherited from the image `ENV` and the pod spec, materialised by the kubelet. In
the cluster they are part of the Pod object (and of the ConfigMap/Secret it
references). On the host they live in the shell (`export`), in `.env` files, in
the service manager, or in the parent process.

**What are the mechanisms?** On the host: `export`, `VAR=value cmd`, `.env` with
`set -a`, `envsubst`, `direnv`. In Kubernetes: literal `env`, `envFrom`
(ConfigMap/Secret), `valueFrom` (`configMapKeyRef`, `secretKeyRef`, `fieldRef`,
`resourceFieldRef`), and `$(VAR)` expansion. Precedence: explicit `env` >
`envFrom` > image `ENV`.

### The leak paths (remember these)

```bash
kubectl exec deploy/web -n k8s-lab -- cat /proc/1/environ | tr '\0' '\n'
kubectl describe pod -n k8s-lab -l app.kubernetes.io/name=web | grep -A2 Environment
```

Anything in an env var is visible to every child process and in `describe`.

### Cleanup

```bash
scripts/lab-down.sh a3
```

---

# A4 — let another computer on the LAN reach the app

**Done when:** a second machine (phone, laptop) loads the page through
`http://<host-lan-ip>:8080`, and you can say why the LoadBalancer alone is not
enough on minikube.

### Steps

```bash
scripts/lab-up.sh a6
scripts/lab-tunnel.sh --background --port 8080
```

On the host:

```bash
curl -s http://127.0.0.1:8080 | head -3
curl -s http://$(hostname -I | awk '{print $1}'):8080 | head -3
```

On the other machine: open `http://<host-lan-ip>:8080`.

If it does not answer, the firewall is the first suspect:

```bash
sudo ufw status
sudo ufw allow 8080/tcp     # then remove it again when done
sudo ufw delete allow 8080/tcp
```

### Why this mechanism

`kubectl port-forward --address 0.0.0.0` opens a real listener on the host, on
every interface. It is the only mechanism that behaves the same on minikube, k3d
and a bare cluster, and it needs no ingress, no MetalLB and no root.

### What does not work, and why

| Attempt | Reachable from the LAN? | Reason |
|---|---|---|
| `Service type: LoadBalancer` | no | no cloud controller; `EXTERNAL-IP` stays `<pending>` |
| `minikube tunnel` + LB IP | no | the tunnel's IP exists on the host only |
| `minikube service web --url` | no | it binds `127.0.0.1` |
| `Service type: NodePort` | no (docker driver) | the node's IP is inside the docker network |
| `kubectl port-forward --address 0.0.0.0` | **yes** | a listener on the host |

### Would switching from minikube help?

Yes, for this specific problem, because the node stops being hidden:

- **k3s / MicroK8s on the host**: NodePort and the ingress listen on the host's
  own interfaces. `curl http://<lan-ip>:30080` just works, no tunnel. This is why
  they are popular for homelabs. Cost: they change the host (systemd units,
  iptables, containerd), and cleanup is more than `minikube delete`.
- **k3d / kind**: still docker-in-docker, but they can publish ports to the host
  (`--port 8080:80@loadbalancer`). Reachable from the LAN, no tunnel, cheap to
  delete. Good middle ground.
- **minikube stays** the best choice for A1–A6: one command up, one command
  down, no host changes. Use `port-forward` for the LAN demo and learn the
  difference rather than fight it.

### Cleanup

```bash
kill "$(cat ${TMPDIR:-/tmp}/k8s-lab-forward-8080.pid)" 2>/dev/null || true
scripts/lab-down.sh a6
```

---

# A5 — a test deployment with Secrets

**Done when:** `curl` returns 401 without credentials and 200 with them, and the
password is a mounted file, not an env var.

### Steps

```bash
scripts/lab-up.sh a5
scripts/lab-tunnel.sh --background

curl -si http://127.0.0.1:8080/ | head -3          # HTTP/1.1 401
curl -si -u lab:labpass http://127.0.0.1:8080/ | head -3   # HTTP/1.1 200
```

Inspect what the cluster stores:

```bash
kubectl get secret web-basic-auth -n k8s-lab -o yaml
kubectl exec deploy/web -n k8s-lab -- ls -l /etc/nginx/auth/.htpasswd
```

Expected: `data` is base64, and the mounted file is readable by the nginx worker
(the manifest sets `defaultMode: 0644`; a stricter mode needs matching file
ownership, because the nginx workers do not run as root).

Make your own credential instead of the demo one:

```bash
# htpasswd if installed, openssl otherwise; both produce an apr1 line.
scripts/mkpasswd.sh lab 'labpass' > .htpasswd
kubectl create secret generic web-basic-auth --from-file=.htpasswd -n k8s-lab \
  --dry-run=client -o yaml | kubectl apply -f -
rm .htpasswd
```

### Why a Secret and not a ConfigMap

A Secret is the same key/value object with three differences that matter: it is
excluded from `kubectl describe`-style dumps by convention, it can be mounted
with `0400`, and it can be encrypted at rest if the cluster is configured for it.
Base64 is **encoding**, not encryption: anyone with `get secrets` in the
namespace reads it.

### Verify and cleanup

```bash
scripts/lab-verify.sh a5 --url http://127.0.0.1:8080 --expect 401
scripts/lab-down.sh a5
```

---

# A6 — LoadBalancer, 3 replicas, and the lifecycle

**Done when:** you can bring the app up on an empty cluster, delete it, scale
+1 and −1, and update with a rollback — each with a verification.

### Up on an empty cluster

```bash
scripts/lab-down.sh all --yes        # start from nothing
scripts/lab-up.sh a6
scripts/lab-status.sh a6
```

Expected: `3/3` ready, `Service` of type `LoadBalancer`, `EXTERNAL-IP <pending>`.

### Scale +1, then −1

```bash
scripts/lab-scale.sh --delta 1
scripts/lab-status.sh a6
scripts/lab-scale.sh --delta -1
scripts/lab-status.sh a6
```

### Update and roll back

```bash
scripts/lab-rollout.sh history
scripts/lab-rollout.sh image nginx:1.28-alpine
scripts/lab-rollout.sh history
scripts/lab-rollout.sh undo
```

Watch it happen in a second terminal:

```bash
kubectl get pods -n k8s-lab -w
```

Expected: new pods appear one at a time, old ones terminate only after the new
one is Ready — because `maxUnavailable: 0` and the readiness probe.

### Prove the probe matters

```bash
kubectl patch deploy web -n k8s-lab --type=json \
  -p '[{"op":"remove","path":"/spec/template/spec/containers/0/readinessProbe"}]'
kubectl set image deploy/web web=nginx:1.29-alpine -n k8s-lab
# in another terminal, count failures during the rollout:
for i in $(seq 1 200); do curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080; done | sort | uniq -c
kubectl rollout undo deploy/web -n k8s-lab
```

Without the probe, Kubernetes sends traffic to containers that are not listening
yet. That is the difference between "the update succeeded" and "the update was
invisible".

### Delete

```bash
scripts/lab-down.sh a6      # objects only
scripts/lab-down.sh all --yes   # whole namespace
```

---

# A7 — nginx + Laravel shape + PostgreSQL + SQLite on disk

**Done when:** the page reads both databases, and inserting a row into
`app/database/database.sqlite` on the host changes the page on reload.

### Steps

```bash
# one-time image build (adds pdo_pgsql to php-fpm)
scripts/lab-up.sh a7 --build --mount

scripts/lab-status.sh a7
scripts/lab-tunnel.sh --background
curl -s http://127.0.0.1:8080 | grep -E 'SQLite|PostgreSQL|row'
```

Expected: both sections show at least one row, and the pod name.

Now the live SQLite file:

```bash
# the pod created the file through the mount; write from the host
sqlite3 app/database/database.sqlite \
  "INSERT INTO notes (body) VALUES ('written from the host at $(date +%H:%M:%S)');"

curl -s http://127.0.0.1:8080 | grep 'written from the host'
```

No restart, no rebuild. That is the whole point of A7.

PostgreSQL, for contrast, is a real service:

```bash
kubectl exec deploy/postgres -n k8s-lab -- \
  psql -U lab -d lab -c "INSERT INTO notes (body) VALUES ('from psql');"
curl -s http://127.0.0.1:8080 | grep 'from psql'

kubectl exec deploy/postgres -n k8s-lab -- pg_dump -U lab lab | head -5
```

### Why the stack looks like this

- nginx and php-fpm share **one pod** and **one hostPath**, so they always see
  the same files. No shared PVC, no rsync, no stale code.
- PHP-FPM executes, nginx only routes. `fastcgi_pass 127.0.0.1:9000` works
  because both containers share the pod's network namespace.
- The SQLite file is on the host mount because the exercise asks for a file on
  disk that affects the deployment. Postgres is on a PVC because that is how a
  real database is run.

### The permission trap

```bash
kubectl exec deploy/web -n k8s-lab -c php -- id
# uid=82(www-data) gid=82(www-data)
```

Alpine's `www-data` is uid **82**. The init container chowns `database/` and
`storage/` to 82 and leaves `database.sqlite` at `0666` so the host user can
still write it. Remove that init step and the page fails with
`SQLITE_CANTOPEN` / `permission denied`. The PDF mentions the symptom; this is
the fix.

### Why one replica

SQLite on a network-ish filesystem (9p, NFS) has no reliable multi-writer
locking. WAL mode is not safe there either. One writer, one replica, and the
`Recreate` strategy. Need more replicas? Use PostgreSQL; that is what it is for.

### Cleanup

```bash
scripts/lab-down.sh a7
rm -f app/database/database.sqlite
```

---

# D1 — distributions: minikube vs k3s vs MicroK8s

**Done when:** you have run the same manifest on two of them and can name what
changed.

| | minikube | k3s | MicroK8s |
|---|---|---|---|
| form | binary managing a VM/container | single binary, systemd | snap |
| datastore | etcd | SQLite / Kine / etcd | dqlite |
| runtime | docker/podman/kvm | containerd | containerd |
| default StorageClass | `standard` | `local-path` | `microk8s-hostpath` |
| LAN NodePort | no (docker driver) | yes | yes |
| host impact | none | systemd + iptables | snap + iptables |
| cleanup | `minikube delete` | uninstall script | `snap remove` |

Same app, two clusters:

```bash
minikube start --driver=docker
scripts/lab-up.sh a6
scripts/lab-down.sh a6
minikube stop

# k3d is the cheapest way to get the "real" behaviour without touching the host
k3d cluster create lab -p 8080:80@loadbalancer
kubectl config use-context k3d-lab
scripts/lab-up.sh a6
curl -s http://127.0.0.1:8080 | head -3
k3d cluster delete lab
```

Note what changed: the StorageClass name, the ingress class, and the fact that
`8080` now reaches the load balancer without a port-forward.

---

# H1 — Helm: install, upgrade, rollback

**Done when:** `helm history` shows revisions and a rollback returns to the
previous one.

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm show values bitnami/nginx | head -40   # read, do not copy from a blog
```

Install with the template from this kit:

```bash
helm upgrade --install web bitnami/nginx \
  --namespace helm-lab --create-namespace \
  --set service.type=ClusterIP \
  --set replicaCount=3
kubectl rollout status deploy/web-nginx -n helm-lab
```

Upgrade and roll back:

```bash
helm upgrade web bitnami/nginx -n helm-lab --set replicaCount=4
helm history web -n helm-lab
helm rollback web -n helm-lab      # previous revision
helm rollback web 1 -n helm-lab    # revision 1, NOT "one step back"
helm uninstall web -n helm-lab
```

`helm template` before applying, always:

```bash
helm template web bitnami/nginx --set replicaCount=2 | head -40
helm lint ./chart
helm diff upgrade web bitnami/nginx   # needs the helm-diff plugin
```

### What the PDF got wrong

- `helm rollback web-release 1` is "revision 1", the first install, not "back one".
- Bitnami values (image tags, dependency ranges) change; `helm show values` is
  the only source of truth.
- `--reuse-values` silently keeps old settings. Prefer an explicit `-f values.yaml`.

---

# N1 — Service, Ingress, storage and ConfigMap together

**Done when:** the app answers on a host name through an ingress, and you have
seen a PVC bind and be deleted.

```bash
minikube addons enable ingress
kubectl get pods -n ingress-nginx
scripts/lab-up.sh a6
```

Apply the ingress from the template:

```bash
cp paczki/k8s/ingress.yaml.tpl /tmp/ingress.yaml
sed -i 's/{{ APP_NAME }}/web/; s/{{ HOST }}/app.example.com/; s/{{ SERVICE_NAME }}/web/; s/{{ SERVICE_PORT }}/80/' /tmp/ingress.yaml
kubectl apply -f /tmp/ingress.yaml -n k8s-lab
kubectl get ingress -n k8s-lab
```

Get the address and route by Host header:

```bash
INGRESS_IP=$(kubectl get ingress web -n k8s-lab -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl -s -H 'Host: app.example.com' "http://$INGRESS_IP/" | head -3
```

Now break it on purpose: uncomment `rewrite-target: /` and watch relative assets
404. That is the most common ingress bug in the PDF's example.

Storage, side by side:

```bash
kubectl get storageclass
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: demo-pvc
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: standard
  resources:
    requests:
      storage: 100Mi
EOF
kubectl get pvc demo-pvc -n k8s-lab -w   # Pending -> Bound
kubectl delete pvc demo-pvc -n k8s-lab
```

---

# T1 — troubleshooting drills

**Done when:** you have produced each bad state yourself and fixed it with the
five-step method (`analysis/06-scope-expansion.md`, T2).

The fixed sequence from the PDF, which is correct:

```bash
kubectl get pods -n k8s-lab -o wide
kubectl describe pod <pod> -n k8s-lab
kubectl logs <pod> -n k8s-lab --previous
kubectl exec -it <pod> -n k8s-lab -- /bin/sh
kubectl port-forward <pod> 8080:80 -n k8s-lab
kubectl get events -n k8s-lab --sort-by=.lastTimestamp | tail -20
```

| State | Inject | Read | Fix |
|---|---|---|---|
| CrashLoopBackOff | `command: ["sh","-c","exit 1"]` | `logs --previous`, exit code | fix the command/config |
| ImagePullBackOff | `image: nginx:does-not-exist` | `describe` events | correct tag, `imagePullSecrets` |
| Pending | `requests.memory: 64Gi` | `describe` → `FailedScheduling` | smaller request, more nodes |
| OOMKilled | `limits.memory: 16Mi` + allocation | `describe` → exit 137 | raise the limit or fix the leak |
| Readiness failing | probe `/missing` | endpoints empty, 503 | correct path/port |
| Pending PVC | `storageClassName: nope` | `describe pvc` | real class name |

The rule: `describe` for scheduling and events, `logs` for the app, `exec` for
the environment, `port-forward` for "is it the app or the network".

---

# Reset everything

```bash
scripts/lab-down.sh all --yes
minikube delete
docker system prune -f
```

`minikube delete` removes the cluster and its images; `docker system prune`
reclaims the build cache. Check `df -h /` before and after — this machine has
64 GiB free, and a full lab round can eat several.
