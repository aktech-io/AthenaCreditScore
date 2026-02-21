from __future__ import annotations

"""
Feature Store — reads and writes versioned feature vectors to/from PostgreSQL.

Tables used (from schema.sql):
  - feature_definitions   : schema/metadata per named feature set
  - feature_values        : customer-level feature vector snapshots (JSONB)

Provides:
  - write_features()      : upsert a feature vector for a customer
  - read_features()       : retrieve the latest vector by feature set name
  - list_feature_sets()   : enumerate registered definitions
  - register_definition() : create or update a feature set definition
"""

import json
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger(__name__)


async def register_definition(
    db: AsyncSession,
    feature_set_name: str,
    version: str,
    feature_names: List[str],
    description: str = "",
    encoding_config: Optional[Dict] = None,
) -> int:
    """Register a new feature set definition. Returns the definition_id."""
    result = await db.execute(text("""
        INSERT INTO feature_definitions
            (feature_set_name, version, feature_names, description, encoding_config)
        VALUES
            (:name, :ver, :fnames::jsonb, :desc, :enc::jsonb)
        ON CONFLICT (feature_set_name, version)
        DO UPDATE SET
            feature_names   = EXCLUDED.feature_names,
            description     = EXCLUDED.description,
            encoding_config = EXCLUDED.encoding_config
        RETURNING definition_id
    """), {
        "name":   feature_set_name,
        "ver":    version,
        "fnames": json.dumps(feature_names),
        "desc":   description,
        "enc":    json.dumps(encoding_config or {}),
    })
    row = result.fetchone()
    await db.commit()
    definition_id = row[0]
    logger.info("Feature definition registered", name=feature_set_name, version=version, id=definition_id)
    return definition_id


async def write_features(
    db: AsyncSession,
    customer_id: int,
    feature_set_name: str,
    version: str,
    feature_vector: Dict[str, Any],
    computed_at: Optional[date] = None,
) -> None:
    """
    Upsert a feature vector for a customer.
    If a row already exists for (customer_id, feature_set_name, version, computed_at),
    it is updated in place.
    """
    computed_at = computed_at or date.today()

    # Resolve definition_id
    defn_row = await db.execute(text("""
        SELECT definition_id FROM feature_definitions
        WHERE feature_set_name = :name AND version = :ver
        LIMIT 1
    """), {"name": feature_set_name, "ver": version})
    defn = defn_row.fetchone()
    if not defn:
        raise ValueError(
            f"Feature definition '{feature_set_name}' v{version} not registered. "
            "Call register_definition() first."
        )
    definition_id = defn[0]

    await db.execute(text("""
        INSERT INTO feature_values
            (customer_id, definition_id, feature_vector, computed_at)
        VALUES
            (:cid, :did, :fv::jsonb, :dt)
        ON CONFLICT (customer_id, definition_id, computed_at)
        DO UPDATE SET feature_vector = EXCLUDED.feature_vector
    """), {
        "cid": customer_id,
        "did": definition_id,
        "fv":  json.dumps(feature_vector, default=str),
        "dt":  computed_at,
    })
    await db.commit()
    logger.debug("Features written", customer_id=customer_id, feature_set=feature_set_name, version=version)


async def read_features(
    db: AsyncSession,
    customer_id: int,
    feature_set_name: str,
    version: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve the latest feature vector for a customer.
    If version is None, the latest version is used.
    Returns None if no features found.
    """
    version_filter = "AND fd.version = :ver" if version else ""
    row = await db.execute(text(f"""
        SELECT fv.feature_vector, fd.version, fv.computed_at
        FROM feature_values fv
        JOIN feature_definitions fd ON fd.definition_id = fv.definition_id
        WHERE fv.customer_id = :cid
          AND fd.feature_set_name = :name
          {version_filter}
        ORDER BY fv.computed_at DESC, fd.version DESC
        LIMIT 1
    """), {"cid": customer_id, "name": feature_set_name, "ver": version})
    r = row.fetchone()
    if not r:
        logger.info("No features found", customer_id=customer_id, feature_set=feature_set_name)
        return None
    fv = r[0] if isinstance(r[0], dict) else json.loads(r[0])
    fv["_meta"] = {"version": r[1], "computed_at": str(r[2])}
    return fv


async def read_features_batch(
    db: AsyncSession,
    customer_ids: List[int],
    feature_set_name: str,
    version: Optional[str] = None,
) -> Dict[int, Dict[str, Any]]:
    """Retrieve latest features for a batch of customer IDs."""
    results: Dict[int, Dict[str, Any]] = {}
    for cid in customer_ids:
        fv = await read_features(db, cid, feature_set_name, version)
        if fv:
            results[cid] = fv
    return results


async def list_feature_sets(db: AsyncSession) -> List[Dict[str, Any]]:
    """Enumerate all registered feature set definitions."""
    rows = await db.execute(text("""
        SELECT definition_id, feature_set_name, version, description, created_at
        FROM feature_definitions
        ORDER BY feature_set_name, version DESC
    """))
    return [
        {
            "definition_id": r[0],
            "feature_set_name": r[1],
            "version": r[2],
            "description": r[3],
            "created_at": str(r[4]),
        }
        for r in rows.fetchall()
    ]


async def get_feature_coverage(
    db: AsyncSession,
    feature_set_name: str,
    version: str,
    since: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Return coverage statistics: how many customers have features computed,
    and when the latest computation was.
    """
    since_filter = "AND fv.computed_at >= :since" if since else ""
    row = await db.execute(text(f"""
        SELECT
            COUNT(DISTINCT fv.customer_id) AS n_customers,
            MAX(fv.computed_at) AS latest_at,
            MIN(fv.computed_at) AS earliest_at
        FROM feature_values fv
        JOIN feature_definitions fd ON fd.definition_id = fv.definition_id
        WHERE fd.feature_set_name = :name AND fd.version = :ver
          {since_filter}
    """), {"name": feature_set_name, "ver": version, "since": since})
    r = row.fetchone()
    return {
        "feature_set": feature_set_name,
        "version": version,
        "n_customers": r[0] or 0,
        "latest_computed_at": str(r[1]) if r[1] else None,
        "earliest_computed_at": str(r[2]) if r[2] else None,
    }
