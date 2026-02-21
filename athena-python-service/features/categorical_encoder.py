from __future__ import annotations

import json
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold
import structlog

logger = structlog.get_logger(__name__)


class TargetEncoder:
    """
    Target encoding with K-fold cross-validation to prevent leakage.
    
    For each categorical column:
      - Splits training data into K folds
      - Encodes each fold using mean target from the other K-1 folds
      - Applies global mean smoothing (for low-frequency categories)
      - Stores final encoding map (mean target per category on all training data)
    
    The stored mapping is used for inference-time encoding.
    Mappings are serialized to JSON for storage in the feature_definitions table.
    """

    def __init__(self, n_folds: int = 5, smoothing: float = 10.0, min_samples: int = 5):
        self.n_folds = n_folds
        self.smoothing = smoothing      # higher = more regularization
        self.min_samples = min_samples  # categories below this → global mean
        self.encoding_maps: Dict[str, Dict[str, float]] = {}
        self.global_means: Dict[str, float] = {}

    def fit_transform(
        self,
        df: pd.DataFrame,
        categorical_cols: List[str],
        target_col: str,
    ) -> pd.DataFrame:
        """
        Fit the encoder on df and return a new DataFrame with encoded columns.
        Original categorical columns are dropped; encoded columns added as _enc suffix.
        """
        df = df.copy()
        kf = KFold(n_splits=self.n_folds, shuffle=True, random_state=42)
        global_mean = df[target_col].mean()

        for col in categorical_cols:
            logger.info("Target encoding", column=col)
            self.global_means[col] = global_mean
            encoded = np.full(len(df), global_mean)

            for train_idx, val_idx in kf.split(df):
                fold_map = (
                    df.iloc[train_idx]
                    .groupby(col)[target_col]
                    .agg(["mean", "count"])
                )
                # Smoothing: blend category mean toward global mean
                fold_map["smoothed"] = (
                    (fold_map["mean"] * fold_map["count"] + global_mean * self.smoothing)
                    / (fold_map["count"] + self.smoothing)
                )
                val_categories = df.iloc[val_idx][col]
                encoded[val_idx] = val_categories.map(fold_map["smoothed"]).fillna(global_mean).values

            df[f"{col}_enc"] = encoded

            # Build the global encoding map (for inference)
            full_map = (
                df.groupby(col)[target_col]
                .agg(["mean", "count"])
            )
            full_map["smoothed"] = (
                (full_map["mean"] * full_map["count"] + global_mean * self.smoothing)
                / (full_map["count"] + self.smoothing)
            )
            self.encoding_maps[col] = full_map["smoothed"].to_dict()

            df = df.drop(columns=[col])

        return df

    def transform(self, df: pd.DataFrame, categorical_cols: List[str]) -> pd.DataFrame:
        """Apply stored encoding maps to new data (inference)."""
        df = df.copy()
        for col in categorical_cols:
            if col not in self.encoding_maps:
                raise ValueError(f"Column '{col}' not fitted. Call fit_transform first.")
            global_mean = self.global_means.get(col, 0.0)
            df[f"{col}_enc"] = df[col].map(self.encoding_maps[col]).fillna(global_mean)
            df = df.drop(columns=[col])
        return df

    def to_json(self) -> str:
        """Serialize encoding maps to JSON for storage in feature_definitions table."""
        return json.dumps({
            "encoding_maps": self.encoding_maps,
            "global_means": self.global_means,
            "n_folds": self.n_folds,
            "smoothing": self.smoothing,
        })

    @classmethod
    def from_json(cls, json_str: str) -> "TargetEncoder":
        """Reconstruct encoder from stored JSON."""
        data = json.loads(json_str)
        enc = cls(n_folds=data["n_folds"], smoothing=data["smoothing"])
        enc.encoding_maps = data["encoding_maps"]
        enc.global_means = data["global_means"]
        return enc
