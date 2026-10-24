# ConfigMap — configuration that lives next to the pod, not in the image.
#
# Change: APP_NAME, ENV_NAME, ENV_VALUE, and the file block at the bottom.
# Bites:
#   - 1 MiB total, UTF-8 only: no images, no binaries
#   - keys must match [-._a-zA-Z0-9]
#   - env vars from a ConfigMap do NOT update until the pod is recreated
#   - a volume mount DOES update (about a minute), unless you used subPath
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ APP_NAME }}
  labels:
    app.kubernetes.io/name: {{ APP_NAME }}
data:
  # Simple key/value pairs, usable with envFrom or a single env valueFrom.
  {{ ENV_NAME }}: "{{ ENV_VALUE }}"

  # A whole file. The key becomes the file name when mounted as a volume.
  # Replace the body with the real content; keep the indentation.
  app-settings.json: |
    {
      "cache_ttl": 3600,
      "enable_telemetry": false
    }
