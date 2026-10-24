# Observability and traceability

The goal is not "a Grafana screenshot". It is to answer four questions for the
cluster **and** the hosts it talks to:

1. What is happening? (metrics)
2. What was said? (logs)
3. Where did the request spend its time? (traces)
4. Who changed it? (audit, Git, Kubernetes events)

## Layers and budget

| Layer | Component | Memory | Retention here |
|---|---|---|---|
| metrics | Prometheus + node-exporter + kube-state-metrics | ~600 MiB | 7 days |
| uptime | blackbox-exporter | ~40 MiB | none (probes) |
| dashboards | Grafana | ~200 MiB | none |
| logs | Loki single binary + Alloy/Promtail | ~300 MiB | 3 days |
| traces | Tempo single binary + OTel collector | ~350 MiB | 1 day |
| alerts | Alertmanager (optional) | ~60 MiB | none |

`minimal` (metrics + uptime + Grafana) fits next to the whole A1–A7 lab on a
6 GiB cluster. `logs` and `traces` fit one at a time. `full` is for a quiet
machine or a cloud node.

## Install

```bash
observability/install.sh --profile minimal
observability/install.sh --profile logs
observability/install.sh --profile traces
observability/install.sh --profile full
observability/install.sh --uninstall
```

Read the generated Grafana password:

```bash
kubectl get secret -n observability kube-prometheus-stack-grafana \
  -o jsonpath='{.data.admin-password}' | base64 -d; echo
kubectl port-forward -n observability svc/kube-prometheus-stack-grafana 3000:80
```

## Order of work

1. **Inventory first.** `inventory/hosts.yaml`. A host that is not in the
   inventory does not get a dashboard.
2. **Metrics outside the cluster.** `host/` runs Prometheus, node-exporter and
   blackbox on the LAN. If the cluster dies, the monitoring that watches it
   must still be alive.
3. **One trace id end to end.** Instrument one app (`trace/README.md`), then
   propagate `traceparent` through nginx and the database.
4. **Alerts on symptoms.** `alerts/lab-rules.yaml` ships four: pod crash loop,
   pod not ready, target down, disk filling.
5. **Retention is a budget.** The disk is shared with images and PVCs. Seven
   days of metrics and three of logs is the ceiling here.

## What "traceability" means for controlled hosts

- Every deployment carries `app.kubernetes.io/name`, `version`, and the Git SHA.
- Every request carries a W3C `traceparent`; the trace id is written in the log
  line of every service it touches.
- Every change is a Git commit or a `kubectl` event; the audit log and
  `last-applied-configuration` are kept.
- Every host has an owner and an expected port list in the inventory.

## Files

| Path | What |
|---|---|
| `install.sh` | profile-based installer |
| `values/` | trimmed Helm values for this hardware |
| `inventory/hosts.yaml` | the hosts and what to check |
| `alerts/lab-rules.yaml` | PrometheusRule for the lab |
| `host/` | monitoring that survives the cluster |
| `trace/` | how to add OpenTelemetry to an app |

Do not install `full` on a machine that is also building the A7 PHP image. The
build and the stack compete for the same 6 GiB.
