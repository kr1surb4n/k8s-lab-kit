# Kubernetes Fundamentals — CronJob

## What is a CronJob?

A **CronJob** creates **Jobs** on a repeating schedule (like Unix cron). It's for:
- **Periodic tasks** (backups, reports, cleanup)
- **Batch processing** (daily/hourly)
- **Scheduled maintenance**

## CronJob Spec

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: backup
spec:
  schedule: "0 2 * * *"          # Cron expression (UTC)
  timezone: "Europe/Warsaw"      # Optional (default: UTC)
  successfulJobsHistoryLimit: 3  # Keep last 3 successful Jobs
  failedJobsHistoryLimit: 1      # Keep last 1 failed Job
  startingDeadlineSeconds: 100   # If missed, run within this window
  concurrencyPolicy: Forbid      # Allow | Forbid | Replace
  suspend: false                 # Pause schedule
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: backup
              image: my-backup:latest
              command: ["/bin/sh", "-c", "pg_dump ..."]
              env:
                - name: PGPASSWORD
                  valueFrom:
                    secretKeyRef:
                      name: db-secret
                      key: password
          restartPolicy: OnFailure  # OnFailure | Never
```

## Cron Schedule Format

```
* * * * *
│ │ │ └─ Day of week (0-7) (Sun=0 or 7)
│ │ └──── Month (1-12)
│ └────── Day of month (1-31)
└──────── Hour (0-23)
```

| Expression | Meaning |
|------------|---------|
| `0 2 * * *` | Daily at 02:00 UTC |
| `0 0 * * 0` | Weekly Sunday midnight |
| `0 0 1 * *` | Monthly 1st day midnight |
| `*/15 * * * *` | Every 15 minutes |
| `0 */6 * * *` | Every 6 hours |
| `0 9-17 * * 1-5` | Weekdays 9am-5pm hourly |

**Timezone:** Use `timezone: "Europe/Warsaw"` for local time (K8s 1.25+)

## Job Template

The `jobTemplate` defines the Job that runs each schedule:

```yaml
jobTemplate:
  spec:
    template:
      spec:
        containers:
          - name: worker
            image: my-job:latest
        restartPolicy: OnFailure  # OnFailure | Never
    # Job-level settings:
    backoffLimit: 3          # Retries before marking failed
    activeDeadlineSeconds: 300  # Max runtime
    ttlSecondsAfterFinished: 86400  # Auto-cleanup after 24h
```

## Concurrency Policy

| Policy | Behavior |
|--------|----------|
| **Allow** (default) | Multiple Jobs can run simultaneously |
| **Forbid** | Skip new Job if previous still running |
| **Replace** | Kill running Job, start new one |

```yaml
concurrencyPolicy: Forbid  # Don't overlap backups
```

## Starting Deadline

```yaml
startingDeadlineSeconds: 100
```
- If cluster down / scheduler busy, Job starts if within this window
- **0** = no deadline (run whenever possible)
- **Important** for: critical jobs that must run daily

## History Limits

```yaml
successfulJobsHistoryLimit: 3  # Keep 3 successful (default 3)
failedJobsHistoryLimit: 1      # Keep 1 failed (default 1)
```
- **Set to 0** to disable history (cleaner, but no debugging)
- Jobs cleaned up by controller after completion

## Manual Execution

```bash
# Create Job manually from CronJob (one-off)
kubectl create job --from=cronjob/backup manual-backup-$(date +%s)

# Or with specific params
kubectl create job --from=cronjob/backup manual-backup \
  --dry-run=client -o yaml | kubectl apply -f -
```

## Suspend/Resume

```yaml
suspend: true  # Pause schedule
```

```bash
# Toggle
kubectl patch cronjob backup -p '{"spec":{"suspend":true}}'
kubectl patch cronjob backup -p '{"spec":{"suspend":false}}'
```

## Common Commands

```bash
# Create
kubectl apply -f cronjob.yaml

# List
kubectl get cronjobs

# View schedule + last run
kubectl get cronjob backup -o wide

# View Jobs created by CronJob
kubectl get jobs --selector=cronjob-name=backup

# View Job logs
kubectl logs job/backup-27482910

# Describe (see schedule, last run, next run)
kubectl describe cronjob backup

# Suspend/Resume
kubectl patch cronjob backup -p '{"spec":{"suspend":true}}'
kubectl patch cronjob backup -p '{"spec":{"suspend":false}}'

# Delete (also deletes created Jobs)
kubectl delete cronjob backup
```

## Job vs CronJob

| Feature | Job | CronJob |
|---------|-----|---------|
| **Runs** | Once (or on failure retry) | On schedule (repeating) |
| **Use case** | One-time batch, migration | Periodic backup, cleanup, reports |
| **Created by** | User | CronJob controller |
| **Schedule** | None | Cron expression |

## Job Spec (for reference)

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: my-job
spec:
  template:
    spec:
      containers:
        - name: worker
          image: my-job:latest
      restartPolicy: OnFailure
  backoffLimit: 3           # Retries
  activeDeadlineSeconds: 300  # Timeout
  ttlSecondsAfterFinished: 86400  # Auto-cleanup
  completions: 1            # How many Pods must succeed
  parallelism: 1            # Max parallel Pods
```

## Advanced Patterns

### Parallel Jobs (Work Queue)
```yaml
spec:
  completions: 10      # Total work items
  parallelism: 3       # 3 Pods at a time
  template:
    spec:
      containers:
        - name: worker
          image: my-worker
          env:
            - name: WORK_ITEM
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
```

### Job with Index (K8s 1.25+)
```yaml
spec:
  completions: 5
  parallelism: 5
  completionMode: Indexed
  template:
    spec:
      containers:
        - name: worker
          image: my-worker
          env:
            - name: JOB_INDEX
              valueFrom:
                fieldRef:
                  fieldPath: metadata.annotations['batch.kubernetes.io/job-completion-index']
```

## Best Practices

1. **Set `restartPolicy: OnFailure`** — required for Jobs
2. **Use `backoffLimit`** — prevent infinite retries
3. **Set `activeDeadlineSeconds`** — prevent stuck Jobs
4. **Use `ttlSecondsAfterFinished`** — auto-cleanup
5. **Use `concurrencyPolicy: Forbid`** — for long-running jobs (backups)
6. **Set `startingDeadlineSeconds`** — handle scheduler downtime
7. **Limit history** — `successfulJobsHistoryLimit: 3`
8. **Use secrets for credentials** — not in image/env
9. **Test manually first** — `kubectl create job --from=cronjob/...`

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Job not created | Schedule syntax error | Validate cron expression |
| Job stuck Pending | No resources / PVC | Check node capacity, PVC binding |
| Job runs multiple times | `concurrencyPolicy: Allow` | Use `Forbid` or `Replace` |
| Job never runs | Scheduler down, deadline missed | Increase `startingDeadlineSeconds` |
| Old Jobs not cleaned | History limits high | Lower `successfulJobsHistoryLimit` |
| Pod fails immediately | Command error | Check logs, command syntax |

## References

- [CronJobs](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)
- [Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/)
- [Cron Expression](https://crontab.guru/)
- [Job Patterns](https://kubernetes.io/docs/concepts/workloads/controllers/jobs-run-to-completion/)