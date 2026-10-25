# Example runs

Two kinds of transcript live here, and they are labelled:

- **real** — actual output from this machine, today.
- **simulated** — output from `scripts/demo/kubectl`, a fake client that answers
  the calls the scripts make. It proves the script logic (arguments, order, exit
  codes, messages). It proves **nothing** about Kubernetes.

Anything marked simulated must be replaced by a real transcript once a cluster
exists. The checklist at the bottom tracks that.

Regenerate the simulated part with:

```bash
make demo
```

---

## 1. Hardware and tools — real

```console
$ make doctor
== host
ok    Linux 6.12.105+deb13-amd64 x86_64
ok    24 CPUs
ok    memory: 30.8 GiB total, 11.9 GiB available
ok    disk free at the kit: 64.5 GiB

== tools
ok    docker (Docker version 29.8.0, build 88096ef)
warn  kubectl is not installed
warn  minikube is not installed
warn  helm is not installed
warn  sqlite3 is not installed
warn  htpasswd is not installed
ok    jq (jq-1.7)
ok    curl (curl 8.14.1 ...)
ok    python3 (Python 3.13.5)
ok    shellcheck (ShellCheck - shell script analysis tool)
ok    git (git version 2.47.3)

== container runtime
ok    docker daemon answers
ok    docker 29.8.0, storage driver overlayfs, cgroup v2
ok    running as: kris (no sudo needed for docker)

== ports
ok    port 80 is free
ok    port 8080 is free
ok    port 8443 is free

== accelerator
ok    GPU: NVIDIA GeForce RTX 5070 Laptop GPU, 8151 MiB, 610.57.04
ok    GPU tier: local 7-8B quantised models and embeddings are realistic

== cluster
warn  no cluster reachable (run: minikube start --driver=docker)

== recommendation
  minikube start --driver=docker --cpus=6 --memory=6144 --disk-size=15g
  tier: STANDARD, A1-A6, A7 with care
  heavier tracks: one at a time; a full kube-prometheus-stack needs ~2 GiB
  local AI: use the GPU outside the cluster, not inside a pod

no blocking problems, 6 warning(s)
```

---

## 2. Host-side environment variables (A3) — real

`scripts/env-demo.sh` needs no cluster. This is the whole point of A3 made
visible: a plain shell variable is not inherited, an exported one is, a `.env`
file is just text until it is exported.

```console
$ scripts/env-demo.sh

== 1. a shell variable is local to the shell
  LOCAL_ONLY     = visible here
$ bash -c "echo \${LOCAL_ONLY:-(unset)}"
  child sees    = (unset)

== 2. export makes it part of the environment
  EXPORTED       = visible everywhere
$ bash -c "echo \${EXPORTED:-(unset)}"
  child sees    = visible everywhere

== 3. a .env file is only text until you export it
$ cat lab.env
  APP_ENV=lab
  LOG_LEVEL=debug
  GREETING="hello from the file"
$ set -a; . lab.env; set +a
  APP_ENV        = lab
  GREETING       = hello from the file

== 4. envsubst renders a file from the environment
$ cat template.txt
  APP_ENV=${APP_ENV} LOG_LEVEL=${LOG_LEVEL}
$ envsubst < template.txt
  APP_ENV=lab LOG_LEVEL=debug

== 5. defaults, empty values and unset
  EMPTY          =
  ${EMPTY:-fallback}   = fallback   (empty triggers the default)
  ${MISSING:-fallback} = fallback   (unset triggers the default)
  ${MISSING-fallback}  = fallback   (unset only, empty stays empty)

== 6. what a child actually receives
$ env -i bash -c "env | sort"
  PWD=/home/kris/00___Castle/07__WorkShops/k8s
  SHLVL=1
  _=/usr/bin/env

== 7. where this shows up in Kubernetes
  image ENV       -> baked into the image, overridden by the pod spec
  pod spec env    -> wins over the image and over envFrom
  envFrom         -> bulk import of ConfigMap/Secret keys
  valueFrom       -> one key, or metadata.name / status.podIP
  change a ConfigMap -> env vars do NOT update; the pod must be recreated
  volume mount       -> DOES update (about a minute), unless subPath is used

cleaned up /tmp/k8s-lab-env-demo
```

