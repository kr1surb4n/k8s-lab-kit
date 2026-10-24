# Deployment — the workload that keeps N replicas alive.
#
# Change: APP_NAME, IMAGE, REPLICAS, CONTAINER_PORT.
# Bites:
#   - selector is immutable; changing matchLabels means delete + apply
#   - no readinessProbe means broken pods receive traffic during a rollout
#   - memory limit below the app's real usage ends in OOMKilled (exit 137)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ APP_NAME }}
  labels:
    app.kubernetes.io/name: {{ APP_NAME }}
spec:
  replicas: {{ REPLICAS }}
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ APP_NAME }}
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app.kubernetes.io/name: {{ APP_NAME }}
    spec:
      containers:
        - name: {{ APP_NAME }}
          image: {{ IMAGE }}
          imagePullPolicy: IfNotPresent
          ports:
            - name: http
              containerPort: {{ CONTAINER_PORT }}
          env:
            - name: APP_ENV
              value: "lab"
          # A readiness probe keeps traffic away until the app answers.
          readinessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 2
            periodSeconds: 5
          # A liveness probe restarts a hung container; keep it forgiving.
          livenessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 10
            periodSeconds: 10
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              memory: 256Mi
