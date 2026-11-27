"""Create a clearly named sample workbook; never overwrites company.xlsx."""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openpyxl import Workbook

from app.data.validation import validate_product_records


def main() -> None:
    target = Path("sample_company.xlsx")
    if target.exists():
        raise SystemExit(f"Refusing to overwrite existing file: {target}")
    records = [
        {"Product Name": "Product A", "Price": 120, "Stock": 25, "Category": "منتجات", "Updated": "sample"},
        {"Product Name": "Product B", "Price": 85, "Stock": 12, "Category": "منتجات", "Updated": "sample"},
        {"Product Name": "خدمة الدعم المميز", "Price": 250, "Stock": "متاح", "Category": "خدمات", "Updated": "sample"},
    ]
    validation = validate_product_records(records)
    if not validation["ok"]:
        raise SystemExit("Sample data validation failed: " + "; ".join(validation["errors"]))
    workbook = Workbook()
    sheet = workbook.active
    headers = list(records[0])
    sheet.append(headers)
    for record in records:
        sheet.append([record.get(header) for header in headers])
    workbook.save(target)
    print(f"Created {target} with {len(records)} sample records")


if __name__ == "__main__":
    main()
