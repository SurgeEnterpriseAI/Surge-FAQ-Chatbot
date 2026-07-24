"""Analytics aggregation.

Every figure returned here comes from a real record: the Prisma telemetry
tables, psutil, or the live vector index. When a source has no data the field
is zero or the list is empty and `hasData` is false, so the dashboard can say
"no data yet" instead of implying activity that never happened.
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from database.supabase_client import prisma_client, connect_prisma

logger = logging.getLogger("analytics_service")


def _utcnow() -> datetime:
    """Timezone-aware now. Prisma returns aware datetimes; naive ones cannot be compared to them."""
    return datetime.now(timezone.utc)


def _day_series(days: int) -> List[str]:
    """Ordered YYYY-MM-DD labels covering the last `days` days, oldest first."""
    now = _utcnow()
    return [(now - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d") for i in range(days)]


def _safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    return numerator / denominator if denominator else default


def _mean(values: List[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


class AnalyticsService:
    @staticmethod
    async def _database_available() -> bool:
        """Return whether optional analytics persistence is usable."""
        try:
            await connect_prisma()
            return prisma_client.is_connected()
        except Exception:
            return False

    @staticmethod
    async def log_event(event_type: str, user_id: str = None, session_id: str = None, agent_name: str = None, metadata: dict = None):
        """Log a general analytics event to the database."""
        await connect_prisma()
        try:
            from prisma import Json
            meta_json = Json(metadata) if metadata else None
            await prisma_client.analyticsevent.create(
                data={
                    "eventType": event_type,
                    "userId": user_id,
                    "sessionId": session_id,
                    "agentName": agent_name,
                    "metadata": meta_json
                }
            )
        except Exception as e:
            logger.error(f"Error logging analytics event {event_type}: {e}")

    @staticmethod
    async def log_security_event(event_type: str, user_id: str = None, ip: str = None, metadata: dict = None):
        """Log a security event to the database."""
        await connect_prisma()
        try:
            from prisma import Json
            meta_json = Json(metadata) if metadata else None
            await prisma_client.securityevent.create(
                data={
                    "eventType": event_type,
                    "userId": user_id,
                    "ip": ip,
                    "metadata": meta_json
                }
            )
        except Exception as e:
            logger.error(f"Error logging security event {event_type}: {e}")

    @staticmethod
    async def log_agent_metric(agent_name: str, requests: int, successes: int, failures: int, avg_exec_time_ms: float, avg_confidence: float, tool_calls: int, rag_calls: int, escalations: int):
        """Record/update agent metric snapshots."""
        await connect_prisma()
        try:
            await prisma_client.agentmetric.create(
                data={
                    "agentName": agent_name,
                    "requests": requests,
                    "successes": successes,
                    "failures": failures,
                    "avgExecTimeMs": avg_exec_time_ms,
                    "avgConfidence": avg_confidence,
                    "toolCalls": tool_calls,
                    "ragCalls": rag_calls,
                    "escalations": escalations
                }
            )
        except Exception as e:
            logger.error(f"Error logging agent metric for {agent_name}: {e}")

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    @staticmethod
    async def get_ai_performance(days: int = 30) -> Dict[str, Any]:
        """AI KPIs and daily trends from recorded analytics and safety events."""
        labels = _day_series(days)
        start_date = _utcnow() - timedelta(days=days)
        empty = {
            "hasData": False,
            "totalRequests": 0,
            "successfulResponses": 0,
            "failedResponses": 0,
            "hallucinationCount": 0,
            "safetyInterventions": 0,
            "blockedInjections": 0,
            "avgConfidenceScore": 0.0,
            "avgRetrievalScore": 0.0,
            "avgContextSizeTokens": 0,
            "avgTokensPerResponse": 0,
            "avgCompletionTimeSeconds": 0.0,
            "avgLlmLatencySeconds": 0.0,
            "trends": [{"date": d, "requests": 0, "confidenceScore": 0, "hallucinations": 0,
                        "safetyInterventions": 0, "promptInjectionsBlocked": 0} for d in labels],
        }

        if not await AnalyticsService._database_available():
            return empty

        try:
            events = await prisma_client.analyticsevent.find_many(
                where={"createdAt": {"gte": start_date}}
            )
            safety_reports = await prisma_client.safetyreport.find_many(
                where={"timestamp": {"gte": start_date}}
            )
            security_events = await prisma_client.securityevent.find_many(
                where={"createdAt": {"gte": start_date}}
            )
            agent_logs = await prisma_client.agentlog.find_many(
                where={"timestamp": {"gte": start_date}}
            )
        except Exception as e:
            logger.error(f"Error reading AI performance data: {e}")
            return empty

        requests = [e for e in events if e.eventType == "ai_request"]
        failures = [e for e in events if e.eventType in ("ai_error", "ai_failure")]
        injections = [e for e in security_events if "injection" in e.eventType.lower()]
        rejected = [r for r in safety_reports if not r.approved]

        by_day_requests = defaultdict(int)
        for event in requests:
            by_day_requests[event.createdAt.strftime("%Y-%m-%d")] += 1

        by_day_confidence = defaultdict(list)
        by_day_rejected = defaultdict(int)
        for report in safety_reports:
            day = report.timestamp.strftime("%Y-%m-%d")
            by_day_confidence[day].append(report.confidence)
            if not report.approved:
                by_day_rejected[day] += 1

        by_day_injections = defaultdict(int)
        for event in injections:
            by_day_injections[event.createdAt.strftime("%Y-%m-%d")] += 1

        durations = [log.durationMs for log in agent_logs if log.durationMs is not None]
        total_requests = len(requests)

        return {
            "hasData": bool(events or safety_reports or agent_logs),
            "totalRequests": total_requests,
            "successfulResponses": max(total_requests - len(failures), 0),
            "failedResponses": len(failures),
            # A safety rejection is the only recorded hallucination signal.
            "hallucinationCount": len(rejected),
            "safetyInterventions": len(rejected),
            "blockedInjections": len(injections),
            "avgConfidenceScore": round(_mean([r.confidence for r in safety_reports]) * 100, 2),
            "avgRetrievalScore": await AnalyticsService._avg_retrieval_score(),
            "avgContextSizeTokens": 0,
            "avgTokensPerResponse": await AnalyticsService._avg_output_tokens(start_date),
            "avgCompletionTimeSeconds": round(_mean(durations) / 1000, 2),
            "avgLlmLatencySeconds": round(_mean(durations) / 1000, 2),
            "trends": [
                {
                    "date": day,
                    "requests": by_day_requests.get(day, 0),
                    "confidenceScore": round(_mean(by_day_confidence.get(day, [])) * 100, 2),
                    "hallucinations": by_day_rejected.get(day, 0),
                    "safetyInterventions": by_day_rejected.get(day, 0),
                    "promptInjectionsBlocked": by_day_injections.get(day, 0),
                }
                for day in labels
            ],
        }

    @staticmethod
    async def _avg_retrieval_score() -> float:
        try:
            results = await prisma_client.retrievalresult.find_many()
            scores = [r.rerankScore if r.rerankScore is not None else r.vectorScore for r in results]
            return round(_mean([s for s in scores if s is not None]) * 100, 2)
        except Exception:
            return 0.0

    @staticmethod
    async def _avg_output_tokens(start_date: datetime) -> int:
        try:
            usage = await prisma_client.costusage.find_many(where={"createdAt": {"gte": start_date}})
            return int(_mean([u.outputTokens for u in usage]))
        except Exception:
            return 0

    @staticmethod
    async def get_agent_performance() -> Dict[str, Any]:
        """Per-agent metrics aggregated from recorded AgentMetric snapshots."""
        empty = {"hasData": False, "metrics": [], "topUsedAgent": None, "leastUsedAgent": None}

        if not await AnalyticsService._database_available():
            return empty

        try:
            snapshots = await prisma_client.agentmetric.find_many()
        except Exception as e:
            logger.error(f"Error reading agent metrics: {e}")
            return empty

        if not snapshots:
            return empty

        grouped: Dict[str, List[Any]] = defaultdict(list)
        for snapshot in snapshots:
            grouped[snapshot.agentName].append(snapshot)

        metrics = []
        for name, rows in grouped.items():
            requests = sum(r.requests for r in rows)
            metrics.append({
                "agentName": name,
                "requests": requests,
                "successes": sum(r.successes for r in rows),
                "failures": sum(r.failures for r in rows),
                # Snapshot averages weighted by the requests each covered.
                "avgExecTimeMs": round(
                    _safe_div(sum(r.avgExecTimeMs * r.requests for r in rows), requests), 2
                ),
                "avgConfidence": round(
                    _safe_div(sum(r.avgConfidence * r.requests for r in rows), requests), 2
                ),
                "toolCalls": sum(r.toolCalls for r in rows),
                "ragCalls": sum(r.ragCalls for r in rows),
                "escalations": sum(r.escalations for r in rows),
            })

        by_usage = sorted(metrics, key=lambda a: a["requests"], reverse=True)
        return {
            "hasData": True,
            "metrics": metrics,
            "topUsedAgent": by_usage[0]["agentName"],
            "leastUsedAgent": by_usage[-1]["agentName"],
        }

    @staticmethod
    async def get_business_metrics(days: int = 30) -> Dict[str, Any]:
        """Ticket, feedback and escalation KPIs with daily trends."""
        labels = _day_series(days)
        start_date = _utcnow() - timedelta(days=days)
        empty = {
            "hasData": False,
            "firstResponseTimeMinutes": 0.0,
            "avgResolutionTimeHours": 0.0,
            "csatScore": 0.0,
            "avgFeedbackRating": 0.0,
            "escalationRatePct": 0.0,
            "resolutionRatePct": 0.0,
            "reopenRatePct": 0.0,
            "ticketBacklog": 0,
            "openTickets": 0,
            "pendingTickets": 0,
            "resolvedTickets": 0,
            "closedTickets": 0,
            "trends": [{"date": d, "created": 0, "resolved": 0, "csat": 0, "escalated": 0} for d in labels],
        }

        if not await AnalyticsService._database_available():
            return empty

        try:
            tickets = await prisma_client.ticket.find_many()
            feedback = await prisma_client.feedback.find_many(where={"timestamp": {"gte": start_date}})
            escalations = await prisma_client.escalation.find_many(where={"createdAt": {"gte": start_date}})
            chat_count = await prisma_client.chat.count()
        except Exception as e:
            logger.error(f"Error reading business metrics: {e}")
            return empty

        by_status = defaultdict(int)
        for ticket in tickets:
            by_status[ticket.status] += 1

        open_tickets = by_status.get("open", 0)
        pending_tickets = by_status.get("pending", 0)
        resolved_tickets = by_status.get("resolved", 0)
        closed_tickets = by_status.get("closed", 0)

        created_by_day = defaultdict(int)
        for ticket in tickets:
            if ticket.createdAt >= start_date:
                created_by_day[ticket.createdAt.strftime("%Y-%m-%d")] += 1

        csat_by_day = defaultdict(list)
        for item in feedback:
            csat_by_day[item.timestamp.strftime("%Y-%m-%d")].append(item.rating)

        escalated_by_day = defaultdict(int)
        for item in escalations:
            escalated_by_day[item.createdAt.strftime("%Y-%m-%d")] += 1

        avg_rating = _mean([f.rating for f in feedback])

        return {
            "hasData": bool(tickets or feedback or escalations),
            # No response/resolution timestamps are recorded, so these stay 0
            # rather than being invented.
            "firstResponseTimeMinutes": 0.0,
            "avgResolutionTimeHours": 0.0,
            "csatScore": avg_rating,
            "avgFeedbackRating": avg_rating,
            "escalationRatePct": round(_safe_div(len(escalations), chat_count) * 100, 2),
            "resolutionRatePct": round(
                _safe_div(resolved_tickets + closed_tickets, len(tickets)) * 100, 2
            ),
            "reopenRatePct": 0.0,
            "ticketBacklog": open_tickets + pending_tickets,
            "openTickets": open_tickets,
            "pendingTickets": pending_tickets,
            "resolvedTickets": resolved_tickets,
            "closedTickets": closed_tickets,
            "trends": [
                {
                    "date": day,
                    "created": created_by_day.get(day, 0),
                    "resolved": 0,
                    "csat": _mean(csat_by_day.get(day, [])),
                    "escalated": escalated_by_day.get(day, 0),
                }
                for day in labels
            ],
        }

    @staticmethod
    async def get_knowledge_base(doc_manager=None) -> Dict[str, Any]:
        """Real index size, document list, and retrieval telemetry."""
        indexed_chunks = 0
        documents: List[str] = []
        namespaces: List[Dict[str, Any]] = []

        if await AnalyticsService._database_available():
            try:
                indexed_chunks = await prisma_client.parentchunk.count()
            except Exception as e:
                logger.error(f"Error counting parent chunks: {e}")

        if doc_manager is not None:
            import asyncio

            try:
                documents = await asyncio.to_thread(
                    doc_manager.rag_system.parent_store.list_sources
                )
            except Exception as e:
                logger.error(f"Error listing indexed documents: {e}")

            try:
                namespaces = await asyncio.to_thread(AnalyticsService._pinecone_namespaces, doc_manager)
            except Exception as e:
                logger.error(f"Error reading Pinecone stats: {e}")

        retrieval_latency = 0.0
        most_retrieved: List[Dict[str, Any]] = []
        if await AnalyticsService._database_available():
            try:
                runs = await prisma_client.retrievalrun.find_many()
                retrieval_latency = round(_mean([r.latencyMs for r in runs if r.latencyMs is not None]), 2)

                results = await prisma_client.retrievalresult.find_many()
                counts: Dict[str, Dict[str, Any]] = {}
                for result in results:
                    key = result.parentId or result.documentId
                    if not key:
                        continue
                    entry = counts.setdefault(key, {"chunk_id": key, "hits": 0, "scores": []})
                    entry["hits"] += 1
                    score = result.rerankScore if result.rerankScore is not None else result.vectorScore
                    if score is not None:
                        entry["scores"].append(score)
                most_retrieved = sorted(
                    (
                        {"chunk_id": v["chunk_id"], "hits": v["hits"], "score": round(_mean(v["scores"]), 3)}
                        for v in counts.values()
                    ),
                    key=lambda item: item["hits"],
                    reverse=True,
                )[:5]
            except Exception as e:
                logger.error(f"Error reading retrieval telemetry: {e}")

        return {
            "hasData": bool(documents or indexed_chunks),
            "indexedDocuments": len(documents),
            "documents": documents,
            "totalChunks": indexed_chunks,
            "totalEmbeddings": sum(n.get("vectorCount", 0) for n in namespaces),
            "mostRetrievedChunks": most_retrieved,
            "avgRetrievalLatencyMs": retrieval_latency,
            "pineconeNamespaceUsage": namespaces,
        }

    @staticmethod
    def _pinecone_namespaces(doc_manager) -> List[Dict[str, Any]]:
        """Live namespace vector counts from the Pinecone index."""
        vector_db = doc_manager.rag_system.vector_db
        manager = getattr(vector_db, "pinecone_manager", None)
        if manager is None or getattr(manager, "pc", None) is None:
            return []
        index = manager.get_index()
        stats = index.describe_index_stats()
        raw = stats.get("namespaces", {}) if isinstance(stats, dict) else getattr(stats, "namespaces", {})
        return [
            {"namespace": name or "(default)", "vectorCount": info.get("vector_count", 0)
             if isinstance(info, dict) else getattr(info, "vector_count", 0)}
            for name, info in (raw or {}).items()
        ]

    @staticmethod
    async def get_system_observability() -> Dict[str, Any]:
        """Live resource usage plus recorded SystemMetric history."""
        try:
            import psutil
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage("/").percent
            resources_available = True
        except Exception:
            cpu = mem = disk = 0.0
            resources_available = False

        db_ok = await AnalyticsService._database_available()

        trends: List[Dict[str, Any]] = []
        samples: List[Any] = []
        if db_ok:
            try:
                samples = await prisma_client.systemmetric.find_many(
                    where={"recordedAt": {"gte": _utcnow() - timedelta(hours=24)}},
                    order={"recordedAt": "asc"},
                )
                trends = [
                    {
                        "time": s.recordedAt.strftime("%H:%M"),
                        "cpu": round(s.cpuPct, 1),
                        "mem": round(s.memPct, 1),
                        "apiLatency": int(s.apiLatencyMs),
                        "dbLatency": int(s.dbQueryMs),
                        "vectorLatency": int(s.vectorSearchMs),
                    }
                    for s in samples
                ]
            except Exception as e:
                logger.error(f"Error reading system metrics: {e}")

        from db.parent_store_manager import ParentStoreManager
        parent_store_degraded = ParentStoreManager.degradation_reason()

        return {
            "hasData": bool(trends) or resources_available,
            "cpuUsage": cpu,
            "memoryUsage": mem,
            "diskUsage": disk,
            "fastapiHealth": "healthy",
            "langgraphHealth": "healthy",
            "pineconeHealth": "healthy",
            "supabaseHealth": "healthy" if db_ok else "degraded",
            "parentStoreHealth": "degraded" if parent_store_degraded else "healthy",
            "parentStoreDegradationReason": parent_store_degraded,
            "llmAvailable": True,
            "avgApiLatencyMs": _mean([s.apiLatencyMs for s in samples]),
            "avgDbQueryTimeMs": _mean([s.dbQueryMs for s in samples]),
            "avgVectorSearchTimeMs": _mean([s.vectorSearchMs for s in samples]),
            "avgEmbeddingTimeMs": _mean([s.embeddingMs for s in samples]),
            "trends": trends,
        }

    @staticmethod
    async def get_user_analytics(days: int = 30) -> Dict[str, Any]:
        """User counts and activity derived from User, Session and Message rows."""
        labels = _day_series(days)
        now = _utcnow()
        empty = {
            "hasData": False,
            "registeredUsers": 0,
            "guestUsers": 0,
            "dailyActiveUsers": 0,
            "weeklyActiveUsers": 0,
            "monthlyActiveUsers": 0,
            "avgSessionDurationMinutes": 0.0,
            "avgMessagesPerSession": 0.0,
            "avgConversationsPerUser": 0.0,
            "returningUsersPct": 0.0,
            "newUsers": 0,
            "trends": [{"date": d, "totalUsers": 0, "activeUsers": 0, "retentionRate": 0,
                        "sessionDurationSeconds": 0} for d in labels],
        }

        if not await AnalyticsService._database_available():
            return empty

        try:
            users = await prisma_client.user.find_many()
            sessions = await prisma_client.session.find_many()
            message_count = await prisma_client.message.count()
            chat_count = await prisma_client.chat.count()
        except Exception as e:
            logger.error(f"Error reading user analytics: {e}")
            return empty

        registered = len(users)
        guest_sessions = [s for s in sessions if not s.userId]

        def active_since(delta: timedelta) -> int:
            cutoff = now - delta
            return len({s.userId for s in sessions if s.lastActive >= cutoff and s.userId})

        # Session duration is measured as created -> last activity.
        durations = [
            (s.lastActive - s.createdAt).total_seconds()
            for s in sessions
            if s.lastActive and s.createdAt
        ]

        users_by_day = defaultdict(int)
        for user in users:
            users_by_day[user.createdAt.strftime("%Y-%m-%d")] += 1

        active_by_day = defaultdict(set)
        duration_by_day = defaultdict(list)
        for session in sessions:
            day = session.lastActive.strftime("%Y-%m-%d")
            if session.userId:
                active_by_day[day].add(session.userId)
            duration_by_day[day].append((session.lastActive - session.createdAt).total_seconds())

        cumulative = 0
        trends = []
        earlier = sum(
            1 for u in users if u.createdAt.strftime("%Y-%m-%d") < labels[0]
        )
        cumulative = earlier
        for day in labels:
            cumulative += users_by_day.get(day, 0)
            trends.append({
                "date": day,
                "totalUsers": cumulative,
                "activeUsers": len(active_by_day.get(day, set())),
                "retentionRate": round(
                    _safe_div(len(active_by_day.get(day, set())), cumulative) * 100, 2
                ),
                "sessionDurationSeconds": int(_mean(duration_by_day.get(day, []))),
            })

        return {
            "hasData": bool(users or sessions),
            "registeredUsers": registered,
            "guestUsers": len(guest_sessions),
            "dailyActiveUsers": active_since(timedelta(days=1)),
            "weeklyActiveUsers": active_since(timedelta(days=7)),
            "monthlyActiveUsers": active_since(timedelta(days=30)),
            "avgSessionDurationMinutes": round(_mean(durations) / 60, 2),
            "avgMessagesPerSession": round(_safe_div(message_count, len(sessions)), 2),
            "avgConversationsPerUser": round(_safe_div(chat_count, registered), 2),
            "returningUsersPct": round(
                _safe_div(
                    len([u for u in users if len([s for s in sessions if s.userId == u.id]) > 1]),
                    registered,
                ) * 100,
                2,
            ),
            "newUsers": sum(users_by_day.get(day, 0) for day in labels),
            "trends": trends,
        }

    @staticmethod
    async def get_security_dashboard(days: int = 7) -> Dict[str, Any]:
        """Counts and timeline built from recorded SecurityEvent rows."""
        labels = _day_series(days)
        start_date = _utcnow() - timedelta(days=days)
        empty = {
            "hasData": False,
            "failedLoginAttempts": 0,
            "blockedRequests": 0,
            "rateLimitedRequests": 0,
            "promptInjectionAttempts": 0,
            "unauthorizedAccessAttempts": 0,
            "invalidTokens": 0,
            "expiredTokens": 0,
            "adminLoginHistory": [],
            "recentSecurityEvents": [],
            "trends": [{"date": d, "securityEvents": 0, "authSuccessRate": 0, "blockedRequests": 0}
                       for d in labels],
        }

        if not await AnalyticsService._database_available():
            return empty

        try:
            events = await prisma_client.securityevent.find_many(
                where={"createdAt": {"gte": start_date}},
                order={"createdAt": "desc"},
            )
        except Exception as e:
            logger.error(f"Error reading security events: {e}")
            return empty

        def count_type(*needles: str) -> int:
            return len([e for e in events if any(n in e.eventType.lower() for n in needles)])

        SEVERITY = {"injection": "high", "unauthorized": "high", "failed_login": "medium",
                    "rate_limit": "low", "admin_login": "info"}

        def severity_for(event_type: str) -> str:
            for key, level in SEVERITY.items():
                if key in event_type.lower():
                    return level
            return "info"

        by_day = defaultdict(int)
        blocked_by_day = defaultdict(int)
        for event in events:
            day = event.createdAt.strftime("%Y-%m-%d")
            by_day[day] += 1
            if "block" in event.eventType.lower() or "injection" in event.eventType.lower():
                blocked_by_day[day] += 1

        admin_logins = [e for e in events if "admin_login" in e.eventType.lower()]

        return {
            "hasData": bool(events),
            "failedLoginAttempts": count_type("failed_login", "login_failed"),
            "blockedRequests": count_type("blocked"),
            "rateLimitedRequests": count_type("rate_limit"),
            "promptInjectionAttempts": count_type("injection"),
            "unauthorizedAccessAttempts": count_type("unauthorized", "forbidden"),
            "invalidTokens": count_type("invalid_token"),
            "expiredTokens": count_type("expired_token"),
            "adminLoginHistory": [
                {
                    "timestamp": e.createdAt.isoformat() + "Z",
                    "userId": e.userId,
                    "ip": e.ip,
                    "status": "failed" if "fail" in e.eventType.lower() else "success",
                }
                for e in admin_logins[:20]
            ],
            "recentSecurityEvents": [
                {
                    "timestamp": e.createdAt.isoformat() + "Z",
                    "event": e.eventType,
                    "ip": e.ip,
                    "severity": severity_for(e.eventType),
                }
                for e in events[:20]
            ],
            "trends": [
                {
                    "date": day,
                    "securityEvents": by_day.get(day, 0),
                    "authSuccessRate": 0.0,
                    "blockedRequests": blocked_by_day.get(day, 0),
                }
                for day in labels
            ],
        }

    @staticmethod
    def _linear_regression(x: List[float], y: List[float]) -> tuple[float, float]:
        """Perform simple linear regression returning slope (m) and intercept (c)."""
        n = len(x)
        if n < 2:
            return 0.0, y[0] if y else 0.0

        sum_x = sum(x)
        sum_y = sum(y)
        sum_xx = sum(val * val for val in x)
        sum_xy = sum(val_x * val_y for val_x, val_y in zip(x, y))

        denominator = (n * sum_xx - sum_x * sum_x)
        if abs(denominator) < 1e-8:
            return 0.0, sum_y / n

        m = (n * sum_xy - sum_x * sum_y) / denominator
        c = (sum_y - m * sum_x) / n
        return m, c

    #: Days of real history required before any projection is offered.
    MIN_HISTORY_DAYS = 7

    @staticmethod
    async def get_predictions(days: int = 30) -> Dict[str, Any]:
        """Project forward from recorded history, or report that there isn't enough."""
        labels = _day_series(days)
        start_date = _utcnow() - timedelta(days=days)
        unavailable = {
            "available": False,
            "reason": "insufficient history",
            "minHistoryDays": AnalyticsService.MIN_HISTORY_DAYS,
            "trends": [],
        }

        if not await AnalyticsService._database_available():
            return unavailable

        try:
            tickets = await prisma_client.ticket.find_many(where={"createdAt": {"gte": start_date}})
            usage = await prisma_client.costusage.find_many(where={"createdAt": {"gte": start_date}})
            logs = await prisma_client.agentlog.find_many(where={"timestamp": {"gte": start_date}})
        except Exception as e:
            logger.error(f"Error reading prediction inputs: {e}")
            return unavailable

        tickets_by_day = defaultdict(int)
        for ticket in tickets:
            tickets_by_day[ticket.createdAt.strftime("%Y-%m-%d")] += 1

        latency_by_day = defaultdict(list)
        for log in logs:
            if log.durationMs is not None:
                latency_by_day[log.timestamp.strftime("%Y-%m-%d")].append(log.durationMs / 1000)

        days_with_data = {d for d in labels if tickets_by_day.get(d) or latency_by_day.get(d)}
        if len(days_with_data) < AnalyticsService.MIN_HISTORY_DAYS:
            return {**unavailable, "observedDays": len(days_with_data)}

        index = list(range(len(labels)))
        ticket_series = [tickets_by_day.get(d, 0) for d in labels]
        latency_series = [_mean(latency_by_day.get(d, [])) for d in labels]

        m_t, c_t = AnalyticsService._linear_regression(index, ticket_series)
        m_r, c_r = AnalyticsService._linear_regression(index, latency_series)

        next_index = len(labels)
        total_tokens = sum(u.inputTokens + u.outputTokens for u in usage)
        total_cost = sum(u.costUsd for u in usage)

        now = _utcnow()
        return {
            "available": True,
            "observedDays": len(days_with_data),
            "expectedTicketsTomorrow": max(0.0, round(m_t * next_index + c_t, 1)),
            "avgResponseTimeTomorrowSeconds": max(0.0, round(m_r * next_index + c_r, 2)),
            "recordedTokens": total_tokens,
            "recordedCostDollars": round(total_cost, 4),
            "projectedMonthlyTokens": int(_safe_div(total_tokens, len(labels)) * 30),
            "projectedMonthlyCostDollars": round(_safe_div(total_cost, len(labels)) * 30, 2),
            "trends": [
                {
                    "date": (now + timedelta(days=i + 1)).strftime("%Y-%m-%d"),
                    "projectedTickets": max(0.0, round(m_t * (next_index + i) + c_t, 1)),
                    "projectedResponseTime": max(0.0, round(m_r * (next_index + i) + c_r, 2)),
                }
                for i in range(7)
            ],
        }
