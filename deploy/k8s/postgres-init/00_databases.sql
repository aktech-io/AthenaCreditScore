-- Runs first (alphabetical order in /docker-entrypoint-initdb.d), only when the
-- data volume is empty. athena_db itself is created by POSTGRES_DB; this adds
-- the MLflow backend-store database (docker-compose points
-- --backend-store-uri at postgres/mlflow_db).
--
-- NOTE: the docker-compose postgres also hosts ~25 athena_* LMS databases —
-- those are created by the AthenaIntelligentLMS stack, which in Kubernetes
-- runs its own postgres in the `lms` namespace, so they are deliberately NOT
-- created here.
CREATE DATABASE mlflow_db;
