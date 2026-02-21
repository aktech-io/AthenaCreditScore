from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

# ── Keyword mapping: sector name → list of regex keyword patterns ─────────────
SECTOR_KEYWORDS: Dict[str, list] = {
    "Agriculture": [
        r"\bagri\b", r"\bfarm\b", r"\bcrop\b", r"\blivestoc\b", r"\bpoultry\b",
        r"\bdairy\b", r"\bmaize\b", r"\bwheat\b", r"\bhorticulture\b", r"\bnursery\b",
        r"\birrigat\b", r"\bfishery\b", r"\baquaculture\b",
    ],
    "Retail": [
        r"\bshop\b", r"\bstore\b", r"\bsupermarket\b", r"\bduka\b", r"\bkiosk\b",
        r"\bwholesale\b", r"\btrade\b", r"\bmerchandise\b", r"\bgeneral goods\b",
        r"\bshopping\b", r"\bvend\b",
    ],
    "Transport": [
        r"\btransport\b", r"\bmatatu\b", r"\bboda\b", r"\btaxi\b", r"\bdelivery\b",
        r"\blogistic\b", r"\bfreight\b", r"\btrucking\b", r"\bcourier\b",
        r"\bsacco.*(transport|vehicle)\b",
    ],
    "Food & Hospitality": [
        r"\brestaurant\b", r"\bcafe\b", r"\bhotel\b", r"\bcanteen\b", r"\bcatering\b",
        r"\bfood\b", r"\bbakery\b", r"\bmkahawa\b", r"\bbar\b",
    ],
    "Healthcare": [
        r"\bclinic\b", r"\bpharmacy\b", r"\bhealth\b", r"\bmedic\b", r"\bhospital\b",
        r"\bdentist\b", r"\bnursing\b", r"\boptician\b",
    ],
    "Education": [
        r"\bschool\b", r"\bcollege\b", r"\btutor\b", r"\binstitu\b", r"\btraining\b",
        r"\bacadem\b", r"\beducation\b",
    ],
    "Construction": [
        r"\bconstruct\b", r"\bbuilder\b", r"\bcontractor\b", r"\bplumbing\b",
        r"\belectrician\b", r"\bcarpentr\b", r"\bpainting\b", r"\bbricklay\b",
        r"\barchitect\b", r"\breal estate\b",
    ],
    "Technology": [
        r"\btech\b", r"\bsoftware\b", r"\bIT\b", r"\bcomputer\b", r"\binternet\b",
        r"\bmobile money\b", r"\bweb\b", r"\bdigital\b", r"\bICT\b",
    ],
    "Financial Services": [
        r"\bsacco\b", r"\bmicrofinanc\b", r"\bcredit\b", r"\bloan\b", r"\binsurance\b",
        r"\binvestment\b", r"\bforex\b", r"\bremittance\b",
    ],
    "Manufacturing": [
        r"\bmanufactur\b", r"\bproduction\b", r"\bprocessing\b", r"\bfactory\b",
        r"\bindustry\b", r"\bassembly\b",
    ],
    "Beauty & Personal Care": [
        r"\bsalon\b", r"\bbarber\b", r"\bspa\b", r"\bbeauty\b", r"\bnails\b",
        r"\bcosmetics\b",
    ],
}

UNKNOWN_SECTOR = "Other/Mixed"


class SectorMapper:
    """
    Maps free-text business descriptions to standardized sector labels
    using a keyword-based rule engine.
    Falls back to a zero-shot HuggingFace classifier if no keyword matches.
    """

    def __init__(self, use_ml_fallback: bool = False):
        self.use_ml_fallback = use_ml_fallback
        self._classifier = None
        if use_ml_fallback:
            self._load_classifier()

    def _load_classifier(self):
        try:
            from transformers import pipeline
            self._classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
            )
        except ImportError:
            pass  # Transformers not installed — keyword-only mode

    def map(self, description: str) -> Tuple[str, str]:
        """
        Returns (sector, method) where method is 'keyword' or 'zero_shot'.
        """
        if not description:
            return UNKNOWN_SECTOR, "default"

        desc_lower = description.lower()

        for sector, patterns in SECTOR_KEYWORDS.items():
            for pattern in patterns:
                if re.search(pattern, desc_lower, re.IGNORECASE):
                    return sector, "keyword"

        # Zero-shot fallback
        if self.use_ml_fallback and self._classifier:
            labels = list(SECTOR_KEYWORDS.keys()) + [UNKNOWN_SECTOR]
            result = self._classifier(
                description,
                candidate_labels=labels,
                multi_label=False,
            )
            top_label = result["labels"][0]
            top_score = result["scores"][0]
            if top_score >= 0.50:
                return top_label, "zero_shot"

        return UNKNOWN_SECTOR, "default"

    def map_batch(self, descriptions: list[str]) -> list[dict]:
        """Batch-map a list of descriptions to sectors."""
        return [
            {"description": d, "sector": self.map(d)[0], "method": self.map(d)[1]}
            for d in descriptions
        ]
