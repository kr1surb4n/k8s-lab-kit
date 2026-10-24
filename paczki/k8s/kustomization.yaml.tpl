# Kustomization — one place for namespace and common labels.
#
# Change: APP_NAME.
# Bites:
#   - `namespace:` here overrides nothing inside the listed files; files with
#     an explicit namespace win, so keep the files namespace-free
#   - list only files that exist; kustomize fails otherwise
#   - `kubectl apply -k .` is the entry point, not `kubectl apply -f`
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: k8s-lab

commonLabels:
  app.kubernetes.io/part-of: {{ APP_NAME }}

resources:
  - deployment.yaml
  - service.yaml
  - configmap.yaml
  - secret.yaml
