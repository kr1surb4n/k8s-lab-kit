# CronJob — recurring or one-off batch work.
#
# Change: APP_NAME, IMAGE, SCHEDULE, CONTAINER_CMD.
# Bites:
#   - .spec.jobTemplate.spec.template.spec.restartPolicy must be OnFailure or Never
#   - concurrencyPolicy: Forbid (default) skips new run if previous still running
#   - successfulJobsHistoryLimit / failedJobsHistoryLimit keep history bounded
apiVersion: batch/v1
kind: CronJob
metadata:
  name: {{ APP_NAME }}
  labels:
    app.kubernetes.io/name: {{ APP_NAME }}
spec:
  schedule: "{{ SCHEDULE }}"
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        metadata:
          labels:
            app.kubernetes.io/name: {{ APP_NAME }}
        spec:
          restartPolicy: OnFailure
          containers:
            - name: {{ APP_NAME }}
              image: {{ IMAGE }}
              imagePullPolicy: IfNotPresent
              command: {{ CONTAINER_CMD }}
              resources:
                requests:
                  cpu: 10m
                  memory: 32Mi
                limits:
                  memory: 128Mi