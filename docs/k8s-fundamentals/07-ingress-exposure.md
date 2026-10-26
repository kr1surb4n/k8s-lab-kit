# Kubernetes Fundamentals — Service Exposure (Ingress, LoadBalancer, NodePort)

## The Problem

Pods have **ephemeral IPs** — they change on restart. Services give stable internal IPs, but **external access** requires additional layers.

## Exposure Methods Overview

| Method | Layer | Protocol | External Access | TLS | Path Routing | Cost |
|--------|-------|----------|-----------------|-----|--------------|------|
| **ClusterIP** | L4 | TCP/UDP | ❌ Internal only | ❌ | ❌ | Free |
| **NodePort** | L4 | TCP/UDP | ✅ NodeIP:Port | ❌ | ❌ | Free |
| **LoadBalancer** | L4 | TCP/UDP | ✅ Cloud LB IP | At LB | ❌ | $/LB |
| **Ingress** | L7 | HTTP/HTTPS | ✅ Via LB + Ingress | ✅ At Ingress | ✅ Path/Host | $/LB |
| **Gateway API** | L7 | HTTP/TCP | ✅ Via LB + Gateway | ✅ Flexible | ✅ Advanced | $/LB |

---

## 1. ClusterIP (Default, Internal Only)

```yaml
apiVersion: v1
kind: Service
spec:
  type: ClusterIP
  selector:
    app: my-app
  ports:
    - port: 80
      targetPort: 8080
```
- **Only accessible within cluster**
- Use for: Service-to-service communication
- **No external access**

---

## 2. NodePort

```yaml
spec:
  type: NodePort
  ports:
    - port: 80
      targetPort: 8080
      nodePort: 30080  # Optional (30000-32767)
```
- **Exposes on every node** at `NodeIP:nodePort`
- **No cloud LB needed** — works on bare metal, minikube
- **Limitations:**
  - Port range 30000-32767
  - 1 Service per port
  - Node IP changes (use external LB or DNS)
  - No TLS termination

---

## 3. LoadBalancer (L4)

```yaml
spec:
  type: LoadBalancer
  ports:
    - port: 80
      targetPort: 8080
  # loadBalancerClass: ""  # For specific LB implementation
```
- **Cloud provisions LB** (AWS ALB/NLB, GCP LB, Azure LB, OCI LB)
- **External IP** assigned automatically
- **Health checks** by cloud LB
- **Costs money** — 1 Service = 1 LB

### ExternalTrafficPolicy

```yaml
spec:
  externalTrafficPolicy: Local  # Preserve client IP, only local Pods
  # Cluster (default) = SNAT, Pod sees LB IP
```

---

## 4. Ingress (L7 HTTP/HTTPS)

### What is Ingress?
- **L7 HTTP router** — routes by host/path
- **TLS termination** at Ingress controller
- **Single LB** for multiple Services
- **Path/host based routing**

### Ingress Controller Required
| Controller | Features |
|------------|----------|
| **NGINX** | Most popular, mature, many annotations |
| **Traefik** | Auto-discovery, Let's Encrypt, metrics |
| **HAProxy** | High performance, enterprise |
| **Envoy** | Gateway API native, advanced |

### Ingress Resource

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx  # Matches IngressClass
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
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend-service
                port:
                  number: 80
  tls:
    - hosts: [app.example.com]
      secretName: app-tls  # Created by cert-manager
```

### Path Types
| Type | Matching |
|------|----------|
| **Exact** | Exact path match |
| **Prefix** | Path prefix (most common) |
| **ImplementationSpecific** | Controller-dependent |

### TLS with cert-manager

```yaml
# ClusterIssuer (Let's Encrypt)
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod-key
    solvers:
      - http01:
          ingress:
            class: nginx
```

```yaml
# Ingress references ClusterIssuer
annotations:
  cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts: [app.example.com]
      secretName: app-tls  # Auto-created
```

---

## 5. Gateway API (Next Generation)

### Why Gateway API?
- **Standardized** (vs vendor-specific Ingress annotations)
- **Role separation**: Infra (GatewayClass/Gateway) vs App (HTTPRoute)
- **Multi-protocol**: HTTP, TLS, TCP, UDP, GRPC
- **Extensible** — custom filters, policies

### Resources

```yaml
# 1. GatewayClass (Infra team)
apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: nginx
spec:
  controllerName: nginx.org/gateway-controller

---
# 2. Gateway (Infra team) — LB + listener
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: public-gateway
spec:
  gatewayClassName: nginx
  listeners:
    - name: http
      protocol: HTTP
      port: 80
      allowedRoutes:
        namespaces:
          from: All
    - name: https
      protocol: HTTPS
      port: 443
      tls:
        mode: Terminate
        certificateRefs:
          - kind: Secret
            name: gateway-tls

---
# 3. HTTPRoute (App team) — routing rules
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: app-route
spec:
  parentRefs:
    - name: public-gateway
  hostnames: ["app.example.com"]
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /api
      backendRefs:
        - name: api-service
          port: 80
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: frontend-service
          port: 80
