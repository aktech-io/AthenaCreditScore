from __future__ import annotations

import os
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
    """

    def __init__(self, model_alias: str = "champion"):
        mlflow.set_tracking_uri(MLFLOW_URI)
        self.model_alias = model_alias
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            model_uri = f"models:/{MODEL_NAME}@{self.model_alias}"
            self.model = mlflow.lightgbm.load_model(model_uri)
            logger.info("LightGBM model loaded", alias=self.model_alias, uri=model_uri)
        except Exception as exc:
            logger.warning(
                "LightGBM model not found in registry — scoring will use rule-based fallback",
                alias=self.model_alias,
                error=str(exc),
            )
            self.model = None

    def predict_pd(self, features: dict) -> Optional[float]:
        """
        Predict probability of default (0-1).
        Returns None if model is not loaded (triggers fallback to rule-based scorer).
        """
        if self.model is None:
            return None
        try:
            df = pd.DataFrame([features])
            proba = self.model.predict_proba(df)
            pd_prob = float(proba[0, 1])
            logger.debug("LightGBM PD prediction", pd=pd_prob, alias=self.model_alias)
            return pd_prob
        except Exception as exc:
            logger.error("LightGBM inference failed", error=str(exc))
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
