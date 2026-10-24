# Service — a stable name and a load balancer in front of the pods.
#
# Change: APP_NAME, SERVICE_TYPE, PORT, TARGET_PORT.
# Bites:
#   - the selector must match the pod labels, or the Service has no endpoints
#   - LoadBalancer on minikube stays <pending> until `minikube tunnel`
#   - NodePort is not reachable from the LAN through the docker driver
apiVersion: v1
kind: Service
metadata:
  name: {{ APP_NAME }}
  labels:
    app.kubernetes.io/name: {{ APP_NAME }}
spec:
  # ClusterIP = inside the cluster only, NodePort = high port on every node,
  # LoadBalancer = ask the platform for an external IP.
  type: {{ SERVICE_TYPE }}
  selector:
    app.kubernetes.io/name: {{ APP_NAME }}
  ports:
    - name: http
      protocol: TCP
      port: {{ PORT }}
      targetPort: {{ TARGET_PORT }}
