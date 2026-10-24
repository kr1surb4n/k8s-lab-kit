# PersistentVolumeClaim — ask for disk space, let the cluster provide it.
#
# Change: PVC_NAME, STORAGE_SIZE, STORAGE_CLASS.
# Bites:
#   - storageClassName differs per distro: minikube=standard,
#     k3s=local-path, microk8s=microk8s-hostpath
#   - ReadWriteOnce binds to one node (fine for a single-node lab)
#   - deleting the PVC deletes the PV when the reclaim policy is Delete
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ PVC_NAME }}
  labels:
    app.kubernetes.io/name: {{ PVC_NAME }}
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: {{ STORAGE_CLASS }}
  resources:
    requests:
      storage: {{ STORAGE_SIZE }}
