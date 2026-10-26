# AGENTS.md — Global Agent Instructions

## Mandatory Logging Policy

**Every response, every task, every piece of work MUST be logged.**

### Log Structure
Each task gets its own Markdown file in `work_logs/` with:
- **Task ID** and **Title**
- **User prompt** that initiated it
- **What was done** (step by step)
- **Why** (reasoning, references to specs/plans)
- **Errors encountered** and **how solved**
- **Commands run** with output
- **Files created/modified**
- **Verification steps** and results
- **Next steps** or blockers

### Log Naming
`work_logs/YYYY-MM-DD_HH-MM_task-slug.md`

### Required Content per Log Entry
```markdown
# Task: <title>

## User Prompt
> <exact user message>

## Plan Reference
- <link to spec/plan item>

## Actions Taken
1. <step 1> — <command/file>
2. <step 2> — <command/file>
...

## Errors & Solutions
| Error | Solution |
|-------|----------|
| ... | ... |

## Verification
- <test/command> — <result>

## Files Touched
- <file> — <what changed>

## Next Steps
- ...
```

### Enforcement
- **No task is complete** until its log file exists and is committed
- **Every git commit** must reference the log file
- **Agent must append** to log in real-time during work

---

## Current Active Plan
**kubernetes_plan.md** — 9-phase Kubernetes learning implementation

| Phase | Title | Status | Log File |
|-------|-------|--------|----------|
| 1 | Study 30% K8s docs (Pod, Service, Deployment, StatefulSet, CronJob, Ingress) | ☐ | |
| 2 | Config management: Kustomize + Helm study | ☐ | |
| 3 | Single-node K8s (k3s/minikube): nginx + Magento | ☐ | |
| 4 | Run all small K8s distros + Rancher | ☐ | |
| 5 | PHP + MySQL + Apache2 project (StatefulSet, reverse proxy, Dockerfiles, image repo) | ☐ | |
| 6 | Package Phase 5 as Helm Charts + Helm repo | ☐ | |
| 7 | Create Git repo over SSH | ☐ | |
| 8 | Package Phase 5 with Kustomize (dev/prod) | ☐ | |
| 9 | Argo CD for GitOps (Phases 6 & 8) | ☐ | |

---

## Existing Work Logs
*(Populated as work progresses)*

---

## Global Settings
- **Repository**: https://github.com/kr1surb4n/k8s-lab-kit
- **Working Dir**: `/home/kris/00___Castle/07__WorkShops/k8s`
- **Test Command**: `make test` (must pass 38/38)
- **Graph RAG Tests**: `cd ai/patterns/graph-rag && .venv/bin/python -m unittest discover -s app/tests` (55/55)