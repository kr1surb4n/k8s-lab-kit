# Helm values — override a chart without editing it.
#
# Change: IMAGE_REPOSITORY, IMAGE_TAG, REPLICAS.
# Bites:
#   - key names are chart-specific; read `helm show values <chart>` first
#   - the Bitnami catalogue changed; do not trust old tag examples
#   - `helm upgrade --reuse-values` silently keeps old settings; prefer an
#     explicit -f file like this one
replicaCount: {{ REPLICAS }}

image:
  repository: {{ IMAGE_REPOSITORY }}
  tag: {{ IMAGE_TAG }}
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80

resources:
  requests:
    cpu: 50m
    memory: 64Mi
  limits:
    memory: 256Mi

# Keep the probes: they are what makes a rolling update zero-downtime.
readinessProbe:
  enabled: true
livenessProbe:
  enabled: true