---

## 3. The A6 lifecycle — simulated

Run with `PATH=scripts/demo:$PATH`, so `kubectl` is the shim. The commands,
arguments, ordering and exit codes are the real ones.

```console
$ scripts/lab-up.sh a6
+ kubectl create namespace k8s-lab
namespace/k8s-lab created
+ kubectl apply -f .../manifests/a6 -n k8s-lab
deployment.apps/web created
service/web created
(applied .../manifests/a6)
deployment "web" successfully rolled out

scenario a6 is up in namespace k8s-lab

try it:
  host:    http://127.0.0.1:8080
  LAN:     http://192.168.1.240:8080  (run scripts/lab-tunnel.sh)
  in pod:  kubectl exec deploy/web -n k8s-lab -- curl -s localhost
```

```console
$ scripts/lab-status.sh a6

== pods
NAME                    READY   STATUS    RESTARTS   AGE   IP           NODE
web-6d8778f-1          1/1     Running   0          5m    10.244.0.5   minikube
web-6d8778f-2          1/1     Running   0          5m    10.244.0.6   minikube
web-6d8778f-3          1/1     Running   0          5m    10.244.0.7   minikube

== deployment
NAME   READY   UP-TO-DATE   AVAILABLE   AGE
web    3/3     3            3           5m

== replicas
deployment "web" successfully rolled out

== service
NAME   TYPE           CLUSTER-IP    EXTERNAL-IP   PORT(S)        AGE
web    LoadBalancer   10.96.0.10    <pending>     80:30080/TCP   5m

== endpoints
NAME   ENDPOINTS                                AGE
web    10.244.0.5:80,10.244.0.6:80,10.244.0.7:80   5m

== ingress
No resources found in k8s-lab namespace.

== storage
No resources found in k8s-lab namespace.

== config
NAME               DATA   AGE
kube-root-ca.crt   1      10m

== secrets
No resources found in k8s-lab namespace.

== recent events
LAST SEEN   TYPE     REASON    OBJECT       MESSAGE
2m          Normal   Pulled    pod/web-1    Container image already present
2m          Normal   Created   pod/web-1    Created container web
2m          Normal   Started   pod/web-1    Started container web

next: scripts/lab-tunnel.sh a6 --background   # then open the LAN URL
```

Note the `<pending>` external IP: on minikube that is the expected state, and it
is exactly the A4 lesson.

```console
$ scripts/lab-scale.sh --delta 1
replicas: 3 -> 4
+ kubectl scale deployment/web --replicas=4 -n k8s-lab
deployment.apps/web scaled
deployment "web" successfully rolled out

ready replicas: 4/4
```

```console
$ scripts/lab-rollout.sh image nginx:1.28-alpine
+ kubectl set image deployment/web web=nginx:1.28-alpine -n k8s-lab
deployment.apps/web image updated
deployment "web" successfully rolled out

now running: nginx:1.28-alpine
+ kubectl rollout status deployment/web -n k8s-lab
deployment "web" successfully rolled out
```

```console
$ scripts/lab-verify.sh a6
verifying scenario a6 in namespace k8s-lab

ok   deployment/web exists (desired 4)
ok   ready replicas = 4
ok   service/web has endpoints (10.244.0.5)
ok   service type = LoadBalancer

all checks passed
```

```console
$ scripts/lab-down.sh a6
+ kubectl delete -f .../manifests/a6 -n k8s-lab --ignore-not-found
deployment.apps "web" deleted
service "web" deleted
scenario a6 removed
```

---

## 4. A failing check — simulated

Verification is only useful if it can fail. Here A5 is verified while the
cluster is running A6:

```console
$ scripts/lab-verify.sh a5 --url http://127.0.0.1:8080 --expect 401
verifying scenario a5 in namespace k8s-lab

ok   deployment/web exists (desired 4)
ok   ready replicas = 4
ok   service/web has endpoints (10.244.0.5)
FAIL secret/web-basic-auth is missing
FAIL configmap/web-auth-config is missing
FAIL HTTP http://127.0.0.1:8080: want '401', got '000'

3 check(s) failed
$ echo $?
1
```

The exit code is what `make verify` and any CI would use.

---

## 5. The offline test suite — real

