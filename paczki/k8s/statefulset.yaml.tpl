# StatefulSet — stable identity, ordered rollout, persistent storage.
#
# Change: APP_NAME, IMAGE, REPLICAS, CONTAINER_PORT, STORAGE_CLASS, STORAGE_SIZE.
# Bites:
#   - pod names are sticky (web-0, web-1...); DNS is <pod>.<service>
#   - volumeClaimTemplates create a PVC per pod; deleting the set deletes PVCs
#   - RollingUpdate with partition lets you pause mid-rollout
#   - serviceName must match a headless Service for stable DNS
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: {{ APP_NAME }}
  labels:
    app.kubernetes.io/name: {{ APP_NAME }}
spec:
  serviceName: {{ APP_NAME }}-headless
  replicas: {{ REPLICAS }}
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ APP_NAME }}
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
          volumeMounts:
            - name: data
              mountPath: /data
          readinessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            requests:
              cpu: 50m
              memory: 64Mi
            limits:
              memory: 256Mi
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: [ "ReadWriteOnce" ]
        storageClassName: {{ STORAGE_CLASS }}
        resources:
          requests:
            storage: {{ STORAGE_SIZE }}
---
# Headless service for stable pod DNS (web-0.{{ APP_NAME }}-headless, ...)
apiVersion: v1
kind: Service
metadata:
  name: {{ APP_NAME }}-headless
  labels:
    app.kubernetes.io/name: {{ APP_NAME }}
spec:
  clusterIP: None
  selector:
    app.kubernetes.io/name: {{ APP_NAME }}
  ports:
    - name: http
      port: {{ CONTAINER_PORT }}
      targetPort: http