# PodDisruptionBudget — limit concurrent voluntary disruptions.
#
# Change: APP_NAME, MIN_AVAILABLE (or MAX_UNAVAILABLE).
# Bites:
#   - only one of minAvailable OR maxUnavailable (not both)
#   - counts pods matching selector; 0 means no pods may be evicted
#   - does NOT protect against involuntary disruptions (node failure, OOM)
#   - cluster autoscaler and kubectl drain respect it; node reboot may not
#   - for single-replica workloads, use maxUnavailable: 0 (or minAvailable: 1)
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{ APP_NAME }}-pdb
  labels:
    app.kubernetes.io/name: {{ APP_NAME }}
spec:
  minAvailable: {{ MIN_AVAILABLE }}
  selector:
    matchLabels:
      app.kubernetes.io/name: {{ APP_NAME }}