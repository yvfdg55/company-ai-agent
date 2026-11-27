"""Read-only connectors for common company data sources."""
from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .unified import UnifiedRecord


def _record(source: str, data_type: str, title: str, content: str, structured: dict[str, Any], metadata: dict[str, Any] | None = None) -> UnifiedRecord:
    key = f"{source}:{data_type}:{title}:{content}"[:1000]
    stable_id = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
    return UnifiedRecord(id=stable_id, source=source, data_type=data_type, title=title, content=content, structured_data=structured, metadata=metadata or {})


def records_from_rows(rows: Iterable[dict[str, Any]], source: str, data_type: str = "record") -> list[UnifiedRecord]:
    result = []
    for index, row in enumerate(rows, start=1):
        title = str(row.get("Product Name", row.get("name", row.get("title", f"{data_type} {index}"))))
        result.append(_record(source, data_type, title, json.dumps(row, ensure_ascii=False, default=str), dict(row), {"row": index}))
    return result


def load_csv(path: str, data_type: str = "record") -> list[UnifiedRecord]:
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return records_from_rows(csv.DictReader(handle), path, data_type)


def load_json(path: str, data_type: str = "record") -> list[UnifiedRecord]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload if isinstance(payload, list) else payload.get("records", [payload]) if isinstance(payload, dict) else []
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("JSON data must contain objects or a records array")
    return records_from_rows(rows, path, data_type)


def load_excel(path: str, data_type: str = "record") -> list[UnifiedRecord]:
    from openpyxl import load_workbook
    workbook = load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    workbook.close()
    if not rows:
        return []
    headers = [str(value or "").strip() for value in rows[0]]
    records = []
    for index, row in enumerate(rows[1:], start=2):
        record = {header: row[i] if i < len(row) else None for i, header in enumerate(headers) if header}
        if any(value not in (None, "") for value in record.values()):
            records.extend(records_from_rows([record], path, data_type))
            records[-1].metadata["row"] = index
    return records


def load_pdf(path: str, data_type: str = "document") -> list[UnifiedRecord]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Install pypdf to ingest PDF files") from exc
    reader = PdfReader(path)
    return [_record(path, data_type, f"Page {index}", page.extract_text() or "", {}, {"page": index}) for index, page in enumerate(reader.pages, start=1)]


def load_docx(path: str, data_type: str = "document") -> list[UnifiedRecord]:
    try:
        from docx import Document
    except ImportError as exc:
        raise RuntimeError("Install python-docx to ingest DOCX files") from exc
    document = Document(path)
    content = "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
    return [_record(path, data_type, Path(path).stem, content, {}, {"file_name": Path(path).name})]


def load_sqlite(path: str, tables: list[str] | None = None) -> list[UnifiedRecord]:
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        available = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        selected = tables or available
        invalid = set(selected) - set(available)
        if invalid:
            raise ValueError("Unknown SQLite tables: " + ", ".join(sorted(invalid)))
        result: list[UnifiedRecord] = []
        for table in selected:
            rows = [dict(row) for row in db.execute(f'SELECT * FROM "{table}" LIMIT 10000')]
            result.extend(records_from_rows(rows, path, table))
        return result


def load_mysql(config: dict[str, Any], tables: list[str] | None = None) -> list[UnifiedRecord]:
    try:
        import mysql.connector
    except ImportError as exc:
        raise RuntimeError("Install mysql-connector-python to ingest MySQL") from exc
    connection = mysql.connector.connect(**config)
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = DATABASE()")
        available = [row[0] for row in cursor.fetchall()]
        selected = tables or available
        invalid = set(selected) - set(available)
        if invalid:
            raise ValueError("Unknown MySQL tables: " + ", ".join(sorted(invalid)))
        result: list[UnifiedRecord] = []
        for table in selected:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(f"SELECT * FROM `{table}` LIMIT 10000")
            result.extend(records_from_rows(cursor.fetchall(), "mysql", table))
            cursor.close()
        return result
    finally:
        connection.close()


def load_file(path: str, data_type: str = "record") -> list[UnifiedRecord]:
    suffix = Path(path).suffix.casefold()
    loaders = {".csv": load_csv, ".json": load_json, ".xlsx": load_excel, ".xlsm": load_excel, ".pdf": load_pdf, ".docx": load_docx}
    if suffix not in loaders:
        raise ValueError(f"Unsupported data source: {suffix}")
    return loaders[suffix](path, data_type)
