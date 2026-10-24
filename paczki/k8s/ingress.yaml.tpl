# Ingress — HTTP routing by host and path. Needs an ingress controller.
#
# Change: APP_NAME, HOST, SERVICE_NAME, SERVICE_PORT.
# Bites:
#   - without a controller this object does nothing and has no ADDRESS
#   - `rewrite-target: /` plus `path: /app` breaks every relative asset;
#     omit the rewrite when the backend expects the full path
#   - pathType Prefix means "this path and everything under it"
#   - the Service must be in the same namespace as the Ingress
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ APP_NAME }}
  labels:
    app.kubernetes.io/name: {{ APP_NAME }}
  annotations:
    # Only needed when the backend lives under a subpath.
    # nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "false"
spec:
  # minikube: "nginx". k3s with Traefik: "traefik". Empty = the default class.
  ingressClassName: nginx
  rules:
    - host: {{ HOST }}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{ SERVICE_NAME }}
                port:
                  number: {{ SERVICE_PORT }}
