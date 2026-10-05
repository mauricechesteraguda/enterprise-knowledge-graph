# type-10052026-Maurice: Centralize deterministic, bounded local configuration.
"""Deterministic, environment-backed application settings."""
from datetime import date
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from kg.observability.tracing import trace_call
class Settings(BaseSettings):
    """Safe defaults for local and CI execution; credentials are optional."""
    model_config = SettingsConfigDict(env_prefix="KG_", env_file=".env", extra="ignore")
    service_name: str = "knowledge-graph-api"
    environment: str = "local"
    data_as_of: date = date(2026, 1, 31)
    artifact_dir: Path = Path("artifacts")
    log_level: str = "INFO"
    api_key: str = Field(default="", repr=False)
    max_question_length: int = Field(default=1000, ge=1, le=10_000)
    max_evidence_rows: int = Field(default=50, ge=1, le=100)
    max_query_rows: int = Field(default=1000, ge=1, le=1000)
    query_timeout_seconds: int = Field(default=5, ge=1, le=5)
    fixture_seed: int = 42
    fixture_dir: Path = Path("data/raw")
    mappings_dir: Path = Path("mappings")
    crm_dsn: str = Field(default="", repr=False)
    billing_csv: Path = Path("data/raw/billing.csv")
    support_json: Path = Path("data/raw/support.json")
    source_manifest: Path = Path("data/sources.json")
    # type-10052026-Maurice: Keep browser access opt-in rather than wildcard by default.
    cors_origins: list[str] = Field(default_factory=list)
@trace_call
def get_settings() -> Settings:
    """Build deterministic settings without cloud credentials."""
    return Settings()
