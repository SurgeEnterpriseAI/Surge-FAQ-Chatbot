"""Periodic system metric sampling.

Every value written here is measured: resource usage comes from psutil, database
latency from timing a real query, and API/vector latency from durations recorded
by the request middleware and the retrieval tool. A source with no samples in
the interval records 0.0 rather than a plausible-looking number.
"""
import asyncio
import logging
import threading
import time
from collections import defaultdict, deque
from database.supabase_client import prisma_client, connect_prisma

logger = logging.getLogger("metrics_collector")


class LatencyTracker:
    """Thread-safe ring buffers of observed latencies, in milliseconds."""

    def __init__(self, maxlen: int = 500):
        self._samples = defaultdict(lambda: deque(maxlen=maxlen))
        self._lock = threading.Lock()

    def record(self, bucket: str, duration_ms: float) -> None:
        with self._lock:
            self._samples[bucket].append(float(duration_ms))

    def drain_mean(self, bucket: str) -> float:
        """Mean of the samples seen since the last drain; 0.0 if none."""
        with self._lock:
            samples = self._samples.get(bucket)
            if not samples:
                return 0.0
            mean = sum(samples) / len(samples)
            samples.clear()
            return round(mean, 1)


latency_tracker = LatencyTracker()


class MetricsCollector:
    def __init__(self):
        self._task = None
        self._running = False
        self._last_db_latency_ms = 0.0

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._collect_loop())
            logger.info("Metrics collector background task started.")

    def stop(self):
        if self._running:
            self._running = False
            if self._task:
                self._task.cancel()
            logger.info("Metrics collector background task stopped.")

    async def _collect_loop(self):
        while self._running:
            try:
                await connect_prisma()

                try:
                    import psutil
                    cpu = psutil.cpu_percent()
                    mem = psutil.virtual_memory().percent
                    disk = psutil.disk_usage("/").percent
                except Exception as e:
                    logger.warning(f"psutil unavailable, skipping this sample: {e}")
                    await asyncio.sleep(30)
                    continue

                # The previous cycle's write is the timed round trip, so each
                # cycle costs exactly one query and still reports a measured
                # latency rather than an assumed one.
                started = time.perf_counter()
                await prisma_client.systemmetric.create(
                    data={
                        "cpuPct": cpu,
                        "memPct": mem,
                        "diskPct": disk,
                        "apiLatencyMs": latency_tracker.drain_mean("api"),
                        "dbQueryMs": self._last_db_latency_ms,
                        "vectorSearchMs": latency_tracker.drain_mean("vector"),
                        "embeddingMs": latency_tracker.drain_mean("embedding"),
                    }
                )
                self._last_db_latency_ms = round((time.perf_counter() - started) * 1000, 1)

                # Cleanup older records (e.g. keep only last 48 hours to avoid db bloat)
                try:
                    from datetime import datetime, timedelta
                    cutoff = datetime.utcnow() - timedelta(days=2)
                    await prisma_client.systemmetric.delete_many(
                        where={"recordedAt": {"lt": cutoff}}
                    )
                except Exception as clean_ex:
                    logger.warning(f"Error cleaning old metrics: {clean_ex}")

            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")

            await asyncio.sleep(30)


metrics_collector = MetricsCollector()
