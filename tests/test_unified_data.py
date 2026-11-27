import csv
import json
import sqlite3

from openpyxl import Workbook

from app.data.manager import DataSourceManager


def test_unified_manager_ingests_common_sources(tmp_path):
    csv_path = tmp_path / "customers.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["name", "city"])
        writer.writeheader()
        writer.writerow({"name": "Ali", "city": "Cairo"})
    json_path = tmp_path / "policies.json"
    json_path.write_text(json.dumps({"records": [{"title": "Returns", "content": "7 days"}]}), encoding="utf-8")
    xlsx_path = tmp_path / "products.xlsx"
    workbook = Workbook(); sheet = workbook.active; sheet.append(["Product Name", "Price"]); sheet.append(["A", 10]); workbook.save(xlsx_path)
    db_path = tmp_path / "events.db"
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE events (name TEXT, value TEXT)")
        db.execute("INSERT INTO events VALUES ('login', '1')")
        db.commit()

    manager = DataSourceManager()
    assert manager.ingest_file(str(csv_path), "customer") == 1
    assert manager.ingest_file(str(json_path), "policy") == 1
    assert manager.ingest_file(str(xlsx_path), "product") == 1
    assert manager.ingest_sqlite(str(db_path)) == 1
    assert manager.search("returns")
    assert manager.summary()["total"] == 4
