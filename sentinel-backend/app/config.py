"""
SENTINEL (PRAVAHA) — Application Configuration
Pydantic-settings driven; reads from .env automatically.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_ROOT = Path(__file__).resolve().parent.parent  # sentinel-backend/


class Settings(BaseSettings):
    """Immutable, validated configuration singleton."""

    model_config = SettingsConfigDict(
        env_file=str(_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ──────────────────────────────────────────
    app_name: str = "sentinel"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # ── Server ───────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # ── GPU ──────────────────────────────────────────────────
    cuda_device: int = 0
    vram_limit_mb: int = 5120
    enable_tensorrt: bool = True

    # ── Model Paths ──────────────────────────────────────────
    yolo_model_path: str = "models/yolov8n.engine"
    raft_model_path: str = "models/raft_small.pth"
    csrnet_model_path: str = "models/csrnet.pth"
    lstm_ae_model_path: str = "models/lstm_ae.pth"
    stgcnn_model_path: str = "models/stgcnn.pth"

    # ── Pipeline ─────────────────────────────────────────────
    target_fps: int = 25
    max_queue_size: int = 30
    frame_skip_heavy: int = 3
    enable_visualization: bool = True
    persistence_interval_seconds: int = 5

    # ── Redis ────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── PostgreSQL ───────────────────────────────────────────
    postgres_url: str = (
        "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel_db"
    )

    # ── MongoDB Atlas ────────────────────────────────────────
    mongodb_url: str = "mongodb+srv://gowsikbabubabu_db_user:sentinel@cluster0.1g1pkb2.mongodb.net/?appName=Cluster0"
    mongodb_db: str = "sentinel_detections"

    # ── InfluxDB ─────────────────────────────────────────────
    influxdb_url: str = "http://localhost:8086"
    influxdb_token: str = "sentinel-token"
    influxdb_org: str = "sentinel"
    influxdb_bucket: str = "metrics"

    # ── RTSP Cameras ─────────────────────────────────────────
    camera_0_url: Optional[str] = None
    camera_1_url: Optional[str] = None

    # ── Observability ────────────────────────────────────────
    metrics_enabled: bool = True

    # ── Derived helpers ──────────────────────────────────────
    @property
    def model_dir(self) -> Path:
        return _ROOT / "models"

    def resolve_model(self, relative: str) -> Path:
        p = _ROOT / relative
        return p


settings = Settings()
