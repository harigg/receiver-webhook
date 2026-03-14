# AI Company Local Agentic Workflow — Setup Status

## Architecture

```
GitHub (code hosting + PRs) ←→ Webhook Receiver (FastAPI in k8s)
                                        ↓
                              Orchestrator Agent (Claude)
                              ├── Architect Agent
                              ├── Coder Agent
                              ├── Security Agent
                              └── Tester Agent
                                        ↓
                              GitHub PR Review Comment posted
                                        ↓
                              Slack + WhatsApp notification

minikube (ai-company profile, docker driver, IP: 192.168.49.2)
├── tools namespace       → Gitea*, Plane, Outline, Vault
├── registry namespace    → Harbor (container registry for built images)
├── monitoring namespace  → Prometheus, Grafana, Loki
├── security namespace    → SonarQube, Gitleaks (CronJob)
└── agents namespace      → Webhook Receiver (GitHub webhook endpoint)
```

> *Gitea is deployed locally but GitHub is the authoritative code host.
> Gitea can be used for local experiments.

## Source of Truth
**GitHub** — all code lives in GitHub repos. GitHub Actions runs CI/CD.
Harbor (local) stores the built Docker images pushed by GitHub Actions.

## Service URLs

| Service     | URL                            | Credentials                |
|-------------|--------------------------------|----------------------------|
| Plane       | http://192.168.49.2:30300      | (first user = admin)       |
| Outline     | http://192.168.49.2:30301      | (first user = admin)       |
| Harbor      | http://192.168.49.2:30002      | admin / Harbor12345        |
| Vault       | http://192.168.49.2:30820      | Token: root                |
| Grafana     | http://192.168.49.2:30400      | admin / grafana1234        |
| Prometheus  | http://192.168.49.2:30401      | no auth                    |
| SonarQube   | http://192.168.49.2:30900      | admin / admin (first login)|
| Webhooks    | http://192.168.49.2:30500      | via GitHub webhook secret  |
| Gitea       | http://192.168.49.2:30080      | admin / admin1234          |

## Phase Status

### ✅ Phase 1: Prerequisites
- minikube running (profile: ai-company, docker driver)
- Namespaces: tools, registry, monitoring, security, agents
- ingress-nginx deployed

### ✅ Phase 2: Project Directory Structure
```
/Users/hari/dev/ai-company/
├── infrastructure/
│   ├── k8s/
│   │   ├── helm-values/    → gitea.yaml, harbor.yaml, vault.yaml,
│   │   │                      prometheus-stack.yaml, loki.yaml, sonarqube.yaml
│   │   └── manifests/      → outline.yaml, plane.yaml, gitleaks.yaml, agents.yaml
│   ├── github-actions/     → ci-cd.yaml (GitHub Actions workflow template)
│   └── gitea-actions/      → ci-cd.yaml (legacy, replaced by github-actions)
├── agents/
│   ├── orchestrator/main.py → Coordinates all specialist agents, posts GitHub review
│   ├── architect/main.py
│   ├── coder/main.py
│   ├── docs/main.py
│   ├── requirements/main.py
│   ├── security/main.py
│   └── tester/main.py
├── shared/lib/
│   ├── __init__.py
│   ├── base_agent.py       → BaseAgent class (wraps Claude API)
│   ├── github_client.py    → GitHub REST API client
│   ├── gitea_client.py     → Gitea REST API client (local use)
│   └── notifier.py         → Slack + WhatsApp notifications
├── webhook-receiver/
│   ├── main.py             → FastAPI app
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── models/events.py    → Pydantic models for webhook payloads
│   └── routes/
│       ├── github.py       → GitHub webhook handlers (primary)
│       ├── gitea.py        → Gitea webhook handlers (secondary)
│       └── health.py
└── .venv/                  → Python venv
```

### ✅ Phase 3: Core Services
- [x] Harbor (container registry) — `registry` namespace
- [x] Vault (secrets manager, dev mode, token: root) — `tools` namespace
- [x] Outline (wiki/docs) — `tools` namespace
- [x] Plane (project management) — `tools` namespace
- [x] Gitea (local git server, optional) — `tools` namespace

### ✅ Phase 4: Observability Stack
- [x] Prometheus — `monitoring` namespace (port 30401)
- [x] Grafana — `monitoring` namespace (port 30400, admin/grafana1234)
- [x] Loki + Promtail — `monitoring` namespace

