# Spec: On-Call Process Boilerplate

## Problem Statement
The repository has recovery drills (`recovery/`, `scripts/lab-drill.sh`) but no documented **on-call process** — the human workflow for responding to production incidents. This spec defines an extensible, boilerplate on-call process that can be adopted by teams using this lab kit as a starting point.

## What an On-Call Process Covers
1. **Rotation** — schedule, handoff, escalation
2. **Alert routing** — how alerts reach the on-call engineer
3. **Triage runbook** — first 15 minutes: acknowledge, assess, mitigate
4. **Incident command** — roles (IC, scribe, comms), severity levels
5. **Communication** — status page, Slack/Teams, stakeholder updates
6. **Post-incident** — blameless postmortem, action items, follow-up
7. **Tooling** — what the on-call engineer needs at 3 AM

## Requirements
- **Extensible** — new alert types, new services, new runbooks plug in without rewriting
- **Tool-agnostic core** — works with PagerDuty, Opsgenie, VictorOps, Grafana OnCall, or plain Alertmanager → webhook
- **Documented as code** — rotation in Git, runbooks in `docs/runbooks/`, drills in `recovery/`
- **Practiced** — weekly/monthly drill schedule, not just documented

## Proposed Structure

```
oncall/
├── rotation/
│   ├── schedule.yaml           # who is on-call when (weekly, follows team calendar)
│   ├── handoff-checklist.md    # what to pass to next person
│   └── escalation.yaml         # L1 → L2 → manager, with timeouts
├── alert-routing/
│   ├── alertmanager-config.yaml    # routes: critical → page, warning → ticket
│   ├── notification-templates/     # Slack, SMS, email templates
│   └── silence-rules.yaml          # planned maintenance windows
├── runbooks/
│   ├── index.md                  # table of contents, search tips
│   ├── SEV-definitions.md        # SEV-1/2/3 criteria, response times
│   ├── triage.md                 # universal first-15-min checklist
│   ├── communications.md         # status page, Slack channels, templates
│   ├── postmortem-template.md    # blameless postmortem structure
│   └── services/                 # one per service
│       ├── graph-rag-api.md
│       ├── postgres-age.md
│       ├── prometheus.md
│       └── ...
├── drills/
│   ├── schedule.md               # weekly drill calendar
│   ├── scenarios/                # inject scripts + expected outcomes
│   │   ├── graph-rag-api-down.md
│   │   ├── postgres-oom.md
│   │   ├── prometheus-disk-full.md
│   │   └── ...
│   └── results/                  # drill outcomes, action items
└── tooling/
    ├── oncall-cli/               # small wrapper: `oncall ack`, `oncall status`, `oncall runbook <name>`
    ├── dashboard-links.md        # Grafana, Kibana, Jaeger, cluster URLs
    └── access.md                 # how to get kubectl, ssh, db access at 3 AM
```

## Triage Runbook (Universal First 15 Minutes)

```markdown
# Triage Checklist — First 15 Minutes

1. **Acknowledge** (≤ 2 min)
   - [ ] Acknowledge alert in PagerDuty/Alertmanager
   - [ ] Open incident channel (`#incident-<service>-<date>`)
   - [ ] Post: "IC: @me, investigating <alert>"

2. **Assess** (≤ 5 min)
   - [ ] Check dashboard: <link to service dashboard>
   - [ ] Run: `kubectl -n <ns> get pods,events --sort-by=.metadata.creationTimestamp`
   - [ ] Check: recent deployments (`argo rollouts` / `kubectl rollout history`)
   - [ ] Check: logs (`stern <pod> --since 10m`)

3. **Classify Severity** (≤ 2 min)
   - SEV-1: User-facing outage, data loss, security breach → page L2 immediately
   - SEV-2: Degraded performance, partial outage → ticket + investigate
   - SEV-3: Non-urgent, background task → ticket, next business day

4. **Mitigate** (≤ 5 min)
   - [ ] If recent deploy: `kubectl rollout undo deploy/<name> -n <ns>`
   - [ ] If OOM: increase limit, restart pod
   - [ ] If disk full: clean logs, expand PVC
   - [ ] If dependency down: check dependency runbook

5. **Communicate** (ongoing)
   - [ ] Update incident channel every 10 min
   - [ ] Post to status page if user-facing
   - [ ] Tag stakeholders per SEV-definitions
```

## Escalation Policy Example

```yaml
# oncall/rotation/escalation.yaml
levels:
  - name: L1 (Primary On-Call)
    timeout: 5m
    notify: [pagerduty, slack]
    if_unacked: escalate
  - name: L2 (Secondary / Team Lead)
    timeout: 10m
    notify: [pagerduty, slack, phone]
    if_unacked: escalate
  - name: L3 (Engineering Manager)
    timeout: 15m
    notify: [pagerduty, phone, email]
    if_unacked: notify_vp
```

## Drill Schedule (Extensible)

| Frequency | Drill Type | Example |
|---|---|---|
| Weekly | Single-service failure inject + recover | `scripts/lab-drill.sh crashloop --inject` |
| Bi-weekly | Multi-service cascade | Postgres down → Graph RAG API degrades → alert fires |
| Monthly | Full SEV-1 simulation | 30-min timeboxed: detect, mitigate, communicate, postmortem |
| Quarterly | Cross-team / disaster recovery | Restore from backup, failover to another cluster |

## Tooling: Minimal On-Call CLI

```bash
# oncall ack <alert-id>           # acknowledge in Alertmanager/PagerDuty
# oncall status                   # show current on-call, active alerts
# oncall runbook <service>        # open runbook in editor/browser
# oncall dashboard <service>      # open Grafana dashboard
# oncall escalate                 # manual escalation to next level
# oncall handoff                  # generate handoff note for next shift
```

Implemented as a thin wrapper around `kubectl`, `stern`, `gh`, `pd` (PagerDuty CLI), `amtool`.

## Integration with Existing Recovery Drills

| Existing | On-Call Extension |
|---|---|
| `scripts/lab-drill.sh crashloop\|imagepull\|pending\|oom --inject\|--recover` | Add `--scenario` flag, map to runbook, record drill result in `oncall/drills/results/` |
| `recovery/method.md` (Observe → Contain → Diagnose → Recover → Prevent) | Adopt as the **triage methodology** in `runbooks/triage.md` |
| `recovery/decision-tree.md` | Convert to interactive CLI: `oncall diagnose <symptom>` |

## Acceptance Criteria
- `oncall/` directory exists with all subdirectories
- `rotation/schedule.yaml` can be parsed by a script to generate calendar invites
- `runbooks/triage.md` is the universal first-15-min checklist
- Each service in `runbooks/services/` has: symptoms, dashboards, common mitigations, dependencies
- `drills/schedule.md` has at least 4 scenarios mapped to existing `lab-drill.sh` drills
- `oncall-cli` (or `Makefile` targets) implements the 6 commands above
- One full SEV-1 simulation drill completed and postmortem written

## References
- `recovery/method.md` — the 5-step method
- `recovery/decision-tree.md` — decision tree for common failures
- `scripts/lab-drill.sh` — inject/recover scripts
- `docs/runbooks.md` §T1 — existing troubleshooting drills
- Google SRE Workbook: "On-Call" chapter
- PagerDuty/Incident.io/Rootly runbook templates