# ðŸ³ Docker Swarm with Jenkins CI/CD

A complete CI/CD project on AWS: **Jenkins** builds Docker images from GitHub, pushes them to **Docker Hub**, and deploys them as replicated services on a **Docker Swarm** cluster using `docker stack`.

---

## ðŸ“Œ Project Overview

| Item | Details |
|------|---------|
| Cloud | AWS EC2 (Amazon Linux 2023, Mumbai region) |
| Cluster | Docker Swarm â€“ 1 Manager + 2 Workers |
| CI/CD | Jenkins Pipeline (parameterized) |
| Registry | Docker Hub |
| Source | GitHub (`Dockerfile` + `docker-compose.yml`) |
| Apps | InternetBanking, MobileBanking, Insurance, Loans |

## ðŸ”„ Workflow

```
GitHub  â”€â”€â–º  Jenkins Pipeline  â”€â”€â–º  Docker Build  â”€â”€â–º  Tag  â”€â”€â–º  Push (Docker Hub)  â”€â”€â–º  docker stack deploy (Swarm)
```

Pipeline stages: **checkout â†’ build â†’ tag â†’ push â†’ deploy**

## ðŸ–¥ï¸ Infrastructure

| Node | Instance Type | Role |
|------|---------------|------|
| Manager | t2.medium | Swarm manager + Jenkins |
| node1 | t3.micro | Swarm worker |
| node2 | t3.micro | Swarm worker |

---

## ðŸš€ Step-by-Step Implementation

### Step 1: Launch EC2 Instances
Launch 3 Amazon Linux 2023 instances: `Manager`, `node1`, `node2`. Open the required ports in the Security Group (22, 8080 for Jenkins, 2377/7946/4789 for Swarm, and the app ports).

![EC2 Instances](images/01-ec2-instances.png)

### Step 2: Install Docker on All Nodes
Connect to all 3 machines with MobaXterm, enable **MultiExec** mode and run:

```bash
sudo -i
yum install -y docker
systemctl start docker
systemctl enable docker
```

![Docker install using MultiExec](images/02-docker-install-multiexec.png)

### Step 3: Set Hostnames

```bash
hostnamectl set-hostname manager   # on manager
hostnamectl set-hostname node1     # on worker 1
hostnamectl set-hostname node2     # on worker 2
```

### Step 4: Initialize Docker Swarm
On the **Manager**:

```bash
docker swarm init
```

Copy the join command it prints and run it on **node1** and **node2**:

```bash
docker swarm join --token <SWARM_TOKEN> <MANAGER_PRIVATE_IP>:2377
```

![Worker joined the swarm](images/03-worker-joined-swarm.png)

Verify on the Manager:

```bash
docker node ls
```

### Step 5: Install Jenkins on the Manager
Jenkins is installed using a shell script (Java 17, Maven, Git and Jenkins).

```bash
vi jen.sh        # paste the script
sh jen.sh
```

Open `http://<MANAGER_PUBLIC_IP>:8080`, unlock Jenkins and install the suggested plugins.

![Jenkins installation](images/04-jenkins-install.png)

### Step 6: Allow Jenkins to Use Docker
Run on the Manager so the Jenkins user can access the Docker daemon:

```bash
chmod 777 /var/run/docker.sock
systemctl daemon-reload
systemctl restart docker.service
```

![Docker socket permission](images/05-docker-sock-permission.png)

> âš ï¸ `chmod 777` is fine for a demo/lab. In production add the `jenkins` user to the `docker` group instead.

### Step 7: Create the Jenkins Pipeline
1. New Item â†’ **Pipeline** â†’ name it `docker project`.
2. Tick **This project is parameterized** and add two *Choice parameters*:

| Parameter | Choices |
|-----------|---------|
| `image` | `internetbanking:v1`, `mobilebanking:v1`, `insurance:v1`, `loans:v1` |
| `repo` | `<dockerhub-user>/ib-image`, `<dockerhub-user>/mb-image`, `<dockerhub-user>/insurance-image`, `<dockerhub-user>/loans-image` |

3. Store the Docker Hub password securely (Jenkins Credentials, or `Manage Jenkins â†’ System â†’ Environment variables`).

Pipeline script:

```groovy
pipeline {
    agent any

    stages {
        stage('checkout') {
            steps {
                git 'https://github.com/damashekar0/dockerproject.git'
            }
        }
        stage('build') {
            steps {
                sh 'docker build -t $image .'
            }
        }
        stage('tag') {
            steps {
                sh 'docker tag $image $repo'
            }
        }
        stage('push') {
            steps {
                sh 'docker login -u <dockerhub-user> -p $password'
                sh 'docker push $repo'
            }
        }
        stage('deploy') {
            steps {
                sh 'docker stack deploy bank -c docker-compose.yml'
            }
        }
    }
}
```

![Jenkins pipeline script](images/06-jenkins-pipeline-script.png)

### Step 8: Run the Build and Push to Docker Hub
Click **Build with Parameters**, pick an `image` and its matching `repo`. A successful run logs in to Docker Hub, pushes the image and ends with `Finished: SUCCESS`.

![Jenkins build success](images/07-jenkins-build-success.png)

Repeat for each application (change `index.html` in GitHub â†’ build with the next image/repo pair) so that all 4 images exist in Docker Hub.

### Step 9: Deploy with Docker Stack
`docker-compose.yml` runs each app with **3 replicas** spread across the swarm nodes:

```yaml
version: '3.8'
services:
  internetbanking:
    image: <dockerhub-user>/ib-image:latest
    ports:
      - "8081:80"
    deploy:
      replicas: 3
  mobilebanking:
    image: <dockerhub-user>/mb-image:latest
    ports:
      - "8082:80"
    deploy:
      replicas: 3
  insurance:
    image: <dockerhub-user>/insurance-image:latest
    ports:
      - "8083:80"
    deploy:
      replicas: 3
  loan:
    image: <dockerhub-user>/loans-image:latest
    ports:
      - "8084:80"
    deploy:
      replicas: 3
```

Useful commands on the Manager:

```bash
docker stack ls
docker stack services bank
docker stack ps bank
docker service ls
```

### Step 10: Access the Application
Open `http://<ANY_NODE_PUBLIC_IP>:8081` â€“ the Swarm routing mesh serves the app from any node.

![Application home page](images/08-app-home-page.png)

![Application login popup](images/09-app-login-popup.png)

---

## âœ… Key Learnings
- Building a multi-node Docker Swarm cluster on AWS
- Parameterized Jenkins pipelines (one pipeline, many images)
- Image tagging and pushing to Docker Hub
- High availability with replicated services using `docker stack deploy`

## ðŸ” Security Notes
- Never hard-code the Docker Hub password; use **Jenkins Credentials**.
- Do not commit Swarm join tokens or public IPs.
- Avoid `chmod 777 /var/run/docker.sock` in production.

## ðŸ”® Future Improvements
- GitHub webhook / SCM polling trigger
- Use Jenkins Credentials binding instead of plain-text password
- Add Docker Swarm visualizer and monitoring (Prometheus + Grafana)
- Image versioning with build numbers instead of `latest`

## ðŸ‘¤ Author
**Shekar** â€“ DevOps Learner

## Note on the pipeline
The GitHub Actions workflow was verified green (run 8, screenshot 12). After the project, the AWS resources were removed to avoid cost, so the workflow is set to manual trigger only.


