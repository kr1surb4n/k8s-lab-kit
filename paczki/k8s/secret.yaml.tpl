# Secret — demo credentials only. Never commit a real one.
#
# Change: APP_NAME, SECRET_KEY, SECRET_VALUE.
# Bites:
#   - base64 is encoding, not encryption; anyone with `get secret` reads it
#   - `stringData` is plain text in the file, `data` is base64 in the file
#   - mounted secrets can be 0400 and are updated; env secrets are not
#   - the value is visible in `kubectl describe pod`, in /proc/1/environ and
#     to every child process of the container
apiVersion: v1
kind: Secret
metadata:
  name: {{ APP_NAME }}
  labels:
    app.kubernetes.io/name: {{ APP_NAME }}
type: Opaque
stringData:
  # The key becomes the file name when mounted as a volume.
  {{ SECRET_KEY }}: "{{ SECRET_VALUE }}"
