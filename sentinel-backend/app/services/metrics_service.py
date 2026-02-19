"""
SENTINEL — Metrics Service
Prometheus counters, histograms, and gauges for pipeline observability.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, Info
import structlog

logger = structlog.get_logger(__name__)

# ── Application Info ─────────────────────────────────────────

app_info = Info("sentinel", "SENTINEL crowd safety platform")
app_info.info({
    "version": "2.0.0",
    "gpu": "RTX 3050 6GB",
    "cuda": "11.8",
})

# ── Frame Processing ─────────────────────────────────────────

frames_processed = Counter(
    "sentinel_frames_processed_total",
    "Total frames processed through pipeline",
    ["camera_id"],
)

frames_dropped = Counter(
    "sentinel_frames_dropped_total",
    "Total frames dropped due to backpressure",
    ["camera_id", "stage"],
)

pipeline_fps = Gauge(
    "sentinel_pipeline_fps",
    "Current FPS of the pipeline",
    ["camera_id"],
)

# ── Stage Latency ────────────────────────────────────────────

stage_latency = Histogram(
    "sentinel_stage_latency_seconds",
    "Per-stage processing latency",
    ["stage"],
    buckets=[0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0],
)

pipeline_latency = Histogram(
    "sentinel_pipeline_latency_seconds",
    "End-to-end pipeline latency",
    ["camera_id"],
    buckets=[0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0],
)

# ── Queue Depth ──────────────────────────────────────────────

queue_depth = Gauge(
    "sentinel_queue_depth",
    "Current depth of inter-stage queues",
    ["buffer_name"],
)

# ── Detections & Risk ────────────────────────────────────────

person_count = Gauge(
    "sentinel_person_count",
    "Current detected person count",
    ["camera_id"],
)

density_count = Gauge(
    "sentinel_density_count",
    "Current estimated crowd density",
    ["camera_id"],
)

risk_score = Gauge(
    "sentinel_risk_score",
    "Current composite risk score",
    ["camera_id"],
)

congestion_score = Gauge(
    "sentinel_congestion_score",
    "Current congestion score",
    ["camera_id"],
)

# ── Alerts ───────────────────────────────────────────────────

alerts_created = Counter(
    "sentinel_alerts_created_total",
    "Total alerts generated",
    ["camera_id", "tier"],
)

alerts_active = Gauge(
    "sentinel_alerts_active",
    "Currently active (unacknowledged) alerts",
)

# ── GPU ──────────────────────────────────────────────────────

gpu_vram_used = Gauge(
    "sentinel_gpu_vram_used_mb",
    "GPU VRAM currently used (MB)",
)

gpu_vram_free = Gauge(
    "sentinel_gpu_vram_free_mb",
    "GPU VRAM free (MB)",
)

gpu_utilization = Gauge(
    "sentinel_gpu_utilization_pct",
    "GPU utilization percentage",
)

gpu_temperature = Gauge(
    "sentinel_gpu_temperature_c",
    "GPU temperature (Celsius)",
)

# ── WebSocket ────────────────────────────────────────────────

ws_connections = Gauge(
    "sentinel_ws_connections",
    "Active WebSocket connections",
)

ws_frames_sent = Counter(
    "sentinel_ws_frames_sent_total",
    "Total frames sent via WebSocket",
    ["camera_id"],
)


def record_frame_metrics(camera_id: str, packet_data: dict) -> None:
    """Convenience: update all gauges from a processed frame."""
    frames_processed.labels(camera_id=camera_id).inc()
    person_count.labels(camera_id=camera_id).set(packet_data.get("person_count", 0))
    density_count.labels(camera_id=camera_id).set(packet_data.get("density", 0))
    risk_score.labels(camera_id=camera_id).set(packet_data.get("risk_score", 0))
    congestion_score.labels(camera_id=camera_id).set(packet_data.get("congestion", 0))

    # Per-stage latency
    for stage_name, latency_ms in packet_data.get("stage_latencies", {}).items():
        stage_latency.labels(stage=stage_name).observe(latency_ms / 1000)

    if "latency_ms" in packet_data:
        pipeline_latency.labels(camera_id=camera_id).observe(
            packet_data["latency_ms"] / 1000
        )
