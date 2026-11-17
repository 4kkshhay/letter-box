"""Runtime settings, read from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    app_env: str
    public_base_url: str
    database_path: Path
    migrations_dir: Path
    static_dir: Path
    listen_host: str
    public_port: int
    admin_port: int

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


def get_settings() -> Settings:
    env = os.environ
    return Settings(
        app_env=env.get("APP_ENV", "development"),
        public_base_url=env.get("PUBLIC_BASE_URL", "http://localhost:8610").rstrip("/"),
        database_path=Path(env.get("DATABASE_PATH", "/data/letterbox.db")),
        migrations_dir=Path(env.get("MIGRATIONS_DIR", BACKEND_DIR / "migrations")),
        static_dir=Path(env.get("STATIC_DIR", BACKEND_DIR / "static")),
        listen_host=env.get("LISTEN_HOST", "0.0.0.0"),
        public_port=int(env.get("PUBLIC_LISTEN_PORT", "8000")),
        admin_port=int(env.get("ADMIN_LISTEN_PORT", "8001")),
    )
