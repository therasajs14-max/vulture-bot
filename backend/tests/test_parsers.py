"""Vulture Bot - Unit Tests for File Parsers and Data Validation."""

import pytest
from pathlib import Path

from app.files.parsers import CSVParser, get_parser_registry
from app.files.service import detect_field_mapping, validate_email_address
from app.security.auth import escape_spreadsheet_formula, compute_content_hash


def test_field_mapping_heuristics():
    assert detect_field_mapping("Student Name") == "name"
    assert detect_field_mapping("Email Address") == "email"
    assert detect_field_mapping("Department") == "department"
    assert detect_field_mapping("Year") == "year"
    assert detect_field_mapping("Reg No") == "register_number"
    assert detect_field_mapping("Phone Number") == "phone"
    assert detect_field_mapping("Section") == "section"


def test_email_validation():
    ok, err = validate_email_address("student@example.com")
    assert ok is True
    assert err is None

    ok, err = validate_email_address("invalid-email-no-at")
    assert ok is False
    assert err is not None

    ok, err = validate_email_address("")
    assert ok is False
    assert "missing" in err.lower()


def test_formula_injection_protection():
    # Formulas must be prepended with a single quote to prevent DDE execution
    assert escape_spreadsheet_formula("=CMD|'/C calc'!A0") == "'=CMD|'/C calc'!A0"
    assert escape_spreadsheet_formula("+12345") == "'+12345"
    assert escape_spreadsheet_formula("-999") == "'-999"
    assert escape_spreadsheet_formula("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert escape_spreadsheet_formula("Normal Text") == "Normal Text"


def test_content_hash_integrity():
    hash1 = compute_content_hash("Task 1", "Subject A", "Body A", "a@test.com,b@test.com")
    hash2 = compute_content_hash("Task 1", "Subject A", "Body A", "a@test.com,b@test.com")
    assert hash1 == hash2

    # Modified body should produce completely different hash
    hash3 = compute_content_hash("Task 1", "Subject A", "Modified Body", "a@test.com,b@test.com")
    assert hash1 != hash3


@pytest.mark.asyncio
async def test_csv_parser_with_sample_file():
    sample_path = Path(__file__).parent / "data" / "sample_students.csv"
    assert sample_path.exists(), "Sample file must exist"

    parser = CSVParser()
    result = await parser.parse(sample_path)

    assert result.total_rows == 20
    assert "Student Name" in result.columns
    assert "Email Address" in result.columns
    assert len(result.rows) == 20
