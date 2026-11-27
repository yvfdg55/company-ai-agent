"""Management AI agent for Company AI Agent.

This module reuses the existing analytics and recommendation layers and gives
management a read-only interface for KPIs, customer analysis, sales analysis,
and human-reviewed recommendations. It never sends campaigns, edits orders,
changes prices, or changes inventory.
"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests

from recommendation_engine import recommendation_report

try:
    from mysql_analytics import (
        analytics_snapshot,
        mysql_health_check,
        recommend_actions,
    )
except Exception:  # Optional dependency/runtime connection
    analytics_snapshot = None
    mysql_health_check = None
    recommend_actions = None


@dataclass
class ManagementConfig:
    provider: str = os.getenv("MANAGEMENT_DATA_PROVIDER", "mysql")
    database: str = os.getenv("DATABASE", "company_agent.db")
    ollama_url: str = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("MANAGEMENT_OLLAMA_MODEL", os.getenv("OLLAMA_MODEL", "qwen3:8b"))
    mysql_config: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.mysql_config is None:
            self.mysql_config = {
                "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
                "port": int(os.getenv("MYSQL_PORT", "3306")),
                "database": os.getenv("MYSQL_DATABASE", "company_agent"),
                "user": os.getenv("MYSQL_USER", "company_agent"),
                "password": os.getenv("MYSQL_PASSWORD", ""),
                "time_zone": "+00:00",
            }


class ManagementDataProvider:
    """Read-only data access for the management agent."""

    def __init__(self, config: ManagementConfig | None = None):
        self.config = config or ManagementConfig()

    def health(self) -> dict[str, Any]:
        provider = self.config.provider.casefold()
        if provider == "mysql":
            if mysql_health_check is None:
                return {"ok": False, "provider": "mysql", "message": "MySQL connector/module unavailable"}
            result = mysql_health_check(self.config.mysql_config)
            return {"provider": "mysql", **result}
        if provider == "sqlite":
            try:
                with sqlite3.connect(self.config.database) as conn:
                    conn.execute("SELECT 1").fetchone()
                return {"ok": True, "provider": "sqlite", "message": "SQLite connection is healthy"}
            except Exception as exc:
                return {"ok": False, "provider": "sqlite", "message": str(exc)}
        return {"ok": False, "provider": provider, "message": "Unsupported data provider"}

    def snapshot(self, days: int = 30) -> dict[str, Any]:
        """Return a normalized management snapshot."""
        if days < 1 or days > 3650:
            raise ValueError("days must be between 1 and 3650")
        provider = self.config.provider.casefold()
        if provider == "mysql":
            if analytics_snapshot is None:
                raise RuntimeError("MySQL analytics is unavailable")
            return analytics_snapshot(days, self.config.mysql_config)
        if provider == "sqlite":
            return self._sqlite_snapshot(days)
        raise ValueError("provider must be mysql or sqlite")

    def _sqlite_snapshot(self, days: int) -> dict[str, Any]:
        cutoff = f"-{int(days)} days"
        with sqlite3.connect(self.config.database) as conn:
            conn.row_factory = sqlite3.Row
            overview = conn.execute(
                """SELECT COUNT(*) AS total_customers,
                          COALESCE((SELECT COUNT(*) FROM messages WHERE role='user' AND created_at >= datetime('now', ?)), 0) AS messages
                   FROM customers""",
                (cutoff,),
            ).fetchone()
            orders = conn.execute(
                """SELECT status, COUNT(*) AS total, 0.0 AS value
                   FROM orders WHERE created_at >= datetime('now', ?) GROUP BY status""",
                (cutoff,),
            ).fetchall()
            tickets = conn.execute(
                """SELECT status, COUNT(*) AS total
                   FROM tickets WHERE created_at >= datetime('now', ?) GROUP BY status""",
                (cutoff,),
            ).fetchall()
            recent_customers = conn.execute(
                """SELECT phone, COUNT(*) AS messages
                   FROM messages WHERE role='user' AND created_at >= datetime('now', ?)
                   GROUP BY phone ORDER BY messages DESC LIMIT 20""",
                (cutoff,),
            ).fetchall()
        return {
            "days": days,
            "overview": dict(overview) if overview else {},
            "orders": [dict(row) for row in orders],
            "tickets": [dict(row) for row in tickets],
            "top_customers": [dict(row) for row in recent_customers],
            "by_place": [],
            "events": [],
            "products": [],
            "time": [],
            "monthly_sales": [],
            "sales_by_place": [],
        }

    def recommendation_report(self, orders: Any, order_items: Any, customer_events: Any = None, products: Any = None) -> dict[str, Any]:
        """Run the existing explainable recommendation engine."""
        return recommendation_report(orders, order_items, customer_events, products)

    def operational_recommendations(self, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        if recommend_actions is not None and self.config.provider.casefold() == "mysql":
            return recommend_actions(snapshot)
        return self._fallback_recommendations(snapshot)

    @staticmethod
    def _fallback_recommendations(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        overview = snapshot.get("overview") or {}
        tickets = {str(row.get("status")): int(row.get("total", 0)) for row in snapshot.get("tickets", [])}
        orders = {str(row.get("status")): int(row.get("total", 0)) for row in snapshot.get("orders", [])}
        actions: list[dict[str, Any]] = []
        if tickets.get("open", 0) >= 10:
            actions.append({"priority": "high", "action": "مراجعة ضغط الدعم وتخصيص موارد إضافية", "reason": "عدد التذاكر المفتوحة مرتفع", "approval_required": True})
        if orders.get("pending_review", 0) >= 5:
            actions.append({"priority": "high", "action": "مراجعة الطلبات المعلقة", "reason": "توجد طلبات تحتاج موافقة بشرية", "approval_required": True})
        if int(overview.get("messages", 0) or 0) > 0:
            actions.append({"priority": "low", "action": "مواصلة جمع البيانات قبل تغيير السياسات", "reason": "التوصية مبنية على بيانات تفاعل محدودة", "approval_required": True})
        return actions or [{"priority": "low", "action": "الاستمرار في المراقبة", "reason": "لا توجد عتبات حرجة حاليًا", "approval_required": True}]


class ManagementAgent:
    """Read-only management assistant with deterministic analytics grounding."""

    SYSTEM_PROMPT = """أنت وكيل إدارة وتحليل داخلي.