### ✅ Phase 5: Security Tools
- [x] SonarQube Community — `security` namespace (port 30900, still initializing ~5min)
- [x] Gitleaks — `security` namespace (CronJob, runs every 6h)
- [x] Trivy — built into Harbor

### ✅ Phase 6: Python Agent Framework + Webhook Receiver
- [x] `shared/lib/base_agent.py` — BaseAgent wrapping Claude API
- [x] `shared/lib/github_client.py` — GitHub REST API client
- [x] `shared/lib/notifier.py` — Slack + WhatsApp notifier
- [x] `webhook-receiver/main.py` — FastAPI app receiving GitHub webhooks
- [x] `webhook-receiver/routes/github.py` — GitHub PR/push event handlers

### ✅ Phase 7: Agent Classes
- [x] OrchestratorAgent — routes + synthesizes multi-agent reviews
- [x] ArchitectAgent — architecture / design review
- [x] CoderAgent — code quality review
- [x] SecurityAgent — OWASP / security review
- [x] TesterAgent — test coverage review
- [x] DocsAgent — documentation review
- [x] RequirementsAgent — requirements validation

### ✅ Phase 8: PR Review Multi-Agent System
- [x] GitHub webhook → webhook-receiver → OrchestratorAgent
- [x] Orchestrator fans out to all specialist agents in parallel
- [x] Synthesizes and posts formal GitHub PR review (APPROVE/REQUEST_CHANGES/COMMENT)

### ✅ Phase 9: GitHub Actions CI/CD Pipeline
- [x] `infrastructure/github-actions/ci-cd.yaml`
- Jobs: lint → test → gitleaks → trivy → build → push to Harbor → deploy to k8s
- Requires: self-hosted runner with kubectl access to ai-company cluster

### ✅ Phase 10: Notifications
- [x] Slack (via incoming webhook URL in env var SLACK_WEBHOOK_URL)
- [x] WhatsApp (via Twilio in env vars TWILIO_*)

---

## Next Steps / Configuration Required

### 1. Set GitHub Webhook
In your GitHub repo → Settings → Webhooks → Add webhook:
- URL: `http://192.168.49.2:30500/webhook/github`
  (or use ngrok/cloudflared tunnel for public access)
- Content-Type: `application/json`
- Secret: set a secret and add to k8s Secret as `GITHUB_WEBHOOK_SECRET`
- Events: Pull requests, Pushes

### 2. Set API Keys in Kubernetes Secret
```bash
kubectl create secret generic agent-secrets \
  -n agents \
  --from-literal=ANTHROPIC_API_KEY=your_key \
  --from-literal=GITHUB_TOKEN=your_token \
  --from-literal=GITHUB_WEBHOOK_SECRET=your_secret \
  --from-literal=SLACK_WEBHOOK_URL=https://hooks.slack.com/... \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 3. Build and Deploy Webhook Receiver
```bash
cd /Users/hari/dev/ai-company

# Build the image (point Docker to minikube's daemon)
eval $(minikube -p ai-company docker-env)
docker build -t harbor.local:30002/ai-company/webhook-receiver:latest \
  -f webhook-receiver/Dockerfile .

# Or push to Harbor after logging in:
docker login 192.168.49.2:30002 -u admin -p Harbor12345
docker push 192.168.49.2:30002/ai-company/webhook-receiver:latest

# Deploy
kubectl apply -f infrastructure/k8s/manifests/agents.yaml
```

### 4. Add GitHub Actions Self-Hosted Runner (for deploy step)
Follow GitHub docs to add a self-hosted runner on this machine,
then use the `github-actions/ci-cd.yaml` workflow in your repos.

### 5. Expose Webhook Receiver Publicly (for GitHub to reach it)
```bash
# Option A: ngrok
ngrok http 192.168.49.2:30500

# Option B: cloudflared tunnel
cloudflare tunnel --url http://192.168.49.2:30500
```

---

## Key Credentials

| Item | Value |
|------|-------|
| Kubernetes context | ai-company |
| Minikube IP | 192.168.49.2 |
| Vault root token | root |
| Harbor admin | admin / Harbor12345 |
| Grafana admin | admin / grafana1234 |
| SonarQube admin | admin / admin |
