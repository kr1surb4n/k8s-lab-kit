---
id: doc-13
title: Ingress and the ingress-nginx controller
section: "Concepts > Networking > Ingress"
corpus_version: 2026-10-26.1
source:
  kind: authored
  snapshot: 2026-10-26
  based_on:
    - docs/runbooks.md#n1
    - paczki/k8s/ingress.yaml.tpl
---

An **Ingress** is an HTTP routing rule: host and path to a Service port. It does
nothing on its own. A controller must watch it and program a proxy. On minikube
the controller is installed with `minikube addons enable ingress`, which runs
`ingress-nginx` in the `ingress-nginx` namespace.

The N1 exercise applies the kit template `paczki/k8s/ingress.yaml.tpl` after
substituting the app name, host `app.example.com`, service `web`, and port 80.
It then sends a request with an explicit `Host` header to the address reported
in `status.loadBalancer.ingress[0].ip`.

Two traps are worth remembering:

- A `rewrite-target: /` annotation changes the path the backend receives and can
  break relative asset URLs. It is the most common bug in the PDF example.
- On the docker driver the ingress address is only reachable from the host;
  `minikube tunnel` or a host-side port-forward is needed for anything else.

Ingress is for HTTP. TLS terminates at the controller using a Secret, and TCP
services still need a Service of type NodePort or LoadBalancer.
