# Zero-Downtime Canary Deployment with Automatic Rollback

[![build-and-push](https://github.com/damashekar0/zero-downtime-deploy/actions/workflows/build.yml/badge.svg)](https://github.com/damashekar0/zero-downtime-deploy/actions/workflows/build.yml)

A deployment pipeline that releases a new version of an app **a little at a time** (a canary release), checks the new version's health using **Prometheus metrics**, and **rolls back automatically** if the new version is failing. No human has to notice the problem or press a button.

Built with **Argo Rollouts**, **Prometheus**, **GitHub Actions**, **Amazon ECR** and **Amazon EKS**, and tested both on a local `kind` cluster and on a real EKS cluster.

## Result at a glance

| Environment | Bad release (50% errors) | Rollback time | Timed runs |
|---|---|---|---|
| Local kind cluster | Detected and rolled back automatically | 38 to 51 seconds | 2 |
| Amazon EKS | Detected and rolled back automatically | 33 to 38 seconds | 3 |

- Only **1 of 5 pods** ever ran the bad version.
- The 5 stable pods were never replaced, so users stayed on the good version.
- "Rollback time" means: from the `set image` command until Argo Rollouts reports the rollout as `Degraded` (aborted). It was measured with a PowerShell stopwatch (see [How the rollback time was measured](#how-the-rollback-time-was-measured)).

> Timer screenshots exist for 36 s and 38 s on EKS. The third EKS run (33 s) is backed by its failed AnalysisRun in the evidence, but has no timer screenshot.

---

## The idea in plain words

Imagine a restaurant that wants to change a recipe.

- **Normal deployment:** change the recipe for every customer at once. If it is bad, everyone gets a bad meal.
- **Canary deployment (this project):** serve the new recipe to **one table first**. A health inspector (**Prometheus**) watches how that table reacts. If it goes badly, the kitchen **automatically stops** and goes back to the old recipe. If it goes well, the new recipe goes to more tables, then everyone.

In this project:

| Restaurant | This project |
|---|---|
| The recipe | The app image (`demo-app:v1`, `v2`, `v3-bad`) |
| One table first | 1 canary pod out of 5 |
| The health inspector | Prometheus, measuring the success rate |
| The kitchen's rule | An Argo Rollouts `AnalysisTemplate`: success rate must be at least 95% |
| Going back to the old recipe | Automatic abort and rollback |

---

## Architecture

![Architecture](docs/architecture.png)

| Part | What it does |
|---|---|
| **GitHub + GitHub Actions** | Builds the Docker image on every push to `main` |
| **Amazon ECR** | Stores the images (`v1`, `v2`, `v3-bad`, and a tag per commit) |
| **Amazon EKS** (or kind locally) | The Kubernetes cluster that runs the app |
| **Argo Rollouts controller** | Replaces the normal Deployment and runs the canary steps |
| **Rollout `demo-app`** | Defines the steps: 20%, analysis, 50%, pause, 100% |
| **Service `demo-app`** | One stable address in front of the stable and canary pods |
| **Prometheus** | Collects `/metrics` from every app pod |
| **AnalysisTemplate and AnalysisRun** | Asks Prometheus for the canary's success rate, and decides pass or fail |
| **Load pod** | Sends steady fake traffic, so there are numbers to measure |

---

## How one release works

1. A new version of the image is set on the Rollout (`kubectl argo rollouts set image ...`).
2. Argo starts **1 canary pod** with the new image (20% of the pods).
3. Argo starts an **AnalysisRun**. Every 15 seconds it asks Prometheus: *"What fraction of the canary's requests returned status 200?"*
4. **If the success rate stays at or above 95%:** Argo moves to 50%, waits 30 seconds, then goes to 100%. The old pods are scaled down.
5. **If any check fails:** Argo **aborts** the rollout, scales the canary down to zero, and keeps the stable pods serving. The rollout shows `Degraded`, which here means "the update was rejected, the old version is still running."

The key rules, from `k8s/rollout.yaml` and `k8s/analysis-template.yaml`:

| Setting | Value | Meaning |
|---|---|---|
| Canary steps | 20%, analysis, 50%, 30 s pause, 100% | Gradual rollout |
| Check interval | 15 seconds | How often Prometheus is asked |
| Number of checks | 4 | A good release must pass all 4 |
| `failureLimit` | 0 | A single failed check aborts the release |
| Success rule | success rate of at least 95% (or no data yet) | Defined in `successCondition` |

---

## How the rollback time was measured

The app has a switch for failures: `ERROR_RATE`. The image `v3-bad` is built with `ERROR_RATE=0.5`, so **half of its requests return HTTP 500** on purpose.

```powershell
$sw = [Diagnostics.Stopwatch]::StartNew()
kubectl argo rollouts set image demo-app demo-app="$REG/demo-app:v3-bad"
do { Start-Sleep -Seconds 2; $phase = kubectl get rollout demo-app -o jsonpath='{.status.phase}' } until ($phase -eq "Degraded")
"Automatic rollback after {0:N0} seconds" -f $sw.Elapsed.TotalSeconds
```

The time is made up of the new pod starting, Prometheus collecting error data, and the analysis failing. In the logs the first two checks usually passed (the success rule allows "no data yet"), and a later check failed once errors showed up, which is why detection takes roughly 30 to 40 seconds with a 15-second interval. The timer polls every 2 seconds, so each number is accurate to about 2 seconds.

---

## Evidence

### On Amazon EKS

| Step | Screenshot |
|---|---|
| Cluster created, 2 nodes Ready | ![nodes](docs/screenshots/20-eks-nodes-ready.png) |
| EKS console, cluster Active | ![console](docs/screenshots/20b-eks-console-active.png) |
| Argo Rollouts and Prometheus running | ![argo and prometheus](docs/screenshots/21-eks-argo-prometheus-ready.png) |
| App deployed from ECR, Healthy | ![healthy](docs/screenshots/22-eks-rollout-healthy-v1.png) |
| Prometheus scraping 5 of 5 pods | ![targets](docs/screenshots/23-eks-prometheus-targets-up.png) |
| Good release: analysis running at 20% | ![analysis](docs/screenshots/24-eks-analysis-running.png) |
| Good release complete, v2 stable | ![good release](docs/screenshots/25-eks-good-release-complete.png) |
| **Bad release: analysis Failed, rollout aborted** | ![bad release](docs/screenshots/26-eks-bad-release-auto-rollback.png) |
| Analysis history: 1 passed, 2 failed | ![history](docs/screenshots/26b-eks-analysisruns-history.png) |
| Rollback time, 38 s | ![38s](docs/screenshots/27-eks-rollback-time-38s.png) |
| Rollback time, 36 s | ![36s](docs/screenshots/27b-eks-rollback-time-36s.png) |
| Cluster deleted, nothing left running | ![deleted](docs/screenshots/28-eks-deleted.png) |

Text copies of the final state are in [`docs/evidence`](docs/evidence).

### On the local kind cluster

| Step | Screenshot |
|---|---|
| Prometheus metrics with labels | ![metrics](docs/screenshots/14-prometheus-metrics.png) |
| Prometheus targets up | ![targets](docs/screenshots/14b-prometheus-targets-up.png) |
| Good release: analysis running | ![analysis](docs/screenshots/16-analysis-running.png) |
| Good release complete | ![complete](docs/screenshots/17-good-release-complete.png) |
| Bad release rolled back | ![rollback](docs/screenshots/18-bad-release-auto-rollback.png) |
| Rollback time | ![time](docs/screenshots/19-rollback-time.png) |

### CI/CD

| Step | Screenshot |
|---|---|
| Images in ECR | ![ecr](docs/screenshots/11-ecr-images.png) |
| GitHub Actions run, all steps green | ![actions](docs/screenshots/12-github-actions-green.png) |

---

## Tech stack

| Area | Tools |
|---|---|
| App | Python, Flask, `prometheus_client` |
| Containers | Docker |
| Orchestration | Kubernetes (kind locally, Amazon EKS 1.34 in the cloud) |
| Progressive delivery | Argo Rollouts (canary strategy) |
| Monitoring | Prometheus (Helm chart) |
| CI/CD | GitHub Actions with OIDC |
| Registry | Amazon ECR |
| Cluster tooling | eksctl, kubectl, Helm, AWS CLI |

---

## Repository structure

```
app/
  app.py                    Flask app: /, /health, /metrics, failure switch
  Dockerfile                Builds the image; VERSION and ERROR_RATE are build args
k8s/
  rollout.yaml              Argo Rollout (canary steps and analysis)
  service.yaml              Stable address in front of the pods
  analysis-template.yaml    Prometheus success-rate check
tools/
  load.yaml                 Pod that sends steady traffic
.github/workflows/
  build.yml                 Build and push the image to ECR using OIDC
docs/
  architecture.png          Architecture diagram
  screenshots/              Evidence for every stage
  evidence/                 Text output from the EKS run
```

### The sample app

| Endpoint | Purpose |
|---|---|
| `/` | Returns `Hello from <version>`, and counts the request as 200 or 500 |
| `/health` | Kubernetes readiness check |
| `/metrics` | Prometheus metrics (`http_requests_total` with `status` and `version` labels) |

The three images come from the same code:

| Image | Build arguments | Behaviour |
|---|---|---|
| `demo-app:v1` | `VERSION=v1` | Healthy |
| `demo-app:v2` | `VERSION=v2` | Healthy |
| `demo-app:v3-bad` | `VERSION=v3`, `ERROR_RATE=0.5` | Fails about half of its requests |

---

## Run it locally (free)

Requirements: Docker Desktop, kubectl, kind, Helm, and the Argo Rollouts kubectl plugin.

```powershell
# 1. Build the three images
docker build -t demo-app:v1 --build-arg VERSION=v1 ./app
docker build -t demo-app:v2 --build-arg VERSION=v2 ./app
docker build -t demo-app:v3-bad --build-arg VERSION=v3 --build-arg ERROR_RATE=0.5 ./app

# 2. Create the cluster and load the images
kind create cluster --name lab
kind load docker-image demo-app:v1 demo-app:v2 demo-app:v3-bad --name lab

# 3. Install Argo Rollouts (server-side apply is required, the CRDs are too large)
kubectl create namespace argo-rollouts
kubectl apply --server-side --force-conflicts -n argo-rollouts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml

# 4. Install Prometheus
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/prometheus -n monitoring --create-namespace --set alertmanager.enabled=false --set prometheus-pushgateway.enabled=false --set kube-state-metrics.enabled=false --set prometheus-node-exporter.enabled=false --set server.persistentVolume.enabled=false --set server.global.scrape_interval=10s

# 5. Deploy the app and the load generator
kubectl apply -f k8s/
kubectl apply -f tools/load.yaml
kubectl argo rollouts get rollout demo-app --watch

# 6. Good release, then bad release
kubectl argo rollouts set image demo-app demo-app=demo-app:v2
kubectl argo rollouts set image demo-app demo-app=demo-app:v3-bad
```

Clean up with `kind delete cluster --name lab`.

## Run it on Amazon EKS

1. Create the cluster:
   ```powershell
   eksctl create cluster --name rollouts-lab --region ap-south-1 --nodegroup-name workers --node-type t3.medium --nodes 2 --managed
   ```
2. Install Argo Rollouts and Prometheus with the same commands as above.
3. Push the images to ECR (the GitHub Actions workflow does this for new commits; the `v1`, `v2` and `v3-bad` tags were pushed with `docker push`).
4. Use copies of `k8s/rollout.yaml` and `tools/load.yaml` whose `image:` line is your ECR address (`<account>.dkr.ecr.ap-south-1.amazonaws.com/demo-app:v1`). The files in this repo use local names so no account number is published.
5. Release with the full ECR address:
   ```powershell
   kubectl argo rollouts set image demo-app demo-app="$REG/demo-app:v2"
   kubectl argo rollouts set image demo-app demo-app="$REG/demo-app:v3-bad"
   ```
6. **Delete the cluster when you finish:**
   ```powershell
   eksctl delete cluster --name rollouts-lab --region ap-south-1 --wait
   ```

### Cost

EKS costs about $0.25 to $0.30 per hour while it exists (control plane, 2 small nodes, NAT gateway). The cluster ran for roughly 2.5 hours and was deleted the same day, so the estimated cost is under $2. After deletion, the checks for instances, NAT gateways, Elastic IPs, volumes and load balancers were all empty (see `28-eks-deleted.png`). Only the ECR repository (a few cents a month) and free IAM objects remain.

---

## CI/CD without stored AWS keys

The workflow in `.github/workflows/build.yml` builds the image and pushes it to ECR. It does **not** use stored AWS access keys. Instead:

1. GitHub gives the workflow a short-lived identity token (**OIDC**).
2. AWS checks the token against an **IAM role trust policy** that allows only this repository's `main` branch.
3. The role can only push images to the `demo-app` ECR repository.

---

## Problems I hit and how I solved them

| Problem | What I found | Fix |
|---|---|---|
| **Prometheus targets were DOWN** | Prometheus showed `received unsupported Content-Type "text/html"`. Flask sent `/metrics` as a web page | Return the response with `CONTENT_TYPE_LATEST` (`15-troubleshooting-metrics-content-type.png`) |
| **Argo Rollouts install failed** | `metadata.annotations: Too long: may not be more than 262144 bytes` on two CRDs | Use `kubectl apply --server-side` |
| **GitHub Actions could not log in to AWS** | `Not authorized to perform sts:AssumeRoleWithWebIdentity` on every run | I added a debug step that decoded the token and found GitHub now puts numeric owner and repository IDs in the `sub` claim. I changed the IAM trust policy to match the exact subject (`12c-troubleshooting-oidc-failed.png`) |
| **Bad image address on EKS** | A PowerShell variable was empty in a new window, so the image became `/demo-app:v3-bad` and the pod showed `InvalidImageName` | Set the variable again, added a guard to the timing script, and noted that the stable pods kept serving the whole time (`29-troubleshooting-invalid-image-name.png`) |

---

## Security notes

- No AWS keys in the repository or in GitHub secrets for the pipeline (OIDC instead).
- The IAM role is limited to pushing to one ECR repository.
- ECR image scanning is enabled on push.
- Evidence text files had the AWS account number removed before they were saved.
- The lab used an IAM user with broad permissions from a laptop. In production I would use narrower permissions and a separate role for cluster access.

---

## Limitations and what I would do next

- **Traffic split is by pod ratio.** Without an ingress or service mesh, 1 of 5 pods is about 20% of requests, but not an exact percentage. An NGINX ingress or the AWS Load Balancer Controller would give exact weights.
- **Only canary is implemented.** Argo Rollouts also supports blue-green, which is not part of this repository yet.
- **The success rule allows "no data yet".** That avoids false failures while a new pod starts, but a very low-traffic service could slip through a check. A minimum request count would make it stricter.
- **Prometheus has no persistent storage.** Fine for a short test, not for production.
- **One region, one cluster, two nodes.** There is no autoscaling, and no alert is sent when a rollback happens.
- **Next steps:** exact traffic weights with an ingress, Slack or email notification on rollback, a latency check in addition to the error rate, and GitOps (Argo CD) to deploy the manifests.

---

## What this project demonstrates

- Progressive delivery with automated, metric-based rollback
- Observability with Prometheus (custom metrics, labels, PromQL)
- Containers, Kubernetes, Helm and infrastructure created with eksctl
- Secure CI/CD to AWS using OIDC instead of stored keys
- Cost control: build and test locally, run in the cloud only for the proof, delete the same day
- Debugging real faults and writing down the cause and the fix
