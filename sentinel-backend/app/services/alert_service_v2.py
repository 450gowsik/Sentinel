"""
SENTINEL — Enhanced Alert Service
Production-grade alert management with MongoDB persistence.

Production patterns:
  • Repository pattern for data access
  • Circuit breaker for database resilience  
  • Write-through caching
  • Deduplication with time windows
  • Bulk operations for efficiency
  • Event-driven architecture support
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import structlog
from pydantic import BaseModel, Field

from app.database.mongodb import mongodb
from app.schemas.alert import (
    AlertAck,
    AlertCreate,
    AlertResponse,
    AlertStatus,
    AlertTier,
)

logger = structlog.get_logger(__name__)


# ── Circuit Breaker ──────────────────────────────────────────


class CircuitState(str, Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker pattern for database resilience.
    
    States:
      • CLOSED: Normal operation, failures increment counter
      • OPEN: All calls fail fast without hitting DB
      • HALF_OPEN: Allow one test request to check recovery
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> CircuitState:
        return self._state
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                else:
                    raise CircuitBreakerOpenError("Circuit breaker is OPEN")
            
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.half_open_max_calls:
                    raise CircuitBreakerOpenError("Circuit breaker HALF_OPEN limit reached")
                self._half_open_calls += 1
        
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise
    
    async def _on_success(self):
        async with self._lock:
            self._failure_count = 0
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                logger.info("circuit_breaker.closed", reason="successful_call")
    
    async def _on_failure(self):
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = asyncio.get_event_loop().time()
            
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "circuit_breaker.opened",
                    failure_count=self._failure_count,
                )
    
    def _should_attempt_reset(self) -> bool:
        if self._last_failure_time is None:
            return True
        elapsed = asyncio.get_event_loop().time() - self._last_failure_time
        return elapsed >= self.recovery_timeout


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# ── Alert Repository ─────────────────────────────────────────


class AlertRepository:
    """
    Data access layer for alerts.
    Handles MongoDB persistence with fallback to memory.
    """
    
    COLLECTION_NAME = "alerts"
    
    def __init__(self):
        self._memory_store: Dict[str, Dict] = {}
        self._circuit_breaker = CircuitBreaker()
    
    @property
    def _collection(self):
        if not mongodb.is_connected():
            return None
        return mongodb.get_collection(self.COLLECTION_NAME)
    
    async def create(self, alert_data: Dict) -> Dict:
        """Create a new alert."""
        alert_data["_id"] = alert_data.get("id", str(uuid.uuid4())[:12])
        alert_data["created_at"] = datetime.utcnow()
        alert_data["updated_at"] = datetime.utcnow()
        
        if self._collection is not None:
            try:
                await self._circuit_breaker.call(
                    self._collection.insert_one, alert_data
                )
            except (CircuitBreakerOpenError, Exception) as e:
                logger.warning("alert_repo.db_write_failed", error=str(e))
                # Fallback to memory
                self._memory_store[alert_data["_id"]] = alert_data
        else:
            self._memory_store[alert_data["_id"]] = alert_data
        
        return alert_data
    
    async def get_by_id(self, alert_id: str) -> Optional[Dict]:
        """Get alert by ID."""
        if self._collection is not None:
            try:
                return await self._circuit_breaker.call(
                    self._collection.find_one, {"_id": alert_id}
                )
            except (CircuitBreakerOpenError, Exception) as e:
                logger.warning("alert_repo.db_read_failed", error=str(e))
        
        return self._memory_store.get(alert_id)
    
    async def find(
        self,
        filters: Dict = None,
        limit: int = 50,
        skip: int = 0,
        sort_by: str = "created_at",
        sort_order: int = -1,
    ) -> List[Dict]:
        """Find alerts with filters."""
        filters = filters or {}
        
        if self._collection is not None:
            try:
                cursor = self._collection.find(filters)
                cursor = cursor.sort(sort_by, sort_order)
                cursor = cursor.skip(skip).limit(limit)
                return await self._circuit_breaker.call(cursor.to_list, length=limit)
            except (CircuitBreakerOpenError, Exception) as e:
                logger.warning("alert_repo.db_query_failed", error=str(e))
        
        # Memory fallback
        alerts = list(self._memory_store.values())
        if "status" in filters:
            alerts = [a for a in alerts if a.get("status") == filters["status"]]
        if "camera_id" in filters:
            alerts = [a for a in alerts if a.get("camera_id") == filters["camera_id"]]
        
        alerts.sort(key=lambda x: x.get("created_at", datetime.min), reverse=(sort_order == -1))
        return alerts[skip:skip + limit]
    
    async def update(self, alert_id: str, update_data: Dict) -> Optional[Dict]:
        """Update an alert."""
        update_data["updated_at"] = datetime.utcnow()
        
        if self._collection is not None:
            try:
                result = await self._circuit_breaker.call(
                    self._collection.find_one_and_update,
                    {"_id": alert_id},
                    {"$set": update_data},
                    return_document=True,
                )
                return result
            except (CircuitBreakerOpenError, Exception) as e:
                logger.warning("alert_repo.db_update_failed", error=str(e))
        
        # Memory fallback
        if alert_id in self._memory_store:
            self._memory_store[alert_id].update(update_data)
            return self._memory_store[alert_id]
        return None
    
    async def count(self, filters: Dict = None) -> int:
        """Count alerts matching filters."""
        filters = filters or {}
        
        if self._collection is not None:
            try:
                return await self._circuit_breaker.call(
                    self._collection.count_documents, filters
                )
            except (CircuitBreakerOpenError, Exception) as e:
                logger.warning("alert_repo.db_count_failed", error=str(e))
        
        # Memory fallback
        alerts = list(self._memory_store.values())
        if "status" in filters:
            alerts = [a for a in alerts if a.get("status") == filters["status"]]
        return len(alerts)
    
    async def delete_old(self, before: datetime) -> int:
        """Delete alerts older than specified time."""
        if self._collection is not None:
            try:
                result = await self._circuit_breaker.call(
                    self._collection.delete_many,
                    {"created_at": {"$lt": before}}
                )
                return result.deleted_count
            except (CircuitBreakerOpenError, Exception) as e:
                logger.warning("alert_repo.db_delete_failed", error=str(e))
        
        # Memory fallback
        stale = [
            aid for aid, alert in self._memory_store.items()
            if alert.get("created_at", datetime.max) < before
        ]
        for aid in stale:
            del self._memory_store[aid]
        return len(stale)


# ── Enhanced Alert Service ───────────────────────────────────


class EnhancedAlertService:
    """
    Production-grade alert service.
    
    Features:
      • MongoDB persistence with memory fallback
      • Alert deduplication (same alert within window)
      • Bulk operations
      • Event emission for subscribers
      • Statistics and metrics
    """
    
    DEDUP_WINDOW_SECONDS = 60  # Dedupe identical alerts within 60s
    
    def __init__(self):
        self._repo = AlertRepository()
        self._dedup_cache: Dict[str, datetime] = {}
        self._event_handlers: List[Callable] = []
    
    def _generate_dedup_key(self, alert: AlertCreate) -> str:
        """Generate deduplication key for an alert."""
        key_data = f"{alert.camera_id}:{alert.tier}:{alert.zone_id or 'none'}"
        return hashlib.md5(key_data.encode()).hexdigest()[:16]
    
    def _is_duplicate(self, dedup_key: str) -> bool:
        """Check if alert is a duplicate within the dedup window."""
        if dedup_key not in self._dedup_cache:
            return False
        
        last_seen = self._dedup_cache[dedup_key]
        if (datetime.utcnow() - last_seen).total_seconds() < self.DEDUP_WINDOW_SECONDS:
            return True
        
        return False
    
    async def create(self, alert: AlertCreate) -> Optional[AlertResponse]:
        """
        Create a new alert with deduplication.
        
        Returns None if alert is a duplicate.
        """
        # Check for duplicates
        dedup_key = self._generate_dedup_key(alert)
        if self._is_duplicate(dedup_key):
            logger.debug("alert.deduplicated", camera_id=alert.camera_id, tier=alert.tier)
            return None
        
        # Update dedup cache
        self._dedup_cache[dedup_key] = datetime.utcnow()
        
        # Generate ID
        alert_id = str(uuid.uuid4())[:12]
        
        # Build document
        alert_doc = {
            "id": alert_id,
            "camera_id": alert.camera_id,
            "tier": alert.tier.value,
            "status": AlertStatus.ACTIVE.value,
            "reason": alert.reason,
            "risk_score": alert.risk_score,
            "density_count": alert.density_count,
            "anomaly_score": alert.anomaly_score,
            "zone_id": alert.zone_id,
            "frame_idx": alert.frame_idx,
        }
        
        # Persist
        saved = await self._repo.create(alert_doc)
        
        # Build response
        response = AlertResponse(
            id=saved["id"],
            camera_id=saved["camera_id"],
            tier=AlertTier(saved["tier"]),
            status=AlertStatus(saved["status"]),
            reason=saved["reason"],
            risk_score=saved["risk_score"],
            density_count=saved.get("density_count", 0),
            anomaly_score=saved.get("anomaly_score", 0),
            zone_id=saved.get("zone_id"),
            created_at=saved.get("created_at", datetime.utcnow()),
        )
        
        logger.info(
            "alert.created",
            id=alert_id,
            tier=alert.tier.value,
            camera_id=alert.camera_id,
        )
        
        # Emit event
        await self._emit_event("alert_created", response)
        
        return response
    
    async def get(self, alert_id: str) -> Optional[AlertResponse]:
        """Get alert by ID."""
        doc = await self._repo.get_by_id(alert_id)
        if not doc:
            return None
        return self._doc_to_response(doc)
    
    async def list_alerts(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[AlertStatus] = None,
        camera_id: Optional[str] = None,
        tier: Optional[AlertTier] = None,
        since: Optional[datetime] = None,
    ) -> List[AlertResponse]:
        """List alerts with filters."""
        filters = {}
        
        if status:
            filters["status"] = status.value
        if camera_id:
            filters["camera_id"] = camera_id
        if tier:
            filters["tier"] = tier.value
        if since:
            filters["created_at"] = {"$gte": since}
        
        docs = await self._repo.find(
            filters=filters,
            limit=limit,
            skip=offset,
        )
        
        return [self._doc_to_response(doc) for doc in docs]
    
    async def acknowledge(
        self, alert_id: str, ack: AlertAck
    ) -> Optional[AlertResponse]:
        """Acknowledge an alert."""
        update = {
            "status": AlertStatus.ACKNOWLEDGED.value,
            "acknowledged_at": datetime.utcnow(),
            "acknowledged_by": ack.operator_id,
            "ack_notes": ack.notes,
        }
        
        doc = await self._repo.update(alert_id, update)
        if not doc:
            return None
        
        response = self._doc_to_response(doc)
        
        logger.info(
            "alert.acknowledged",
            id=alert_id,
            by=ack.operator_id,
        )
        
        await self._emit_event("alert_acknowledged", response)
        
        return response
    
    async def resolve(self, alert_id: str, resolved_by: str) -> Optional[AlertResponse]:
        """Mark alert as resolved."""
        update = {
            "status": AlertStatus.RESOLVED.value,
            "resolved_at": datetime.utcnow(),
            "resolved_by": resolved_by,
        }
        
        doc = await self._repo.update(alert_id, update)
        if not doc:
            return None
        
        response = self._doc_to_response(doc)
        await self._emit_event("alert_resolved", response)
        
        return response
    
    async def active_count(self) -> int:
        """Get count of active alerts."""
        return await self._repo.count({"status": AlertStatus.ACTIVE.value})
    
    async def stats(self) -> Dict:
        """Get alert statistics."""
        return {
            "total": await self._repo.count(),
            "active": await self._repo.count({"status": AlertStatus.ACTIVE.value}),
            "acknowledged": await self._repo.count({"status": AlertStatus.ACKNOWLEDGED.value}),
            "resolved": await self._repo.count({"status": AlertStatus.RESOLVED.value}),
            "by_tier": {
                "info": await self._repo.count({"tier": AlertTier.INFO.value}),
                "warning": await self._repo.count({"tier": AlertTier.WARNING.value}),
                "danger": await self._repo.count({"tier": AlertTier.DANGER.value}),
                "emergency": await self._repo.count({"tier": AlertTier.EMERGENCY.value}),
            },
        }
    
    async def cleanup(self, max_age_hours: int = 24) -> int:
        """Remove old alerts."""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        deleted = await self._repo.delete_old(cutoff)
        
        if deleted > 0:
            logger.info("alert.cleanup", deleted=deleted, max_age_hours=max_age_hours)
        
        return deleted
    
    def _doc_to_response(self, doc: Dict) -> AlertResponse:
        """Convert MongoDB document to response model."""
        return AlertResponse(
            id=doc.get("id", doc.get("_id")),
            camera_id=doc["camera_id"],
            tier=AlertTier(doc["tier"]),
            status=AlertStatus(doc.get("status", "ACTIVE")),
            reason=doc["reason"],
            risk_score=doc["risk_score"],
            density_count=doc.get("density_count", 0),
            anomaly_score=doc.get("anomaly_score", 0),
            zone_id=doc.get("zone_id"),
            created_at=doc.get("created_at", datetime.utcnow()),
            acknowledged_at=doc.get("acknowledged_at"),
            acknowledged_by=doc.get("acknowledged_by"),
        )
    
    def on_event(self, handler: Callable):
        """Register event handler for alert events."""
        self._event_handlers.append(handler)
    
    async def _emit_event(self, event_type: str, alert: AlertResponse):
        """Emit event to all registered handlers."""
        for handler in self._event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_type, alert)
                else:
                    handler(event_type, alert)
            except Exception as e:
                logger.error("alert.event_handler_failed", error=str(e))


# Global singleton (backward compatible)
alert_service = EnhancedAlertService()
