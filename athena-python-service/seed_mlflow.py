"""
Seed MLflow with champion and challenger LightGBM models.
Runs against MLFLOW_TRACKING_URI (default: http://localhost:5000).
MLFLOW_ARTIFACT_ROOT can optionally point to a writable local dir.
"""
import os
import sys
import json
import logging
import tempfile

logging.basicConfig(level=logging.INFO)

import mlflow
import pandas as pd
import numpy as np

TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(TRACKING_URI)

# Use a local temp dir as artifact root so the host client doesn't try to write to /mlflow
LOCAL_ARTIFACT_ROOT = tempfile.mkdtemp(prefix="mlflow_seed_")
print(f"MLflow version  : {mlflow.__version__}")
print(f"MLflow server   : {TRACKING_URI}")
print(f"Local artifact  : {LOCAL_ARTIFACT_ROOT}")

# Create or get experiment; override artifact root to a writable local path
from mlflow.tracking import MlflowClient as _Client
_client = _Client()
try:
    exp = _client.get_experiment_by_name("athena-credit-scorer")
    if exp is None:
        exp_id = _client.create_experiment(
            "athena-credit-scorer",
            artifact_location=f"file://{LOCAL_ARTIFACT_ROOT}"
        )
    else:
        exp_id = exp.experiment_id
except Exception:
    exp_id = mlflow.create_experiment(
        "athena-credit-scorer",
        artifact_location=f"file://{LOCAL_ARTIFACT_ROOT}"
    )

# ── Generate synthetic credit-scoring dataset ─────────────────────────────────
np.random.seed(42)
n_samples = 1000
features = {
    "avg_loan_spacing_days": np.random.uniform(0, 180, n_samples),
    "max_delinquency_streak": np.random.randint(0, 10, n_samples),
    "delinquency_rate_90d": np.random.uniform(0, 1, n_samples),
    "total_loans": np.random.randint(1, 20, n_samples),
    "payment_cv": np.random.uniform(0, 1, n_samples),
    "early_repayment_rate": np.random.uniform(0, 1, n_samples),
    "capital_growth_rate": np.random.uniform(-0.5, 2.0, n_samples),
    "profit_margin": np.random.uniform(-0.2, 0.8, n_samples),
    "sector_risk_modifier": np.random.uniform(0.5, 1.5, n_samples),
    "bureau_score": np.random.randint(300, 850, n_samples),
    "open_npa_accounts": np.random.randint(0, 3, n_samples),
}
logit = (
    -2.0
    + 0.5 * features["max_delinquency_streak"]
    + 2.0 * features["delinquency_rate_90d"]
    - 0.01 * (features["bureau_score"] - 500)
    + 1.0 * features["open_npa_accounts"]
    - 1.0 * features["profit_margin"]
)
probs = 1 / (1 + np.exp(-logit))
features["default_flag"] = np.random.binomial(1, probs)
df = pd.DataFrame(features)


# ── Train & register helper ───────────────────────────────────────────────────
def seed_run(run_name: str) -> str:
    import lightgbm as lgb
    from sklearn.metrics import roc_auc_score, average_precision_score, f1_score
    from sklearn.model_selection import train_test_split
    from scipy.stats import ks_2samp

    X = df.drop(columns=["default_flag"])
    y = df["default_flag"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    params = {
        "objective": "binary", "metric": "binary_logloss",
        "learning_rate": 0.05, "num_leaves": 31, "max_depth": 6,
        "min_child_samples": 20, "reg_alpha": 0.1, "reg_lambda": 0.1,
        "n_estimators": 500, "verbose": -1, "class_weight": "balanced",
    }

    experiment = mlflow.set_experiment("athena-credit-scorer")
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params(params)
        model = lgb.LGBMClassifier(**{k: v for k, v in params.items() if k != "early_stopping_rounds"})
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)],
                  callbacks=[lgb.early_stopping(50, verbose=False)])

        y_prob = model.predict_proba(X_test)[:, 1]
        y_pred = (y_prob > 0.5).astype(int)
        auc = roc_auc_score(y_test, y_prob)
        pos_probs = [p for p, y in zip(y_prob, y_test) if y == 1]
        neg_probs = [p for p, y in zip(y_prob, y_test) if y == 0]
        ks = ks_2samp(pos_probs, neg_probs).statistic
        pr_auc = average_precision_score(y_test, y_prob)
        f1 = f1_score(y_test, y_pred)

        mlflow.log_metrics({"auc_roc": round(auc, 4), "ks_statistic": round(ks, 4),
                            "pr_auc": round(pr_auc, 4), "f1_score": round(f1, 4)})
        print(f"  {run_name}: AUC={auc:.4f}  KS={ks:.4f}")

        # Save model to a temp dir, then log as artifact via HTTP
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, "lgbm.txt")
            model.booster_.save_model(model_path)
            mlflow.log_artifact(model_path)

        # Register in model registry
        model_uri = f"runs:/{run.info.run_id}/lgbm.txt"
        mlflow.register_model(model_uri, "AthenaScorer")
        return run.info.run_id


print("\nTraining Champion Model...")
run_id_champion = seed_run("athena-lgbm-champion-v1")

print("\nTraining Challenger Model...")
run_id_challenger = seed_run("athena-lgbm-challenger-v1")

# Set aliases
from mlflow.tracking import MlflowClient
client = MlflowClient()
for mv in client.search_model_versions("name='AthenaScorer'"):
    if mv.run_id == run_id_champion:
        client.set_registered_model_alias("AthenaScorer", "champion", mv.version)
        print(f"\nSet version {mv.version} as 'champion'")
    elif mv.run_id == run_id_challenger:
        client.set_registered_model_alias("AthenaScorer", "challenger", mv.version)
        print(f"Set version {mv.version} as 'challenger'")

print("\n✅ Seeding complete! Open http://localhost:5000 to see the models.")
