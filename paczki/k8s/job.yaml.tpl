# Job — run-to-completion workload (batch, migration, init).
#
# Change: APP_NAME, IMAGE, CONTAINER_CMD, COMPLETIONS, PARALLELISM.
# Bites:
#   - restartPolicy: OnFailure (default) or Never; Never means pod is not recreated
#   - backoffLimit: how many retries before marking Job failed (default 6)
#   - ttlSecondsAfterFinished: auto-cleanup finished Jobs (Kubernetes 1.23+)
#   - use a ConfigMap/Secret for the command if it's long; keep the template clean
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ APP_NAME }}
  labels:
    app.kubernetes.io/name: {{ APP_NAME }}
spec:
  completions: {{ COMPLETIONS }}
  parallelism: {{ PARALLELISM }}
  backoffLimit: 3
  ttlSecondsAfterFinished: 86400
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