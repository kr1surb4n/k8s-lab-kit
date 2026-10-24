# HorizontalPodAutoscaler — scale replicas based on CPU / custom metrics.
#
# Change: APP_NAME, MIN_REPLICAS, MAX_REPLICAS, TARGET_CPU_UTILIZATION.
# Bites:
#   - needs metrics-server (minikube: minikube addons enable metrics-server)
#   - scales based on .spec.metrics; CPU is the only built-in metric
#   - custom metrics need Prometheus Adapter or a custom metrics pipeline
#   - stabilizationWindowSeconds prevents thrashing (default 300s)
#   - behavior.scaleDown / scaleUp policies let you tune responsiveness
#   - without resource requests on the container, HPA cannot calculate utilization
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ APP_NAME }}-hpa
  labels:
    app.kubernetes.io/name: {{ APP_NAME }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ APP_NAME }}
  minReplicas: {{ MIN_REPLICAS }}
  maxReplicas: {{ MAX_REPLICAS }}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ TARGET_CPU_UTILIZATION }}
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
        - type: Pods
          value: 4
          periodSeconds: 15
      selectPolicy: Max