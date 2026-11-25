"""Optional MySQL analytics for Company AI Agent.

The agent can continue using SQLite locally. Configure MYSQL_* environment
variables and call initialize_mysql_schema() only when a central MySQL
analytics store is desired.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "database": os.getenv("MYSQL_DATABASE", "company_agent"),
    "user": os.getenv("MYSQL_USER", "company_agent"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
}

MYSQL_SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    phone VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NULL,
    city VARCHAR(120) NULL,
    country VARCHAR(120) NULL,
    source VARCHAR(80) NULL,
    first_seen DATETIME NOT NULL,
    last_seen DATETIME NOT NULL,
    message_count INT NOT NULL DEFAULT 0,
    INDEX idx_customers_city (city),
    INDEX idx_customers_last_seen (last_seen)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS customer_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    phone VARCHAR(64) NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    event_value DECIMAL(12,2) NULL,
    product_name VARCHAR(255) NULL,
    city VARCHAR(120) NULL,
    metadata JSON NULL,
    created_at DATETIME NOT NULL,
    INDEX idx_events_phone (phone),
    INDEX idx_events_type_date (event_type, created_at),
    CONSTRAINT fk_events_customer FOREIGN KEY (phone) REFERENCES customers(phone)
        ON DELETE CASCADE
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS orders (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    phone VARCHAR(64) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'pending_review',
    amount DECIMAL(12,2) NULL,
    details TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    INDEX idx_orders_status_date (status, created_at),
    CONSTRAINT fk_orders_customer FOREIGN KEY (phone) REFERENCES customers(phone)
        ON DELETE CASCADE
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS tickets (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    phone VARCHAR(64) NOT NULL,
    status VARCHAR(40) NOT NULL DEFAULT 'open',
    subject VARCHAR(255) NOT NULL,
    details TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    INDEX idx_tickets_status_date (status, created_at),
    CONSTRAINT fk_tickets_customer FOREIGN KEY (phone) REFERENCES customers(phone)
        ON DELETE CASCADE
) ENGINE=InnoDB;
"""


def _connector():
    try:
        import mysql.connector
    except ImportError as exc:
        raise RuntimeError(
            "mysql-connector-python is required for MySQL analytics. "
            "Install it with: pip install mysql-connector-python"
        ) from exc
    return mysql.connector


@contextmanager
def mysql_connection(config: dict[str, Any] | None = None) -> Iterator[Any]:
    """Open a MySQL connection without logging or exposing the password."""
    connector = _connector()
    settings = dict(MYSQL_CONFIG)
    settings.update(config or {})
    conn = connector.connect(**settings)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_mysql_schema(config: dict[str, Any] | None = None) -> None:
    """Create the analytics tables. Safe to run repeatedly."""
    with mysql_connection(config) as conn:
        cursor = conn.cursor()
        for statement in MYSQL_SCHEMA.split(";"):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)
        cursor.close()


