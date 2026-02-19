"""
SENTINEL — Background Task Scheduler
Production-grade async task management.

Features:
  • Async task scheduling with intervals
  • Task health monitoring
  • Graceful shutdown
  • Task retry with backoff
  • Metrics collection
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Coroutine, Dict, List, Optional
import structlog

logger = structlog.get_logger(__name__)


class TaskState(str, Enum):
    """Task execution state."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskStats:
    """Task execution statistics."""
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    last_run: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_error: Optional[str] = None
    avg_duration_ms: float = 0.0
    
    def record_success(self, duration_ms: float) -> None:
        self.total_runs += 1
        self.successful_runs += 1
        self.last_run = datetime.utcnow()
        self.last_success = self.last_run
        # Running average
        self.avg_duration_ms = (
            (self.avg_duration_ms * (self.successful_runs - 1) + duration_ms)
            / self.successful_runs
        )
    
    def record_failure(self, error: str) -> None:
        self.total_runs += 1
        self.failed_runs += 1
        self.last_run = datetime.utcnow()
        self.last_error = error


@dataclass
class ScheduledTask:
    """A scheduled background task."""
    name: str
    func: Callable[..., Coroutine[Any, Any, Any]]
    interval_seconds: float
    run_immediately: bool = False
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    enabled: bool = True
    
    # Runtime state
    state: TaskState = field(default=TaskState.PENDING)
    stats: TaskStats = field(default_factory=TaskStats)
    _task: Optional[asyncio.Task] = field(default=None, repr=False)
    _stop_event: asyncio.Event = field(default_factory=asyncio.Event, repr=False)


