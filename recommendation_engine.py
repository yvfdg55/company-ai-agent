"""Explainable marketing recommendations for Company AI Agent.

The first layer is deliberately dependency-light and works with pandas records.
Optional advanced models can replace the heuristic scores after enough labeled
campaign data exists. No function sends messages or changes orders.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from typing import Any

import pandas as pd


def _frame(rows: Any) -> pd.DataFrame:
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    return pd.DataFrame(list(rows or []))


def rfm_segments(orders: Any, as_of: datetime | None = None) -> pd.DataFrame:
    df = _frame(orders)
    required = {"phone", "created_at", "amount"}
    if df.empty or not required.issubset(df.columns):
        return pd.DataFrame(columns=["phone", "recency_days", "frequency", "monetary", "segment"])
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df = df.dropna(subset=["created_at"])
    reference = pd.Timestamp(as_of or datetime.now(timezone.utc))
    grouped = df.groupby("phone").agg(
        last_purchase=("created_at", "max"),
        frequency=("phone", "size"),
        monetary=("amount", "sum"),
    ).reset_index()
    grouped["recency_days"] = (reference - grouped["last_purchase"]).dt.days.clip(lower=0)
    def segment(row):
        if row.monetary >= grouped.monetary.quantile(0.80) and row.recency_days <= 30:
            return "vip"
        if row.recency_days > 90:
            return "at_risk"
        if row.frequency <= 1 and row.recency_days <= 30:
            return "new"
        if row.monetary <= grouped.monetary.quantile(0.30):
            return "price_sensitive"
        return "loyal"
    grouped["segment"] = grouped.apply(segment, axis=1)
    return grouped[["phone", "recency_days", "frequency", "monetary", "segment"]].sort_values("monetary", ascending=False)


def association_rules(order_items: Any, min_support: float = 0.05, min_confidence: float = 0.20) -> pd.DataFrame:
    """Mine simple product pairs; replaceable by FP-Growth for large datasets."""
    df = _frame(order_items)
    if df.empty or not {"order_id", "product_name"}.issubset(df.columns):
        return pd.DataFrame(columns=["antecedent", "consequent", "support", "confidence", "lift"])
    baskets = [set(g["product_name"].dropna().astype(str)) for _, g in df.groupby("order_id")]
    baskets = [b for b in baskets if b]
    if not baskets:
        return pd.DataFrame()
    total = len(baskets)
    item_counts = Counter(item for basket in baskets for item in basket)
    pair_counts = Counter(tuple(sorted(pair)) for basket in baskets for pair in combinations(basket, 2))
    rows = []
    for (a, b), count in pair_counts.items():
        support = count / total
        if support < min_support:
            continue
        confidence_ab = count / item_counts[a]
        confidence_ba = count / item_counts[b]
        lift_ab = confidence_ab / (item_counts[b] / total)
        lift_ba = confidence_ba / (item_counts[a] / total)
        if confidence_ab >= min_confidence:
            rows.append({"antecedent": a, "consequent": b, "support": support, "confidence": confidence_ab, "lift": lift_ab})
        if confidence_ba >= min_confidence:
            rows.append({"antecedent": b, "consequent": a, "support": support, "confidence": confidence_ba, "lift": lift_ba})
    return pd.DataFrame(rows).sort_values(["lift", "confidence"], ascending=False) if rows else pd.DataFrame()


def content_recommendations(customer_events: Any, products: Any, phone: str, limit: int = 5) -> pd.DataFrame:
    events = _frame(customer_events)
    catalog = _frame(products)
    if events.empty or catalog.empty or "product_name" not in events or "Product Name" not in catalog:
        return pd.DataFrame()
    viewed = set(events.loc[(events.phone == phone) & events.event_type.isin(["product_view", "order_created"]), "product_name"].dropna().astype(str))
    if not viewed:
        return catalog.head(limit).copy()
    scored = catalog.copy()
    scored["score"] = scored["Product Name"].astype(str).apply(lambda p: 0.2 if p in viewed else 0.8)
    scored["reason"] = scored["Product Name"].astype(str).apply(lambda p: "مكمل محتمل للمنتجات التي تفاعل معها العميل" if p not in viewed else "تم استبعاده لأنه شاهده أو اشتراه بالفعل")
    return scored[scored["score"] > 0.2].sort_values("score", ascending=False).head(limit)


def purchase_propensity(rfm: pd.DataFrame) -> pd.DataFrame:
    """Transparent baseline score; upgrade to CatBoost/LightGBM with labels later."""
    if rfm.empty:
        return pd.DataFrame()
    out = rfm.copy()
    out["purchase_probability"] = (0.45 * (1 - out.recency_days.clip(0, 180) / 180) + 0.30 * (out.frequency.clip(0, 10) / 10) + 0.25 * (out.monetary / max(float(out.monetary.max()), 1))).clip(0, 1).round(3)
    out["confidence"] = (0.50 + 0.50 * (out.frequency / max(float(out.frequency.max()), 1))).clip(0, 1).round(3)
    return out.sort_values("purchase_probability", ascending=False)


def churn_risk(rfm: pd.DataFrame) -> pd.DataFrame:
    if rfm.empty:
        return pd.DataFrame()
    out = rfm.copy()
    out["churn_risk"] = ((out.recency_days.clip(0, 180) / 180) * 0.70 + (1 - out.frequency.clip(0, 10) / 10) * 0.30).clip(0, 1).round(3)
    out["risk_label"] = out["churn_risk"].map(lambda x: "high" if x >= .65 else "medium" if x >= .35 else "low")
    return out.sort_values("churn_risk", ascending=False)


def marketing_recommendations(rfm: pd.DataFrame, propensity: pd.DataFrame | None = None, churn: pd.DataFrame | None = None, rules: pd.DataFrame | None = None) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for _, row in rfm.iterrows():
        if row.segment == "vip":
            actions.append({"phone": row.phone, "priority": "high", "action": "عرض ولاء مخصص", "reason": "عميل عالي القيمة وحديث الشراء", "confidence": .86, "approval_required": True})
        elif row.segment == "at_risk":
            actions.append({"phone": row.phone, "priority": "high", "action": "حملة استعادة هادئة", "reason": f"مرّ {int(row.recency_days)} يومًا منذ آخر شراء", "confidence": .78, "approval_required": True})
        elif row.segment == "price_sensitive":
            actions.append({"phone": row.phone, "priority": "medium", "action": "اقتراح باقة اقتصادية", "reason": "متوسط قيمة المشتريات منخفض نسبيًا", "confidence": .67, "approval_required": True})
    if rules is not None and not rules.empty:
        best = rules.iloc[0]
        actions.append({"phone": "segment", "priority": "medium", "action": f"اقترح {best.consequent} مع {best.antecedent}", "reason": f"lift={best.lift:.2f}, confidence={best.confidence:.2f}", "confidence": float(min(best.confidence, 1)), "approval_required": True})
    return actions


def recommendation_report(orders: Any, order_items: Any, customer_events: Any = None, products: Any = None) -> dict[str, Any]:
    rfm = rfm_segments(orders)
    propensity = purchase_propensity(rfm)
    churn = churn_risk(rfm)
    rules = association_rules(order_items)
    actions = marketing_recommendations(rfm, propensity, churn, rules)
    return {"rfm": rfm, "propensity": propensity, "churn": churn, "association_rules": rules, "actions": actions, "model_stage": "explainable_baseline"}