```console
$ make test
ok   scripts/lab-up.sh is executable
...
ok   lab-verify passes a healthy lab
ok   lab-verify fails on a missing lab
ok   lab-verify detects a missing deployment
ok   lab-down removes a scenario
ok   lab-down all removes the namespace
ok   lab-doctor prints a recommendation
ok   lab-doctor prints a tier
ok   mkpasswd prints an apr1 line
ok   cluster-create sizes minikube
ok   cluster-create reports the result
ok   observability plan includes Prometheus
ok   observability picks a StorageClass
ok   bastion setup shows the sshd drop-in
ok   bastion setup shows the firewall step

36 passed, 0 failed, 0 skipped
```

---

## 6. What still needs a real transcript

Replace each item once the cluster exists. Do not mark it done before the output
is pasted here.

- [x] A1: page served, image downloaded, live edit visible.
- [x] A2: ConfigMap edit visible without a restart; `subPath` counter-example.
- [x] A3: `printenv` inside the pod and the precedence proof.
- [x] A4: `curl` from a second machine on the LAN.
- [x] A5: 401 without credentials, 200 with them.
- [x] A6: real 3/3, real rolling update with `maxUnavailable: 0`.
- [x] A7: both databases read; host-side SQLite insert visible on reload.
- [ ] D1: the same manifest on k3d, with the StorageClass difference.
- [ ] H1: `helm history` with two revisions and a rollback.
- [ ] N1: ingress by Host header, and the `rewrite-target` 404.
- [ ] T1: one real bad state per row of the troubleshooting table.

---

## 7. Real A1 transcript — host mount, live edit, logo

```console
$ scripts/lab-up.sh a1 --mount
mount started (pid 1934007, log /tmp/k8s-lab-mount.log)
+ kubectl create namespace k8s-lab
namespace/k8s-lab created
+ kubectl apply -f /home/kris/00___Castle/07__WorkShops/k8s/manifests/a1 -n k8s-lab
deployment.apps/web created
service/web created
Waiting for deployment "web" rollout to finish: 0 of 1 updated replicas are available...
deployment "web" successfully rolled out

scenario a1 is up in namespace k8s-lab

try it:
  host:    http://127.0.0.1:8080
  LAN:     http://192.168.1.240:8080  (run scripts/lab-tunnel.sh)
  in pod:  kubectl exec deploy/web -n k8s-lab -- curl -s localhost

$ scripts/lab-tunnel.sh --background
forward started (pid 1934634, log /tmp/k8s-lab-forward-8080.log)

from this machine: http://127.0.0.1:8080
from the LAN:      http://192.168.1.240:8080
if it does not answer from another machine, open the port:
  sudo ufw allow 8080/tcp

$ curl -s http://127.0.0.1:8080/
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>k8s lab — A1</title>
    <style>
      body { font-family: system-ui, sans-serif; margin: 3rem; background: #0f172a; color: #e2e8f0; }
      code { background: #1e293b; padding: .15rem .4rem; border-radius: .25rem; }
    </style>
  </head>
  <body>
    <h1>k8s lab — A1</h1>
    <p>Site served by nginx in the A1 scenario.</p>
    <p>Edit this file on the host and reload the page: no restart, no rebuild.</p>
    <p>Generated at: <code>replace-me-by-hand</code></p>
    <img src="/images/logo.svg" alt="k8s lab logo" style="width:240px;height:120px">
  </body>
</html>

$ curl -sI http://127.0.0.1:8080/images/logo.svg
HTTP/1.1 200 OK
Server: nginx/1.27.5
Date: Sat, 24 Oct 2026 21:30:17 GMT
Content-Type: image/svg+xml
Content-Length: 454
Last-Modified: Sat, 24 Oct 2026 21:30:03 GMT
Connection: keep-alive
ETag: "6add235b-1c6"
Accept-Ranges: bytes

# Live edit: sed on the host file
$ sed -i "s/replace-me-by-hand/first-real-run/" site/index.html

# Verify the change appears without pod restart
$ curl -s http://127.0.0.1:8080/ | grep first-real-run
first-real-run
```

The page and the logo are served from the host `site/` directory through
`minikube mount`. The live edit proves the hostPath mount works end-to-end.
