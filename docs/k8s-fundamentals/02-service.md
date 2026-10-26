# Kubernetes Fundamentals — Service

## What is a Service?

A **Service** is an abstraction that defines a logical set of Pods and a policy for accessing them. It provides:
- **Stable IP** (ClusterIP) and DNS name
- **Load balancing** across Pods
- **Service discovery** via DNS/environment variables

## Service Types

| Type | Description | Use Case |
|------|-------------|----------|
| **ClusterIP** (default) | Internal IP only, accessible within cluster | Internal service-to-service communication |
| **NodePort** | Exposes on each node's IP at static port (30000-32767) | External access without LB, dev/testing |
| **LoadBalancer** | Provisions external LB (cloud), assigns external IP | Production external access |
| **ExternalName** | Maps to DNS name (CNAME), no proxy | External services, migration |

## Service Spec

```yaml
apiVersion: v1
kind: Service
metadata:
  name: my-service
  labels:
    app: my-app
spec:
  type: ClusterIP  # ClusterIP | NodePort | LoadBalancer | ExternalName
  selector:
    app: my-app    # Selects Pods with this label
  ports:
    - name: http
      protocol: TCP
      port: 80        # Service port (clients connect here)
      targetPort: 8080 # Pod port (forwarded to)
      nodePort: 30080 # Only for NodePort (optional, auto-assigned if omitted)
  # sessionAffinity: None | ClientIP  # Sticky sessions
```

## How Service Selects Pods

- **Label selector** (`spec.selector`) matches Pod labels
- **Endpoints** controller watches Pods and updates Endpoints object
- **kube-proxy** on each node programs iptables/IPVS rules for load balancing

```bash
# View endpoints
kubectl get endpoints my-service
# Or
kubectl get ep my-service
```

## Service Discovery

### DNS (CoreDNS)
```
# Format: <service-name>.<namespace>.svc.cluster.local
my-service.default.svc.cluster.local  # Full
my-service.default                    # Short (same namespace)
my-service                            # Shortest (same namespace)
```

### Environment Variables (injected at Pod start)
```
MY_SERVICE_SERVICE_HOST=10.96.1.42
MY_SERVICE_SERVICE_PORT=80
MY_SERVICE_PORT=tcp://10.96.1.42:80
```

## Service Variants Deep Dive

### 1. ClusterIP (Default)
- **Virtual IP** only exists in cluster
- **kube-proxy** handles load balancing (iptables/IPVS)
- **No external access** — use Ingress or port-forward for outside

```yaml
spec:
  type: ClusterIP
  clusterIP: 10.96.1.42  # Can specify, or auto-assigned
```

### 2. NodePort
- Opens **same port on every node** (range 30000-32767)
- Traffic: `NodeIP:nodePort` → Service → Pod
- **Works on any cluster** (no cloud LB needed)
- **Limitations**: Port range, 1 Service per port, node IP changes

```yaml
spec:
  type: NodePort
  ports:
    - port: 80
      targetPort: 8080
      nodePort: 30080  # Optional, auto-assign if omitted
```

### 3. LoadBalancer
- **Cloud provider provisions LB** (AWS ALB/NLB, GCP LB, Azure LB, OCI LB)
- **External IP** assigned to Service
- **Health checks** handled by cloud LB
- **Costs money** — each Service = 1 LB

```yaml
spec:
  type: LoadBalancer
  loadBalancerClass: ""  # Optional, for specific LB implementation
  # externalTrafficPolicy: Local  # Preserve client source IP
```

### 4. ExternalName
- **No selector, no ports, no endpoints**
- Returns **CNAME** record pointing to external DNS
- Useful for: external databases, legacy systems, migration

```yaml
spec:
  type: ExternalName
  externalName: mydb.example.com
```

## Headless Service (ClusterIP: None)

- **No ClusterIP assigned**
- **No load balancing** — DNS returns **Pod IPs directly**
- Used with **StatefulSets** for stable network identity
- Pod DNS: `<pod-name>.<service-name>.<namespace>.svc.cluster.local`

```yaml
spec:
  clusterIP: None
  selector:
    app: my-stateful-app
```

## Service Exposure Methods (HTTP + TCP)

### HTTP/HTTPS Exposure

| Method | Description | TLS Termination | Path Routing |
|--------|-------------|-----------------|--------------|
| **Ingress** | L7 HTTP router, paths/hosts | At Ingress controller | Yes (path/host) |
| **LoadBalancer + Ingress** | LB + Ingress controller | At Ingress or LB | Yes |
| **Gateway API** | Newer, more expressive | Flexible | Advanced |

### TCP/UDP Exposure

| Method | Description |
|--------|-------------|
| **LoadBalancer (TCP)** | Direct TCP passthrough, LB health checks |
| **LoadBalancer (UDP)** | For DNS, syslog, etc. (provider support varies) |
| **NodePort (TCP/UDP)** | Direct node port access |
| **HostPort** | Pod port → node port (anti-pattern, avoids CNI) |
| **HostNetwork** | Pod uses node network namespace (anti-pattern) |

### Ingress Example (NGINX)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api-service
                port:
                  number: 80
  tls:
    - hosts: [app.example.com]
      secretName: app-tls  # TLS cert from cert-manager
```

---

## Service Networking Details

### kube-proxy Modes
| Mode | Mechanism | Performance |
|------|-----------|-------------|
| **iptables** (default) | DNAT rules per Service | Good for <1000 Services |
| **IPVS** | Kernel IPVS, hash tables | Better for >1000 Services |
| **nftables** | Newer, replaces iptables | Similar to IPVS |

### ExternalTrafficPolicy (LoadBalancer/NodePort)
| Policy | Behavior |
|--------|----------|
| **Cluster** (default) | SNAT → Pod sees LB IP, load balanced across all nodes |
| **Local** | No SNAT → Pod sees real client IP, only local Pods receive traffic |

## Multi-Port Services

```yaml
spec:
  ports:
    - name: http
      port: 80
      targetPort: 8080
    - name: https
      port: 443
      targetPort: 8443
    - name: grpc
      port: 9000
      targetPort: 9000
```

## Common Commands

```bash
# Create Service
kubectl expose deployment my-deploy --port=80 --target-port=8080 --type=ClusterIP

# View Service
kubectl get svc my-service -o wide

# View endpoints
kubectl get endpoints my-service

# Describe (see selector, endpoints, events)
kubectl describe svc my-service

# Port forward for local testing
kubectl port-forward svc/my-service 8080:80

# Delete
kubectl delete svc my-service
```

## Best Practices

1. **Use ClusterIP for internal** — default, simplest
2. **Use Ingress for HTTP** — not LoadBalancer per Service
3. **Label Pods consistently** — selector matches labels
4. **Name ports** — enables protocol-specific config
4. **Headless for StatefulSets** — stable DNS per Pod
5. **ExternalName for external deps** — no proxy overhead
6. **Avoid NodePort in prod** — use Ingress + LoadBalancer

## References

- [Service](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Service Types](https://kubernetes.io/docs/concepts/services-networking/service/#publishing-services-service-types)
- [Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [DNS for Services and Pods](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)
- [Gateway API](https://gateway-api.sigs.k8s.io/)