class BackgroundScheduler:
    """
    Async background task scheduler.
    
    Usage:
        scheduler = BackgroundScheduler()
        
        @scheduler.task(interval_seconds=60)
        async def cleanup_old_data():
            # Your task logic
            pass
        
        # Start scheduler
        await scheduler.start()
        
        # Stop scheduler
        await scheduler.stop()
    """
    
    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._shutdown_event = asyncio.Event()
    
    def task(
        self,
        interval_seconds: float,
        *,
        name: Optional[str] = None,
        run_immediately: bool = False,
        max_retries: int = 3,
        retry_delay_seconds: float = 5.0,
    ) -> Callable:
        """
        Decorator to register a scheduled task.
        
        Args:
            interval_seconds: How often to run the task
            name: Task name (defaults to function name)
            run_immediately: Run once on startup
            max_retries: Max retry attempts on failure
            retry_delay_seconds: Delay between retries
        """
        def decorator(func: Callable[..., Coroutine]) -> Callable:
            task_name = name or func.__name__
            
            self._tasks[task_name] = ScheduledTask(
                name=task_name,
                func=func,
                interval_seconds=interval_seconds,
                run_immediately=run_immediately,
                max_retries=max_retries,
                retry_delay_seconds=retry_delay_seconds,
            )
            
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def register(
        self,
        func: Callable[..., Coroutine],
        interval_seconds: float,
        **kwargs,
    ) -> None:
        """Register a task programmatically."""
        name = kwargs.get("name", func.__name__)
        self._tasks[name] = ScheduledTask(
            name=name,
            func=func,
            interval_seconds=interval_seconds,
            **{k: v for k, v in kwargs.items() if k != "name"},
        )
    
    async def start(self) -> None:
        """Start all scheduled tasks."""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        self._running = True
        self._shutdown_event.clear()
        
        logger.info("Starting background scheduler", task_count=len(self._tasks))
        
        for task in self._tasks.values():
            if task.enabled:
                task._stop_event.clear()
                task._task = asyncio.create_task(
                    self._run_task_loop(task),
                    name=f"scheduler:{task.name}",
                )
    
    async def stop(self, timeout: float = 10.0) -> None:
        """Stop all scheduled tasks gracefully."""
        if not self._running:
            return
        
        logger.info("Stopping background scheduler...")
        self._running = False
        self._shutdown_event.set()
        
        # Signal all tasks to stop
        for task in self._tasks.values():
            task._stop_event.set()
        
        # Wait for tasks to complete
        tasks = [t._task for t in self._tasks.values() if t._task]
        if tasks:
            done, pending = await asyncio.wait(tasks, timeout=timeout)
            
            # Force cancel any stuck tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Background scheduler stopped")
    
    async def _run_task_loop(self, task: ScheduledTask) -> None:
        """Main loop for a scheduled task."""
        task.state = TaskState.RUNNING
        
        # Run immediately if configured
        if task.run_immediately:
            await self._execute_task(task)
        
        while not task._stop_event.is_set():
            try:
                # Wait for interval or shutdown
                await asyncio.wait_for(
                    task._stop_event.wait(),
                    timeout=task.interval_seconds,
                )
                break  # Stop event was set
            except asyncio.TimeoutError:
                # Interval elapsed, run task
                await self._execute_task(task)
        
        task.state = TaskState.COMPLETED
    
    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a task with retry logic."""
        for attempt in range(task.max_retries + 1):
            start = asyncio.get_event_loop().time()
            
            try:
                await task.func()
                duration_ms = (asyncio.get_event_loop().time() - start) * 1000
                task.stats.record_success(duration_ms)
                
                logger.debug(
                    "Task completed",
                    task=task.name,
                    duration_ms=round(duration_ms, 2),
                )
                return
                
            except asyncio.CancelledError:
                raise  # Don't retry cancelled tasks
                
            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)[:100]}"
                task.stats.record_failure(error_msg)
                
                if attempt < task.max_retries:
                    logger.warning(
                        "Task failed, retrying",
                        task=task.name,
                        attempt=attempt + 1,
                        max_retries=task.max_retries,
                        error=error_msg,
                    )
                    await asyncio.sleep(task.retry_delay_seconds * (attempt + 1))
                else:
                    logger.error(
                        "Task failed permanently",
                        task=task.name,
                        error=error_msg,
                    )
    
    def get_task(self, name: str) -> Optional[ScheduledTask]:
        """Get a task by name."""
        return self._tasks.get(name)
    
    def enable_task(self, name: str) -> bool:
        """Enable a task."""
        task = self._tasks.get(name)
        if task:
            task.enabled = True
            return True
        return False
    
    def disable_task(self, name: str) -> bool:
        """Disable a task."""
        task = self._tasks.get(name)
        if task:
            task.enabled = False
            return True
        return False
    
    async def run_now(self, name: str) -> bool:
        """Manually trigger a task to run."""
        task = self._tasks.get(name)
        if task:
            await self._execute_task(task)
            return True
        return False
    
    def status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "running": self._running,
            "task_count": len(self._tasks),
            "tasks": {
                name: {
                    "state": task.state.value,
                    "enabled": task.enabled,
                    "interval_seconds": task.interval_seconds,
                    "stats": {
                        "total_runs": task.stats.total_runs,
                        "successful_runs": task.stats.successful_runs,
                        "failed_runs": task.stats.failed_runs,
                        "last_run": task.stats.last_run.isoformat() if task.stats.last_run else None,
                        "last_error": task.stats.last_error,
                        "avg_duration_ms": round(task.stats.avg_duration_ms, 2),
                    },
                }
                for name, task in self._tasks.items()
            },
        }


# ── Global Scheduler Instance ────────────────────────────────


scheduler = BackgroundScheduler()


# ── Built-in Tasks ───────────────────────────────────────────


@scheduler.task(interval_seconds=300, run_immediately=False)  # Every 5 minutes
async def cleanup_old_alerts():
    """Clean up alerts older than retention period."""
    try:
        from app.database.mongodb import mongodb
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(days=7)
        result = await mongodb.db.alerts.delete_many({"created_at": {"$lt": cutoff}})
        
        if result.deleted_count > 0:
            logger.info("Cleaned up old alerts", count=result.deleted_count)
    except Exception as e:
        logger.warning("Alert cleanup failed", error=str(e))


@scheduler.task(interval_seconds=60, run_immediately=True)  # Every minute
async def collect_metrics():
    """Collect system metrics for monitoring."""
    try:
        import psutil
        
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        # Store metrics (can be extended to push to monitoring system)
        logger.debug(
            "Metrics collected",
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_available_mb=round(memory.available / 1024 / 1024, 1),
        )
    except ImportError:
        pass  # psutil not installed
    except Exception as e:
        logger.warning("Metrics collection failed", error=str(e))


@scheduler.task(interval_seconds=600, run_immediately=False)  # Every 10 minutes
async def check_gpu_memory():
    """Monitor GPU memory usage and warn if high."""
    try:
        import torch
        
        if not torch.cuda.is_available():
            return
        
        for i in range(torch.cuda.device_count()):
            allocated = torch.cuda.memory_allocated(i)
            reserved = torch.cuda.memory_reserved(i)
            
            # Get total memory safely
            try:
                props = torch.cuda.get_device_properties(i)
                total = props.total_memory
            except Exception:
                total = reserved * 2  # Estimate
            
            usage_percent = (allocated / total) * 100 if total > 0 else 0
            
            if usage_percent > 85:
                logger.warning(
                    "High GPU memory usage",
                    device=i,
                    usage_percent=round(usage_percent, 1),
                    allocated_mb=round(allocated / 1024 / 1024, 1),
                )
    except Exception as e:
        logger.debug("GPU memory check skipped", error=str(e))


@scheduler.task(interval_seconds=3600, run_immediately=False)  # Every hour
async def cleanup_upload_directory():
    """Clean up old uploaded files."""
    try:
        import os
        from pathlib import Path
        
        upload_dir = Path("data/uploads")
        if not upload_dir.exists():
            return
        
        cutoff = datetime.utcnow() - timedelta(days=1)
        
        for date_dir in upload_dir.iterdir():
            if date_dir.is_dir():
                try:
                    dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
                    if dir_date < cutoff:
                        import shutil
                        shutil.rmtree(date_dir)
                        logger.info("Cleaned up upload directory", dir=date_dir.name)
                except ValueError:
                    pass  # Invalid date format, skip
    except Exception as e:
        logger.warning("Upload cleanup failed", error=str(e))
