"""Dependency-light hybrid search helpers for Arabic and English text."""
from __future__ import annotations
import math
import re
from collections import Counter
from typing import Any, Iterable

_ARABIC_DIACRITICS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
_NON_WORD = re.compile(r"[^\w\u0600-\u06ff]+", re.UNICODE)
_ARABIC_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ؤ": "و", "ئ": "ي", "ة": "ه"})


def normalize_text(value: Any) -> str:
    text = str(value or "").casefold().translate(_ARABIC_MAP)
    text = _ARABIC_DIACRITICS.sub("", text)
    return _NON_WORD.sub(" ", text).strip()


def tokenize(value: Any) -> list[str]:
    tokens = []
    for token in normalize_text(value).split():
        # Lightweight Arabic normalization: treat the definite article as a stop prefix.
        if token.startswith("ال") and len(token) > 3:
            token = token[2:]
        if len(token) > 1:
            tokens.append(token)
    return tokens


def _row_text(row: Any) -> str:
    if hasattr(row, "searchable_text"):
        return str(row.searchable_text())
    if isinstance(row, dict):
        return " ".join(f"{key} {value}" for key, value in row.items())
    return str(row)


def rank_records(records: Iterable[Any], query: str, limit: int = 20) -> list[Any]:
    """Rank lexical matches using exact phrase, token overlap and TF-IDF cosine.

    This is lexical retrieval, not embeddings or semantic vector search.
    """
    query_tokens = tokenize(query)
    if not query_tokens:
        return []
    rows = list(records)
    documents = [tokenize(_row_text(row)) for row in rows]
    query_counts = Counter(query_tokens)
    document_frequency = Counter(token for doc in documents for token in set(doc))
    n_docs = max(1, len(documents))
    def weight(token: str, count: int) -> float:
        return count * (math.log((n_docs + 1) / (document_frequency[token] + 1)) + 1)
    query_vector = {token: weight(token, count) for token, count in query_counts.items()}
    query_norm = math.sqrt(sum(value * value for value in query_vector.values())) or 1.0
    ranked: list[tuple[float, int, Any]] = []
    normalized_query = normalize_text(query)
    for index, (row, tokens) in enumerate(zip(rows, documents)):
        counts = Counter(tokens)
        vector = {token: weight(token, count) for token, count in counts.items()}
        norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
        cosine = sum(query_vector.get(token, 0.0) * value for token, value in vector.items()) / (query_norm * norm)
        overlap = sum(min(query_counts[token], counts[token]) for token in query_counts)
        phrase_bonus = 1.0 if normalized_query and normalized_query in normalize_text(_row_text(row)) else 0.0
        score = cosine + min(overlap, 5) * 0.12 + phrase_bonus * 0.75
        if score > 0:
            ranked.append((score, index, row))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [row for _, _, row in ranked[: max(1, min(limit, 100))]]
