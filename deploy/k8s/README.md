# NemoScore — Kubernetes deployment (namespace `nemoscore`)

Kustomize manifests for the NemoScore credit-scoring stack (Athena rebrand for
the Nemo neobank). Pattern follows the house EthioDigitalRecon layout:
numbered manifests, one gitignored plain-Secret file, short local image names
remapped to GHCR in `kustomization.yaml`, CI/CD via GitHub Actions →
ghcr.io → `kubectl set image` over SSH.

```
kubectl apply -k deploy/k8s
```

## What runs

| Manifest | Workload | Notes |
|---|---|---|
| 10-postgres | postgres:16-alpine StatefulSet, 5Gi local-path PVC | schema + migrations via `/docker-entrypoint-initdb.d` (postgres-init ConfigMap), first boot only |
| 11-rabbitmq | rabbitmq:3.13-management-alpine, 2Gi PVC, Recreate | |
| 12-mlflow | `nemoscore/mlflow` (v2.19.0 + psycopg2), 5Gi artifact PVC | backend store `mlflow_db` on postgres, `--serve-artifacts` |
| 20–24 | Go services: user(8081) customer(8082) media(8083, 10Gi PVC) notification(8085) scoring(8080) | GORM AutoMigrate at startup; readiness `GET /actuator/health` |
| 30 | athena-python-service (FastAPI, 8001) | readiness `GET /health`; fail-closed API-key auth |
| 40-kong | kong:3.6-ubuntu, DB-less | **the scoring-contract edge**; Service `kong:8000`; admin 8444 pod-local only |
| 45-portal | nginx SPA (port 80) | nginx.conf proxies `/api/**` to service DNS at runtime — no baked URL, no rebuild-arg needed |
| 50-ingress | api./portal.nemoscore.athenafinance.cloud | ingress-nginx + cert-manager (prod only) |
| 55-backup | nightly pg_dump CronJob (02:00), 7-day retention, own 5Gi PVC | dumps athena_db + mlflow_db |
| 60-issuer | letsencrypt-prod ClusterIssuer | already exists on the shared Contabo cluster — applying is idempotent/optional |

The LMS (`lms` namespace, same cluster) calls the scoring contract at
`http://kong.nemoscore.svc.cluster.local:8000/api/v1/credit-score/{id}` with
`X-Api-Key: <one of SERVICE_API_KEYS>` (its `SCORING_API_URL`/`SCORING_API_KEY`
env). Auth is validated fail-closed by the python service.

## First-time setup (any cluster)

1. **Secrets** — `cp 02-secrets.example.yaml 02-secrets.yaml` and fill it
   (generator commands are documented in the example file). `02-secrets.yaml`
   is gitignored — never commit it.
   - `JWT_SECRET` must be `openssl rand -base64 32` — services base64-DECODE it.
   - `SERVICE_API_KEYS` must be strong random keys (never `dev-key` in prod);
     `SCORING_ENGINE_API_KEY` must be one of them.
2. **ghcr pull secret** (prod / any cluster pulling from GHCR):
   ```
   kubectl create ns nemoscore   # if not applying -k first
   kubectl -n nemoscore create secret docker-registry ghcr-pull \
     --docker-server=ghcr.io \
     --docker-username=<github-username> \
     --docker-password=<GHCR_PAT_with_read:packages> \
     --docker-email=tech@aktech.co.ke
   ```
3. `kubectl apply -k deploy/k8s`

## Local k3s staging (no ingress-nginx — k3s ships Traefik)

