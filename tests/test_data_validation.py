from app.data.validation import validate_product_records


def test_product_data_contract_accepts_valid_rows():
    result = validate_product_records([{"Product Name": "A", "Price": 10, "Stock": 2}])
    assert result["ok"] is True


def test_product_data_contract_rejects_missing_or_invalid_price():
    result = validate_product_records([{"Product Name": "A", "Price": "unknown"}])
    assert result["ok"] is False
    assert "Invalid" in result["errors"][0]
