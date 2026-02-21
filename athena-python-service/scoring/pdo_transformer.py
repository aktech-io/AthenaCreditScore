from __future__ import annotations

import math
import os
from dataclasses import dataclass


@dataclass
class PDOResult:
    pd_probability: float   # raw probability of default 0-1
    score: int              # PDO-scaled integer score 300-850
    band: str               # score band label
    factor: float
    offset: float


_BANDS = [
    (780, "Excellent"),
    (720, "Very Good"),
    (680, "Good"),
    (640, "Fair"),
    (600, "Marginal"),
    (0,   "Poor"),
]


class PDOTransformer:
    """
    Converts a raw probability of default (PD) into a business-friendly
    credit score using the Points-to-Double-Odds (PDO) method.

    Formula:
        factor = pdo / ln(2)
        offset = base_score - factor * ln(base_odds)
        score  = offset - factor * ln(odds)
        where odds = pd / (1 - pd)
    """

    def __init__(
        self,
        pdo: float = float(os.getenv("PDO", "50")),
        base_score: float = float(os.getenv("BASE_SCORE", "500")),
        base_odds: float = float(os.getenv("BASE_ODDS", "1.0")),
    ):
        self.pdo = pdo
        self.base_score = base_score
        self.base_odds = base_odds
        self.factor = pdo / math.log(2)
        self.offset = base_score - self.factor * math.log(base_odds)

    def transform(self, pd_probability: float) -> PDOResult:
        """Transform a raw PD to a scaled score (300-850)."""
        pd_clamped = max(1e-4, min(0.9999, pd_probability))
        odds = pd_clamped / (1.0 - pd_clamped)
        raw_score = self.offset - self.factor * math.log(odds)
        score = max(300, min(850, round(raw_score)))
        band = self._get_band(score)
        return PDOResult(
            pd_probability=round(pd_probability, 6),
            score=score,
            band=band,
            factor=round(self.factor, 4),
            offset=round(self.offset, 4),
        )

    @staticmethod
    def _get_band(score: int) -> str:
        for floor, label in _BANDS:
            if score >= floor:
                return label
        return "Poor"

    def pd_from_score(self, score: int) -> float:
        """Inverse: convert a score back to PD (for display purposes)."""
        odds = math.exp((self.offset - score) / self.factor)
        return round(odds / (1 + odds), 6)
