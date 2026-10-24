# RBAC — Role + RoleBinding (namespace-scoped) or ClusterRole + ClusterRoleBinding.
#
# Change: APP_NAME, NAMESPACE, VERBS, RESOURCES, API_GROUPS.
# Bites:
#   - Role is namespace-scoped; ClusterRole is cluster-scoped
#   - RoleBinding binds a Role to subjects in ONE namespace
#   - ClusterRoleBinding binds a ClusterRole (or Role) to subjects cluster-wide
#   - subjects: User, Group, or ServiceAccount (most common for workloads)
#   - prefer Role/RoleBinding; use ClusterRole only for cluster-wide resources
#   - least privilege: list only the verbs/resources the workload actually needs
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: {{ APP_NAME }}-role
  namespace: {{ NAMESPACE }}
rules:
  - apiGroups: {{ API_GROUPS }}
    resources: {{ RESOURCES }}
    verbs: {{ VERBS }}
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: {{ APP_NAME }}-rolebinding
  namespace: {{ NAMESPACE }}
subjects:
  - kind: ServiceAccount
    name: {{ APP_NAME }}
    namespace: {{ NAMESPACE }}
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: {{ APP_NAME }}-role