- The Ingress is inert without an nginx controller; either ignore it or
  `kubectl delete -f deploy/k8s/50-ingress.yaml`. Skip 60-issuer if
  cert-manager isn't installed: `kubectl delete --ignore-not-found -f
  deploy/k8s/60-cert-manager-issuer.yaml` after apply errors, or apply
  everything and accept the one CRD error. In-cluster Service DNS is what
  matters locally.
- Feed the cluster the locally-built images under the **GHCR names** (so the
  `images:` remap needs no local override; `imagePullPolicy: IfNotPresent`
  keeps k3s from pulling):
  ```
  for s in user-service customer-service media-service notification-service \
           scoring-service athena-python-service mlflow athena-portal; do
    docker tag athenacreditscore-$s:latest ghcr.io/aktech-io/nemoscore-${s/athena-/}:latest
  done   # see scripts in git history; python-service/portal names differ slightly
  docker save <all tags> | sudo k3s ctr images import -
  ```
- `kubectl apply -k deploy/k8s` (the ClusterIssuer apply fails harmlessly if
  cert-manager is absent), wait for rollouts, then verify through Kong from
  another namespace:
  ```
  kubectl run curl -n lms --rm -it --image=curlimages/curl --restart=Never -- \
    curl -si -H "X-Api-Key: $KEY" \
    http://kong.nemoscore.svc.cluster.local:8000/api/v1/credit-score/1
  ```
  No key → 401. Valid key + unknown customer → 404 (transport + auth OK).

## Kept-in-sync copies (kustomize can't read outside deploy/k8s/)

| Copy in deploy/k8s/ | Source of truth |
|---|---|
| `postgres-init/01_schema.sql` | `database/schema.sql` |
| `postgres-init/02..05_*.sql` | `database/migrations/2026_07_*.sql` (compose initdb order: tenant, reason_codes, mpesa; 05 feature_store_alignment is idempotent and a no-op on fresh schema) |
| `kong.yml` | `kong/kong.yml` |

`postgres-init/00_databases.sql` is k8s-only: creates `mlflow_db`.
`postgres-init/06_go_service_tables.sql` is also k8s-only: DDL for the Go
services' user/role/group/invitation/media/notification tables. These are NOT
in `database/schema.sql` — they date from the Java services' Flyway era, the
compose stack still runs on that old volume, and the Go port has no GORM
AutoMigrate — so fresh installs need this file (extracted via
`pg_dump --schema-only` from the working compose DB, 2026-07-20). The ~25
`athena_*` LMS databases living in the compose postgres are NOT created here —
in k8s the LMS runs its own postgres in the `lms` namespace.

New SQL migrations: initdb only runs on an EMPTY volume — apply new migration
files to a live cluster manually
(`kubectl -n nemoscore exec -i postgres-0 -- psql -U athena -d athena_db < file.sql`)
and add them to `postgres-init/` for future fresh installs.

## Prod (Contabo shared cluster) checklist

1. DNS A records: `api.nemoscore.athenafinance.cloud` and
   `portal.nemoscore.athenafinance.cloud` → cluster public IP.
2. `ghcr-pull` secret (step 2 above) — GHCR org is `aktech-io`.
3. `02-secrets.yaml` on the box that applies (or apply the Secret directly).
4. Replace the `dev-partner`/`dev-key` consumer in `kong.yml` with a real
   partner key (guards `/api/v1/credit-reports` and `/api/v3p`).
5. `kubectl apply -k deploy/k8s` — the letsencrypt-prod ClusterIssuer already
   exists there; applying is idempotent (or drop 60- from resources).
6. GitHub repo secrets for deploy.yml: `DEPLOY_HOST` (cluster IP/host),
   `DEPLOY_SSH_KEY` (private key for the `deploy` user, which has
   passwordless `sudo k3s kubectl`).
7. Point the LMS at the contract: `SCORING_API_URL=http://kong.nemoscore.svc.cluster.local:8000`
   and `SCORING_API_KEY=<one of SERVICE_API_KEYS>`.

## CI/CD

- `.github/workflows/ci.yml` — Go build+test per module (go.work layout) and
  python pytest on every push/PR.
- `.github/workflows/deploy.yml` — on push to main: matrix-builds the 8 images
  → ghcr.io/aktech-io/nemoscore-*:{latest,sha} → SSH `kubectl set image` +
  `rollout status` on the cluster. Postgres/rabbitmq/kong run stock images and
  are not part of the rollout.

## Not deployed (deliberately)

Prometheus/Grafana (cluster-level `monitoring` namespace already exists),
discovery-server/Eureka (removed July 2026), the Java/ekyc/fraud leftovers.
