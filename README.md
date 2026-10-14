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

