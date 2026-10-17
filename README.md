\# Zero-Downtime Canary Deployment Pipeline



Canary and blue-green deployments with Argo Rollouts on Kubernetes,

with automated rollback driven by Prometheus metrics.



\## Status

Work in progress. Day 1 complete: app, Docker images, Rollout manifests, local canary tested.



\## Structure

\- `app/` sample app with /health, /metrics and a failure switch

\- `k8s/` Rollout and Service manifests

\- `docs/screenshots/` evidence of each stage



\## Evidence

!\[Canary at 50%](docs/screenshots/07-canary-in-progress.png)

!\[Manual abort](docs/screenshots/09-manual-abort.png)

## Security (IAM)

| Identity | Permissions | Why it is safe |
|---|---|---|
| `github-actions-ecr` role | Push images to the `demo-app` ECR repository only | GitHub authenticates with a short-lived OIDC token, so no AWS keys are stored in GitHub. The trust policy allows only this repository's `main` branch |
| `devops-lab` IAM user | AdministratorAccess | Used only from my laptop for this lab. For production I would use narrower permissions |

ECR image scanning is enabled on push.

## Cost estimate (EKS test day)

| Item | Approx. cost |
|---|---|
| EKS control plane | about $0.10 per hour |
| 2 x t3.medium worker nodes | about $0.09 per hour |
| NAT gateway and load balancer | about $0.07 per hour |
| **Total** | **about $0.25 to $0.30 per hour** |

The cluster is created for the test and deleted afterwards. The local kind cluster costs nothing.

## Troubleshooting notes

- **Prometheus target DOWN:** Flask's `/metrics` was sent as `text/html`, which newer Prometheus rejects. Fixed by returning `CONTENT_TYPE_LATEST`.
- **Argo Rollouts CRD install failed:** the CRDs exceed the annotation size limit, so I used `kubectl apply --server-side`.
- **OIDC login failed:** I decoded the token's `sub` claim and found GitHub now includes numeric owner and repo IDs. I updated the IAM trust policy to match the exact subject.

## Result

A deliberately bad release (50% errors) was detected through Prometheus metrics and rolled back automatically in about 38 seconds, with only 1 of 5 pods ever running the bad version.