- استخدم البيانات والأرقام التي يزودك بها النظام فقط.
- اذكر الفترة الزمنية ومصدر البيانات عند الإمكان.
- ميّز بوضوح بين الحقيقة والتوصية.
- لا تنفذ أو تدّعي تنفيذ إرسال حملات أو تعديل أسعار أو مخزون أو طلبات.
- كل توصية تحتاج موافقة بشرية.
- أجب بالعربية إذا كان السؤال بالعربية وبالإنجليزية إذا كان بالإنجليزية.
"""

    def __init__(self, provider: ManagementDataProvider | None = None):
        self.provider = provider or ManagementDataProvider()

    def analyze(self, days: int = 30) -> dict[str, Any]:
        snapshot = self.provider.snapshot(days)
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "days": days,
            "provider": self.provider.config.provider,
            "snapshot": snapshot,
            "recommendations": self.provider.operational_recommendations(snapshot),
        }

    def answer(self, question: str, days: int = 30, use_llm: bool = True) -> str:
        question = str(question or "").strip()
        if not question:
            return "اكتب سؤالًا إداريًا مثل: ما إجمالي العملاء أو ما التوصيات؟"
        report = self.analyze(days)
        deterministic = self._deterministic_answer(question, report)
        if not use_llm:
            return deterministic
        try:
            return self._llm_answer(question, report)
        except Exception:
            return deterministic

    @staticmethod
    def _deterministic_answer(question: str, report: dict[str, Any]) -> str:
        snapshot = report["snapshot"]
        overview = snapshot.get("overview") or {}
        low = question.casefold()
        if any(x in question for x in ["عدد العملاء", "كم عميل"]) or "customer" in low:
            return f"عدد العملاء: {overview.get('total_customers', 0)}. الفترة: آخر {report['days']} يومًا."
        if any(x in question for x in ["اقتراح", "اقتراحات", "توصية", "توصيات", "إجراء", "إجراءات"]) or any(x in low for x in ["recommend", "action"]):
            rows = report["recommendations"]
            return "التوصيات المقترحة للمراجعة البشرية:\n" + "\n".join(
                f"- [{r.get('priority', 'medium')}] {r.get('action')}: {r.get('reason')}" for r in rows
            )
        if any(x in question for x in ["مبيعات", "المبيعات", "sales"]):
            rows = snapshot.get("monthly_sales", [])
            if rows:
                return "المبيعات حسب الشهر:\n" + "\n".join(f"- {r.get('month')}: {r.get('sales')} من {r.get('orders')} طلبات" for r in rows)
            return "لا توجد بيانات مبيعات شهرية متاحة في مصدر البيانات الحالي."
        if any(x in question for x in ["طلبات", "الطلبات", "orders"]):
            rows = snapshot.get("orders", [])
            return "حالة الطلبات:\n" + "\n".join(f"- {r.get('status')}: {r.get('total')}" for r in rows) if rows else "لا توجد بيانات طلبات متاحة."
        return "تم إعداد التحليل. اسأل عن عدد العملاء، المبيعات، الطلبات، التذاكر، أو التوصيات."

    def _llm_answer(self, question: str, report: dict[str, Any]) -> str:
        payload = {
            "model": self.provider.config.ollama_model,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 700},
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps({"question": question, "report": report}, ensure_ascii=False, default=str)},
            ],
        }
        response = requests.post(self.provider.config.ollama_url.rstrip("/") + "/api/chat", json=payload, timeout=90)
        response.raise_for_status()
        content = response.json().get("message", {}).get("content", "").strip()
        if not content:
            raise RuntimeError("Empty management model response")
        return content


__all__ = ["ManagementConfig", "ManagementDataProvider", "ManagementAgent"]
