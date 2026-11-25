"""Typed configuration (pydantic) for the network generator, scoring and runtime settings."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
CYPHER_DIR = ROOT / "cypher"
DATA_DIR = ROOT / "data"
REFERENCE_DIR = DATA_DIR / "reference"
GENERATED_DIR = DATA_DIR / "generated"
REPORTS_DIR = ROOT / "reports"
DOCS_DIR = ROOT / "docs"

load_dotenv(ROOT / ".env")


class ProfileConfig(BaseModel):
    bom_depth: int = Field(4, ge=2, le=10)
    n_finished: int = Field(240, ge=5)
    l1_per_finished: float = 1.15
    level_decay: float = Field(0.6, gt=0, le=1)
    n_tier1: int = 150
    n_tier2: int = 70
    n_tier3: int = 24
    n_plants: int = 16
    n_hospitals: int = 1400
    n_municipalities: int = 450
    skus_per_hospital: float = 18
    lots_per_finished: float = 170
    component_lot_reuse: float = 5
    raw_lot_reuse: float = 12
    include_lots: bool = True


class SourcingConfig(BaseModel):
    tier1_supplier_count_probs: list[float]
    tier2_supplier_count_probs: list[float]
    tier2_concentration_alpha: float
    false_dual_source_share: float
    sub_tier_single_buy_prob: float = 0.3
    concentrated_raw: dict[str, int]
    tier1_domestic_share: float
    plant_domestic_share: float
    tier3_country_weights: dict[str, float]
    tier2_country_weights: dict[str, float]

    @model_validator(mode="after")
    def _probs(self) -> SourcingConfig:
        for p in (self.tier1_supplier_count_probs, self.tier2_supplier_count_probs):
            if abs(sum(p) - 1) > 1e-6:
                raise ValueError("supplier count probabilities must sum to 1")
        return self


class LogisticsConfig(BaseModel):
    air_share: float
    dc_ufs: list[str]
    second_dc_probability: float
    second_dc_max_km: float


class InventoryConfig(BaseModel):
    days_cover_median: float
    days_cover_sigma: float
    safety_stock_days: float


class NetworkConfig(BaseModel):
    seed: int
    as_of: str
    reference_year: int
    profile_name: str
    profile: ProfileConfig
    aura_limits: dict[str, int]
    sourcing: SourcingConfig
    logistics: LogisticsConfig
    inventory: InventoryConfig


def load_network_config(
    profile: str = "full", seed: int | None = None, path: Path | None = None
) -> NetworkConfig:
    raw = yaml.safe_load((path or CONFIG_DIR / "network.yaml").read_text(encoding="utf-8"))
    profiles = raw["profiles"]
    if profile not in profiles:
        raise ValueError(f"unknown profile '{profile}'. Available: {', '.join(profiles)}")
    # benchmark profiles inherit unspecified keys from `full`
    merged = {**profiles["full"], **profiles[profile]}
    return NetworkConfig(
        seed=seed if seed is not None else raw["seed"],
        as_of=raw["as_of"],
        reference_year=raw["reference_year"],
        profile_name=profile,
        profile=ProfileConfig(**merged),
        aura_limits=raw["aura_limits"],
        sourcing=SourcingConfig(**raw["sourcing"]),
        logistics=LogisticsConfig(**raw["logistics"]),
        inventory=InventoryConfig(**raw["inventory"]),
    )


class ScoringConfig(BaseModel):
    weights: dict[str, float]
    ttr_days: int
    ttr_days_by_tier: dict[int, int] = {1: 60, 2: 120, 3: 180}
    sensitivity_scenarios: dict[str, dict[str, float]]

    @model_validator(mode="after")
    def _weights(self) -> ScoringConfig:
        for name, w in {"weights": self.weights, **self.sensitivity_scenarios}.items():
            if abs(sum(w.values()) - 1) > 0.01:
                raise ValueError(f"scoring weights '{name}' must sum to 1.0 (got {sum(w.values()):.3f})")
        return self


def load_scoring_config(path: Path | None = None) -> ScoringConfig:
    raw = yaml.safe_load((path or CONFIG_DIR / "scoring.yaml").read_text(encoding="utf-8"))
    return ScoringConfig(**raw)


class Neo4jSettings(BaseModel):
    uri: str = "neo4j://localhost:7687"
    user: str = "neo4j"
    password: str = "change-me-local"
    database: str = "neo4j"


def neo4j_settings(target: str = "local") -> Neo4jSettings:
    """Read connection settings from the environment (.env). target = local | aura."""
    if target == "aura":
        uri = os.getenv("AURA_URI")
        pwd = os.getenv("AURA_PASSWORD")
        if not uri or not pwd:
            raise RuntimeError(
                "AURA_URI / AURA_PASSWORD are not set. Create an AuraDB Free instance and fill .env "
                "(see .env.example and PENDENCIAS.md)."
            )
        return Neo4jSettings(
            uri=uri,
            user=os.getenv("AURA_USER", "neo4j"),
            password=pwd,
            database=os.getenv("AURA_DATABASE", "neo4j"),
        )
    return Neo4jSettings(
        uri=os.getenv("NEO4J_URI", "neo4j://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "change-me-local"),
        database=os.getenv("NEO4J_DATABASE", "neo4j"),
    )
