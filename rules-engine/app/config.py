import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str
    contracts_dir: Path
    scheduler_enabled: bool
    sample_size: int
    failure_webhook_url: str | None  # phase 4: n8n webhook


def get_settings() -> Settings:
    return Settings(
        database_url=os.environ.get(
            "DATABASE_URL", "postgresql://dataguard:dataguard@localhost:5432/dataguard"
        ),
        contracts_dir=Path(os.environ.get("CONTRACTS_DIR", Path(__file__).resolve().parents[2] / "contracts")),
        scheduler_enabled=os.environ.get("SCHEDULER_ENABLED", "false").lower() == "true",
        sample_size=int(os.environ.get("SAMPLE_SIZE", "5")),
        failure_webhook_url=os.environ.get("FAILURE_WEBHOOK_URL") or None,
    )
