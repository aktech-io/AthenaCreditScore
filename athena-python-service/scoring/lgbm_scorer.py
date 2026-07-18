from __future__ import annotations

import os
import tempfile
from typing import Optional

import mlflow
import mlflow.lightgbm
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)

MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MODEL_NAME = os.getenv("MLFLOW_MODEL_NAME", "AthenaScorer")


class LGBMScorer:
    """
    Loads a LightGBM model from the MLflow model registry and runs inference.
    Supports champion/challenger model aliasing.

    Handles both storage formats found in the registry:
    - models logged with the mlflow.lightgbm flavor (sklearn API, predict_proba)
    - raw Booster text files registered as artifacts (Booster.predict)
    """

    def __init__(self, model_alias: str = "champion"):
        mlflow.set_tracking_uri(MLFLOW_URI)
        self.model_alias = model_alias
        self.model = None
        self.calibrator = None
        self._explainer = None
        self.model_version: Optional[str] = None
        self._load_model()

    def _load_model(self):
        self._explainer = None
        try:
            client = mlflow.tracking.MlflowClient()
            mv = client.get_model_version_by_alias(MODEL_NAME, self.model_alias)
            self.model_version = mv.version
        except Exception as exc:
            logger.warning(
                "No model version for alias — scoring will use rule-based fallback",
                alias=self.model_alias, error=str(exc),
            )
            self.model = None
            return

        self._load_calibrator(mv.run_id)

        model_uri = f"models:/{MODEL_NAME}@{self.model_alias}"
        try:
            self.model = mlflow.lightgbm.load_model(model_uri)
            logger.info("LightGBM model loaded (flavor)", alias=self.model_alias, version=self.model_version)
            return
        except Exception as exc:
            logger.info(
                "lightgbm flavor load failed, trying raw Booster artifact",
                alias=self.model_alias, error=str(exc),
            )

        try:
            import lightgbm as lgb
            with tempfile.TemporaryDirectory() as tmpdir:
                local = mlflow.artifacts.download_artifacts(
                    run_id=mv.run_id, artifact_path="lgbm.txt", dst_path=tmpdir
                )
                self.model = lgb.Booster(model_file=local)
            logger.info("LightGBM model loaded (raw Booster)", alias=self.model_alias, version=self.model_version)
        except Exception as exc:
            logger.warning(
                "LightGBM model not loadable — scoring will use rule-based fallback",
                alias=self.model_alias, error=str(exc),
            )
            self.model = None

    def _load_calibrator(self, run_id: str):
        """Load the isotonic calibrator logged alongside the model, if any."""
        self.calibrator = None
        try:
            import joblib
            with tempfile.TemporaryDirectory() as tmpdir:
                local = mlflow.artifacts.download_artifacts(
                    run_id=run_id, artifact_path="calibrator.joblib", dst_path=tmpdir
                )
                self.calibrator = joblib.load(local)
            logger.info("PD calibrator loaded", alias=self.model_alias)
        except Exception:
            logger.info("No PD calibrator for this model version — raw PD used",
                        alias=self.model_alias)

    def _frame(self, features: dict) -> pd.DataFrame:
        """Build a single-row frame aligned to the model's feature order."""
        clean = {k: v for k, v in features.items() if not k.startswith("_")}
        df = pd.DataFrame([clean])
        # LightGBM matches features POSITIONALLY, and JSONB storage does not
        # preserve key order — always reindex to the model's feature order.
        if hasattr(self.model, "feature_name_"):
            df = df.reindex(columns=list(self.model.feature_name_))
        elif hasattr(self.model, "feature_name"):
            df = df.reindex(columns=list(self.model.feature_name()))
        return df

    def predict_pd(self, features: dict) -> Optional[float]:
        """
        Predict probability of default (0-1).
        Returns None if model is not loaded or the feature vector is unusable
        (triggers fallback to rule-based scorer).
        """
        if self.model is None:
            return None
        try:
            df = self._frame(features)
            if hasattr(self.model, "predict_proba"):
                pd_prob = float(self.model.predict_proba(df)[0, 1])
            else:
                # Booster with binary objective returns P(class=1) directly
                pd_prob = float(self.model.predict(df)[0])
            if self.calibrator is not None:
                pd_prob = float(self.calibrator.predict([pd_prob])[0])
            logger.debug("LightGBM PD prediction", pd=pd_prob, alias=self.model_alias)
            return pd_prob
        except Exception as exc:
            logger.error("LightGBM inference failed", error=str(exc))
            return None

    def explain(self, features: dict) -> Optional[list]:
        """
        Per-feature SHAP contributions for one prediction, as
        [(feature_name, shap_value), ...]. Positive values push PD up.
        Returns None when the model or SHAP is unavailable.
        """
        if self.model is None:
            return None
        try:
            if self._explainer is None:
                import shap
                self._explainer = shap.TreeExplainer(self.model)
            df = self._frame(features)
            shap_values = self._explainer.shap_values(df)
            if isinstance(shap_values, list):       # older SHAP: [class0, class1]
                shap_values = shap_values[1]
            row = shap_values[0]
            if getattr(row, "ndim", 1) > 1:         # newer SHAP: (n_features, n_classes)
                row = row[:, 1]
            return list(zip(df.columns.tolist(), [float(v) for v in row]))
        except Exception as exc:
            logger.warning("SHAP explanation failed", error=str(exc))
            return None

    def reload(self):
        """Reload the model (called after champion is promoted)."""
        self._load_model()


# Module-level cache of champion and challenger scorers
_champion_scorer: Optional[LGBMScorer] = None
_challenger_scorer: Optional[LGBMScorer] = None


def get_lgbm_scorer(model_target: str = "champion") -> LGBMScorer:
    """Return (cached) scorer for the given alias."""
    global _champion_scorer, _challenger_scorer
    if model_target == "champion":
        if _champion_scorer is None:
            _champion_scorer = LGBMScorer("champion")
        return _champion_scorer
    else:
        if _challenger_scorer is None:
            _challenger_scorer = LGBMScorer("challenger")
        return _challenger_scorer
