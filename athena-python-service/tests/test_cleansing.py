"""
Tests for cleansing pipeline: SectorMapper and TargetEncoder
"""
import pytest
import pandas as pd
import numpy as np

from cleansing.sector_mapper import SectorMapper, UNKNOWN_SECTOR
from features.categorical_encoder import TargetEncoder


# ── SectorMapper Tests ───────────────────────────────────────────────────────

class TestSectorMapper:
    def setup_method(self):
        self.mapper = SectorMapper(use_ml_fallback=False)

    def test_agriculture_keyword(self):
        sector, method = self.mapper.map("Dairy and poultry farming in Nakuru")
        assert sector == "Agriculture"
        assert method == "keyword"

    def test_retail_keyword(self):
        sector, method = self.mapper.map("General goods duka in Mathare")
        assert sector == "Retail"
        assert method == "keyword"

    def test_transport_keyword(self):
        sector, method = self.mapper.map("Matatu business along Thika Road")
        assert sector == "Transport"
        assert method == "keyword"

    def test_food_hospitality_keyword(self):
        sector, method = self.mapper.map("Mkahawa and restaurant in CBD")
        assert sector == "Food & Hospitality"
        assert method == "keyword"

    def test_construction_keyword(self):
        sector, method = self.mapper.map("Building and construction contractor")
        assert sector == "Construction"
        assert method == "keyword"

    def test_tech_keyword(self):
        sector, method = self.mapper.map("Software development and IT consultancy")
        assert sector == "Technology"
        assert method == "keyword"

    def test_unknown_returns_default(self):
        sector, method = self.mapper.map("XYZ company doing various things")
        assert sector == UNKNOWN_SECTOR

    def test_empty_description_returns_default(self):
        sector, method = self.mapper.map("")
        assert sector == UNKNOWN_SECTOR
        assert method == "default"

    def test_case_insensitive_matching(self):
        sector, _ = self.mapper.map("DAIRY FARMING IN RIFT VALLEY")
        assert sector == "Agriculture"

    def test_batch_map_returns_all(self):
        descriptions = [
            "Matatu transport business",
            "Poultry farming",
            "Unknown company",
        ]
        results = self.mapper.map_batch(descriptions)
        assert len(results) == 3
        assert results[0]["sector"] == "Transport"
        assert results[1]["sector"] == "Agriculture"
        assert results[2]["sector"] == UNKNOWN_SECTOR


# ── TargetEncoder Tests ──────────────────────────────────────────────────────

class TestTargetEncoder:
    def _make_df(self, n=200):
        """Synthetic dataset with known sector → default correlation."""
        np.random.seed(42)
        sectors = np.random.choice(["Agriculture", "Retail", "Transport", "Other"], n)
        # Agriculture has higher default rate (0.4) vs others (0.1)
        default = np.array([
            np.random.binomial(1, 0.4 if s == "Agriculture" else 0.1)
            for s in sectors
        ])
        return pd.DataFrame({"sector": sectors, "region": ["Nairobi"] * n, "default": default})

    def test_fit_transform_adds_encoded_column(self):
        df = self._make_df()
        enc = TargetEncoder(n_folds=5)
        result = enc.fit_transform(df, ["sector"], "default")
        assert "sector_enc" in result.columns
        assert "sector" not in result.columns  # original dropped

    def test_agriculture_higher_encoding_than_transport(self):
        """Agriculture should get a higher encoded value (higher default rate)."""
        df = self._make_df(n=500)
        enc = TargetEncoder(n_folds=5)
        enc.fit_transform(df, ["sector"], "default")
        assert enc.encoding_maps["sector"]["Agriculture"] > enc.encoding_maps["sector"]["Transport"]

    def test_transform_at_inference_uses_stored_map(self):
        df = self._make_df()
        enc = TargetEncoder()
        enc.fit_transform(df, ["sector"], "default")
        new_df = pd.DataFrame({"sector": ["Agriculture", "Retail", "UNKNOWN_CAT"]})
        result = enc.transform(new_df, ["sector"])
        assert "sector_enc" in result.columns
        # Unknown category → filled with global mean (no NaN)
        assert result["sector_enc"].isna().sum() == 0

    def test_json_serialization_roundtrip(self):
        df = self._make_df()
        enc = TargetEncoder()
        enc.fit_transform(df, ["sector"], "default")
        json_str = enc.to_json()
        loaded = TargetEncoder.from_json(json_str)
        # Encoding maps should be identical
        assert loaded.encoding_maps == enc.encoding_maps
        assert loaded.global_means == enc.global_means

    def test_fit_transform_multiple_columns(self):
        df = self._make_df()
        enc = TargetEncoder()
        result = enc.fit_transform(df, ["sector", "region"], "default")
        assert "sector_enc" in result.columns
        assert "region_enc" in result.columns

    def test_unfitted_column_raises_value_error(self):
        enc = TargetEncoder()
        # Use a large enough df for fit_transform (need >= n_folds rows)
        df = pd.DataFrame({
            "sector": ["Agriculture", "Retail", "Transport", "Other", "Agriculture",
                       "Retail", "Transport", "Other", "Agriculture", "Retail"],
            "default": [1, 0, 0, 0, 1, 0, 0, 0, 1, 0],
        })
        enc.fit_transform(df, ["sector"], "default")
        # Now try to transform a column that was never fitted
        new_df = pd.DataFrame({"unknown_col": ["x", "y"]})
        with pytest.raises(ValueError, match="not fitted"):
            enc.transform(new_df, ["unknown_col"])
