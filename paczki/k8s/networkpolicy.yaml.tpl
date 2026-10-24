# NetworkPolicy — default-deny with explicit allow rules.
#
# Change: APP_NAME, NAMESPACE, INGRESS_FROM, EGRESS_TO.
# Bites:
#   - applies to pods matching podSelector; empty selector = all pods in namespace
#   - if no NetworkPolicy selects a pod, it is unisolated (allow all)
#   - combining Ingress + Egress in one policy = both must match to allow
#   - ipBlock with except lets you carve out CIDR exceptions
#   - namespaceSelector uses labels on the namespace, not the pod
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ APP_NAME }}-netpol
  namespace: {{ NAMESPACE }}
  labels:
    app.kubernetes.io/name: {{ APP_NAME }}
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: {{ APP_NAME }}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        {{ INGRESS_FROM }}
      ports:
        - protocol: TCP
          port: {{ CONTAINER_PORT }}
  egress:
    - to:
        {{ EGRESS_TO }}
      ports:
        - protocol: TCP
          port: 443
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53