def mysql_health_check(config: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        with mysql_connection(config) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
        return {"ok": True, "message": "MySQL connection is healthy"}
    except Exception as exc:
        return {"ok": False, "message": str(exc)}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def upsert_customer(phone: str, name: str = "", city: str = "", country: str = "", source: str = "whatsapp", config: dict[str, Any] | None = None) -> None:
    now = _now()
    with mysql_connection(config) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO customers
            (phone, name, city, country, source, first_seen, last_seen, message_count)
            VALUES (%s,%s,%s,%s,%s,%s,%s,1)
            ON DUPLICATE KEY UPDATE
              name=COALESCE(NULLIF(VALUES(name),''), name),
              city=COALESCE(NULLIF(VALUES(city),''), city),
              country=COALESCE(NULLIF(VALUES(country),''), country),
              last_seen=VALUES(last_seen), message_count=message_count+1""",
            (phone, name, city, country, source, now, now),
        )
        cursor.close()


def record_event(phone: str, event_type: str, event_value: float | None = None, metadata: dict[str, Any] | None = None, product_name: str | None = None, city: str | None = None, config: dict[str, Any] | None = None) -> None:
    with mysql_connection(config) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO customer_events (phone,event_type,event_value,product_name,city,metadata,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (phone, event_type, event_value, product_name, city, json.dumps(metadata or {}, ensure_ascii=False), _now()),
        )
        cursor.close()


def analytics_snapshot(days: int = 30, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return explainable KPIs for customers, places, conversion and support."""
    with mysql_connection(config) as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) AS total_customers, COUNT(DISTINCT NULLIF(city,'')) AS places, COALESCE(SUM(message_count),0) AS messages FROM customers")
        overview = cursor.fetchone()
        cursor.execute("SELECT COALESCE(NULLIF(city,''),'غير محدد') AS place, COUNT(*) AS customers FROM customers GROUP BY COALESCE(NULLIF(city,''),'غير محدد') ORDER BY customers DESC LIMIT 20")
        by_place = cursor.fetchall()
        cursor.execute("SELECT status, COUNT(*) AS total, COALESCE(SUM(amount),0) AS value FROM orders WHERE created_at >= (NOW() - INTERVAL %s DAY) GROUP BY status", (days,))
        orders = cursor.fetchall()
        cursor.execute("SELECT status, COUNT(*) AS total FROM tickets WHERE created_at >= (NOW() - INTERVAL %s DAY) GROUP BY status", (days,))
        tickets = cursor.fetchall()
        cursor.execute("SELECT event_type, COUNT(*) AS total, COALESCE(SUM(event_value),0) AS value FROM customer_events WHERE created_at >= (NOW() - INTERVAL %s DAY) GROUP BY event_type ORDER BY total DESC", (days,))
        events = cursor.fetchall()
        cursor.execute("SELECT COALESCE(NULLIF(product_name,''),'غير محدد') AS product, COUNT(*) AS events, COALESCE(SUM(event_value),0) AS value FROM customer_events WHERE created_at >= (NOW() - INTERVAL %s DAY) GROUP BY COALESCE(NULLIF(product_name,''),'غير محدد') ORDER BY events DESC LIMIT 30", (days,))
        products = cursor.fetchall()
        cursor.execute("SELECT DATE(created_at) AS day, HOUR(created_at) AS hour, COUNT(*) AS events FROM customer_events WHERE created_at >= (NOW() - INTERVAL %s DAY) GROUP BY DATE(created_at), HOUR(created_at) ORDER BY day DESC, hour", (days,))
        time = cursor.fetchall()
        cursor.close()
    return {"days": days, "overview": overview, "by_place": by_place, "orders": orders, "tickets": tickets, "events": events, "products": products, "time": time}


def recommend_actions(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    """Generate deterministic, auditable business actions from the snapshot."""
    recommendations: list[dict[str, str]] = []
    overview = snapshot.get("overview") or {}
    tickets = {str(row.get("status")): int(row.get("total", 0)) for row in snapshot.get("tickets", [])}
    orders = {str(row.get("status")): int(row.get("total", 0)) for row in snapshot.get("orders", [])}
    events = {str(row.get("event_type")): int(row.get("total", 0)) for row in snapshot.get("events", [])}
    total_customers = int(overview.get("total_customers", 0) or 0)

    if tickets.get("open", 0) >= 10:
        recommendations.append({"priority": "high", "action": "تخصيص موظف دعم إضافي", "reason": f"يوجد {tickets['open']} تذكرة مفتوحة خلال الفترة."})
    if orders.get("pending_review", 0) >= 5:
        recommendations.append({"priority": "high", "action": "مراجعة الطلبات المعلقة اليوم", "reason": f"هناك {orders['pending_review']} طلبات تحتاج مراجعة بشرية."})
    if events.get("product_view", 0) > 0 and events.get("order_created", 0) == 0:
        recommendations.append({"priority": "medium", "action": "متابعة العملاء المهتمين بالمنتجات", "reason": "تم تسجيل مشاهدات منتجات دون طلبات مؤكدة."})
    if total_customers and int(overview.get("messages", 0) or 0) / total_customers >= 8:
        recommendations.append({"priority": "medium", "action": "إعداد ردود تلقائية للأسئلة المتكررة", "reason": "متوسط التفاعل لكل عميل مرتفع ويستحق أتمتة الأسئلة المتكررة."})
    if not recommendations:
        recommendations.append({"priority": "low", "action": "الاستمرار في جمع البيانات", "reason": "لا توجد عتبات حرجة حاليًا؛ راقب الاتجاهات قبل اتخاذ إجراء."})
    return recommendations
