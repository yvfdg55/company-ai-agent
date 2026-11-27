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
    # Only completed revenue belongs in RFM; drafts/cancelled orders must not
    # inflate customer value or make a customer look active.
    if "status" in df.columns:
        completed = {"paid", "completed", "delivered", "fulfilled", "closed"}
        df = df[df["status"].astype(str).str.casefold().isin(completed)]
    if df.empty:
        return pd.DataFrame(columns=["phone", "recency_days", "frequency", "monetary", "segment"])
    reference = pd.Timestamp(as_of or datetime.now(timezone.utc))
    if reference.tzinfo is None:
        reference = reference.tz_localize("UTC")
    else:
        reference = reference.tz_convert("UTC")
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
    customer_events = events[(events.get("phone", pd.Series(dtype=str)).astype(str) == str(phone))]
    interacted = customer_events[customer_events.get("event_type", pd.Series(dtype=str)).isin(["product_view", "order_created"])]
    viewed = set(interacted.get("product_name", pd.Series(dtype=str)).dropna().astype(str))
    candidates = catalog[~catalog["Product Name"].astype(str).isin(viewed)].copy()
    if candidates.empty:
        return pd.DataFrame(columns=[*catalog.columns, "score", "reason"])
    # Lightweight content similarity: match category/tags when available, and
    # otherwise use a neutral baseline. This is deterministic and transparent.
    interacted_rows = catalog[catalog["Product Name"].astype(str).isin(viewed)]
    categories = set(interacted_rows.get("Category", pd.Series(dtype=str)).dropna().astype(str))
    if "Category" in candidates.columns and categories:
        candidates["score"] = candidates["Category"].astype(str).isin(categories).map({True: 0.9, False: 0.4})
        candidates["reason"] = candidates["Category"].astype(str).apply(
            lambda c: "ينتمي إلى فئة تفاعل معها العميل سابقًا" if c in categories else "منتج جديد مقترح للمقارنة"
        )
    else:
        candidates["score"] = 0.5
        candidates["reason"] = "منتج غير متفاعل معه سابقًا، مقترح للمقارنة"
    return candidates.sort_values("score", ascending=False).head(limit)


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
    propensity_by_phone = {} if propensity is None or propensity.empty else propensity.set_index("phone").to_dict("index")
    churn_by_phone = {} if churn is None or churn.empty else churn.set_index("phone").to_dict("index")
    for _, row in rfm.iterrows():
        phone = row.phone
        prop = propensity_by_phone.get(phone, {}).get("purchase_probability")
        risk = churn_by_phone.get(phone, {}).get("churn_risk")
        if row.segment == "vip":
            actions.append({"phone": phone, "priority": "high", "action": "عرض ولاء مخصص", "reason": "عميل عالي القيمة وحديث الشراء", "confidence": .86, "purchase_probability": prop, "churn_risk": risk, "approval_required": True})
        elif row.segment == "at_risk":
            actions.append({"phone": phone, "priority": "high", "action": "حملة استعادة هادئة", "reason": f"مرّ {int(row.recency_days)} يومًا منذ آخر شراء", "confidence": .78, "purchase_probability": prop, "churn_risk": risk, "approval_required": True})
        elif row.segment == "price_sensitive":
            actions.append({"phone": phone, "priority": "medium", "action": "اقتراح باقة اقتصادية", "reason": "متوسط قيمة المشتريات منخفض نسبيًا", "confidence": .67, "purchase_probability": prop, "churn_risk": risk, "approval_required": True})
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
    content = pd.DataFrame()
    if customer_events is not None and products is not None and not rfm.empty:
        content_parts = [content_recommendations(customer_events, products, phone)
                         for phone in rfm["phone"].astype(str)]
        content = pd.concat(content_parts, ignore_index=True) if content_parts else pd.DataFrame()
    return {"rfm": rfm, "propensity": propensity, "churn": churn, "association_rules": rules, "content_recommendations": content, "actions": actions, "model_stage": "explainable_baseline"}