```

---

## TCP/UDP Exposure (Non-HTTP)

### LoadBalancer (TCP)

```yaml
spec:
  type: LoadBalancer
  ports:
    - name: tcp-port
      protocol: TCP
      port: 3306
      targetPort: 3306
```

### LoadBalancer (UDP)

```yaml
spec:
  type: LoadBalancer
  ports:
    - name: dns
      protocol: UDP
      port: 53
      targetPort: 53
```
- **Provider support varies** — check cloud docs

### NodePort (TCP/UDP)

```yaml
spec:
  type: NodePort
  ports:
    - protocol: TCP
      port: 3306
      targetPort: 3306
      nodePort: 30306
    - protocol: UDP
      port: 53
      targetPort: 53
      nodePort: 30053
```

### Ingress (TCP/UDP) — NGINX Specific

```yaml
# ConfigMap for TCP/UDP services
apiVersion: v1
kind: ConfigMap
metadata:
  name: tcp-services
  namespace: ingress-nginx
data:
  "3306": "default/mysql:3306"
---
# In Ingress controller deployment:
# --tcp-services-configmap=ingress-nginx/tcp-services
```

---

## Comparison: Choosing the Right Method

### For HTTP/HTTPS Apps

| Scenario | Recommended |
|----------|-------------|
| Single app, simple | Ingress + LoadBalancer |
| Multiple apps, path routing | Ingress |
| Multiple apps, advanced routing | Gateway API |
| Need TLS termination | Ingress/Gateway + cert-manager |
| Internal only | ClusterIP + port-forward |

### For TCP/UDP (Databases, Custom Protocols)

| Scenario | Recommended |
|----------|-------------|
| Cloud, production | LoadBalancer (TCP) |
| Bare metal, no LB | NodePort |
| Internal only | ClusterIP + port-forward |
| Need client IP | LoadBalancer `externalTrafficPolicy: Local` |

---

## Architecture Patterns

### Pattern 1: Ingress + ClusterIP Services (Standard)
```
Internet → LoadBalancer → Ingress Controller (Service: LoadBalancer)
                                    ↓
                    Ingress routes by host/path
                                    ↓
                    Services (ClusterIP) → Pods
```

### Pattern 2: Gateway API (Modern)
```
Internet → LoadBalancer → Gateway (Listener)
                                    ↓
                    HTTPRoute/GRPCRoute → Services → Pods
```

### Pattern 3: Direct LoadBalancer per Service (Simple)
```
Internet → LoadBalancer (per Service) → Service (LoadBalancer) → Pods
```
- **Costly** — 1 LB per Service
- **No L7 features** — no path routing, no TLS at LB

---

## TLS Termination Locations

| Location | Pros | Cons |
|----------|------|------|
| **Ingress Controller** | Centralized, cert-manager integration | Single point |
| **LoadBalancer (AWS ALB, GCP LB)** | Offloads app, managed certs | Less flexible |
| **Application (Pod)** | End-to-end encryption | Cert management per app |
| **Service Mesh (mTLS)** | Zero-trust, auto-rotate | Complexity |

---

## Common Ingress Annotations (NGINX)

```yaml
annotations:
  # Rewrite
  nginx.ingress.kubernetes.io/rewrite-target: /
  
  # Rate limiting
  nginx.ingress.kubernetes.io/rate-limit: "100"
  nginx.ingress.kubernetes.io/rate-limit-window: "1m"
  
  # Auth
  nginx.ingress.kubernetes.io/auth-type: basic
  nginx.ingress.kubernetes.io/auth-secret: basic-auth
  nginx.ingress.kubernetes.io/auth-realm: "Auth Required"
  
  # CORS
  nginx.ingress.kubernetes.io/enable-cors: "true"
  nginx.ingress.kubernetes.io/cors-allow-origin: "*"
  
  # Proxy body size
  nginx.ingress.kubernetes.io/proxy-body-size: "10m"
  
  # TLS
  nginx.ingress.kubernetes.io/ssl-redirect: "true"
```

---

## Common Commands

```bash
# View Ingress
kubectl get ingress -A

# View Ingress details
kubectl describe ingress my-ingress

# View Ingress controller logs
kubectl logs -n ingress-nginx deploy/ingress-nginx-controller

# Test locally
kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 8080:80

# View Gateway API resources
kubectl get gatewayclass,gateway,httproute -A
```

---

## Best Practices

1. **Use Ingress for HTTP** — not LoadBalancer per Service
2. **Use cert-manager** — automate TLS certificates
3. **Use Gateway API** for new clusters — standard, extensible
4. **Use LoadBalancer for TCP** — databases, custom protocols
5. **Use ClusterIP + port-forward** for dev/internal access
6. **Set `ingressClassName`** — explicit, avoids conflicts
7. **Use annotations sparingly** — prefer Gateway API for complex routing
8. **Health checks** — configure on LoadBalancer and Ingress backend

---

## References

- [Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [Ingress Controllers](https://kubernetes.io/docs/concepts/services-networking/ingress-controllers/)
- [Gateway API](https://gateway-api.sigs.k8s.io/)
- [cert-manager](https://cert-manager.io/docs/)
- [NGINX Ingress Annotations](https://kubernetes.github.io/ingress-nginx/user-guide/nginx-configuration/annotations/)