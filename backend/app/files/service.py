"""Vulture Bot - File Processing and Dataset Management Service."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional
import email_validator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.config import get_settings
from app.files.parsers import get_parser_registry, ParsedTable
from app.database.models.file import (
    UploadedFile, Dataset, DatasetColumn, DatasetRecord
)
from app.security.auth import escape_spreadsheet_formula


# Column heuristic patterns
PATTERNS = {
    "name": [r"name", r"student_?name", r"full_?name", r"candidate", r"first_?name"],
    "register_number": [r"reg", r"roll", r"id", r"student_?id", r"usn", r"matric", r"admission_?no", r"reg_?no"],
    "email": [r"email", r"mail", r"e_?mail", r"email_?address", r"student_?email"],
    "department": [r"dept", r"department", r"branch", r"course", r"program", r"discipline"],
    "year": [r"year", r"academic_?year", r"batch", r"class_?year", r"yr"],
    "semester": [r"sem", r"semester", r"term"],
    "section": [r"section", r"sec", r"class", r"division", r"group"],
    "phone": [r"phone", r"mobile", r"contact", r"tel", r"phone_?no"],
    "task": [r"task", r"assignment", r"work", r"topic", r"project", r"activity", r"homework", r"question", r"deliverable"],
}


def detect_field_mapping(column_name: str) -> Optional[str]:
    """Detect probable standardized field from column header."""
    col_clean = column_name.lower().strip()
    col_clean = re.sub(r"[^a-z0-9_]", "_", col_clean)

    for field_name, regex_list in PATTERNS.items():
        for pat in regex_list:
            if re.search(pat, col_clean):
                return field_name
    return None


def validate_email_address(email: str) -> tuple[bool, Optional[str]]:
    """Validate email address syntax using email-validator."""
    if not email or not email.strip():
        return False, "Email address is missing"
    email = email.strip()
    try:
        email_validator.validate_email(email, check_deliverability=False)
        return True, None
    except email_validator.EmailNotValidError as e:
        return False, str(e)


class FileService:
    """Handles upload validation, parsing, field detection, and dataset persistence."""

    def __init__(self):
        self.registry = get_parser_registry()
        self.settings = get_settings()

    async def parse_and_preview(
        self,
        file_path: Path,
        original_filename: str,
    ) -> dict[str, Any]:
        """Parse file and return preview statistics with detected field mappings."""
        ext = file_path.suffix.lower()
        parser = self.registry.get_parser(ext)
        if not parser:
            raise ValueError(f"No parser available for file format '{ext}'.")

        parsed: ParsedTable = await parser.parse(file_path)

        # Detect mappings
        mappings: dict[str, Optional[str]] = {}
        for col in parsed.columns:
            mappings[col] = detect_field_mapping(col)

        email_col = next((c for c, m in mappings.items() if m == "email"), None)
        name_col = next((c for c, m in mappings.items() if m == "name"), None)
        dept_col = next((c for c, m in mappings.items() if m == "department"), None)
        year_col = next((c for c, m in mappings.items() if m == "year"), None)

        # Preview and analysis of first rows and stats
        valid_emails = 0
        missing_emails = 0
        invalid_emails = 0
        duplicate_emails = 0
        seen_emails: set[str] = set()

        sample_rows = []
        for i, row in enumerate(parsed.rows):
            email_val = str(row.get(email_col, "")).strip() if email_col else ""
            is_valid = True
            err = None

            if email_col:
                if not email_val:
                    missing_emails += 1
                    is_valid = False
                    err = "Missing email"
                else:
                    ok, msg = validate_email_address(email_val)
                    if ok:
                        valid_emails += 1
                        if email_val.lower() in seen_emails:
                            duplicate_emails += 1
                        seen_emails.add(email_val.lower())
                    else:
                        invalid_emails += 1
                        is_valid = False
                        err = msg

            if i < 15:
                sample_rows.append({
                    "row_index": i + 1,
                    "data": row,
                    "is_valid": is_valid,
                    "error": err,
                })

        rows_requiring_review = missing_emails + invalid_emails + duplicate_emails

        return {
            "filename": original_filename,
            "total_rows": parsed.total_rows,
            "columns": parsed.columns,
            "field_mappings": mappings,
            "stats": {
                "total_rows": parsed.total_rows,
                "valid_emails": valid_emails if email_col else parsed.total_rows,
                "missing_emails": missing_emails,
                "invalid_emails": invalid_emails,
                "duplicate_emails": duplicate_emails,
                "rows_requiring_review": rows_requiring_review,
            },
            "sample_rows": sample_rows,
            "raw_text_preview": parsed.raw_text[:500] if parsed.raw_text else None,
        }

    async def import_dataset(
        self,
        db: AsyncSession,
        user_id: str,
        file_id: str,
        name: str,
        field_mappings: dict[str, str],
    ) -> Dataset:
        """Import parsed rows into persistent Dataset and DatasetRecord entities."""
        file_obj = await db.get(UploadedFile, file_id)
        if not file_obj:
            raise ValueError("Uploaded file not found.")

        file_path = Path(file_obj.storage_path)
        ext = file_path.suffix.lower()
        parser = self.registry.get_parser(ext)
        parsed: ParsedTable = await parser.parse(file_path)

        # Reverse lookup for mapped fields
        field_to_col: dict[str, str] = {}
        for col, field in field_mappings.items():
            if field:
                field_to_col[field] = col

        # Create Dataset
        dataset = Dataset(
            file_id=file_id,
            user_id=user_id,
            name=name,
            columns_json=json.dumps(parsed.columns),
            field_mappings_json=json.dumps(field_mappings),
            status="importing",
        )
        db.add(dataset)
        await db.flush()

        # Create Column entities
        for i, col in enumerate(parsed.columns):
            db.add(DatasetColumn(
                dataset_id=dataset.id,
                original_name=col,
                display_name=col.replace("_", " ").title(),
                data_type="email" if field_mappings.get(col) == "email" else "string",
                mapped_field=field_mappings.get(col),
                column_index=i,
            ))

        # Import Records
        valid_count = 0
        invalid_count = 0
        seen_emails: set[str] = set()
        duplicate_count = 0

        email_col = field_to_col.get("email")
        name_col = field_to_col.get("name")
        dept_col = field_to_col.get("department")
        year_col = field_to_col.get("year")
        sec_col = field_to_col.get("section")
        reg_col = field_to_col.get("register_number")

        for idx, row in enumerate(parsed.rows):
            email_val = str(row.get(email_col, "")).strip() if email_col else ""
            is_valid = True
            err = None
            is_dup = False

            if email_col:
                if not email_val:
                    is_valid = False
                    err = "Email is missing"
                else:
                    ok, msg = validate_email_address(email_val)
                    if not ok:
                        is_valid = False
                        err = msg
                    elif email_val.lower() in seen_emails:
                        is_dup = True
                        duplicate_count += 1
                    seen_emails.add(email_val.lower())

            if is_valid and not is_dup:
                valid_count += 1
            else:
                invalid_count += 1

            record = DatasetRecord(
                dataset_id=dataset.id,
                row_number=idx + 1,
                data_json=json.dumps(row),
                is_valid=is_valid,
                validation_errors=err,
                is_duplicate=is_dup,
                name=str(row.get(name_col, "")).strip() if name_col else None,
                email=email_val or None,
                department=str(row.get(dept_col, "")).strip() if dept_col else None,
                year=str(row.get(year_col, "")).strip() if year_col else None,
                section=str(row.get(sec_col, "")).strip() if sec_col else None,
                register_number=str(row.get(reg_col, "")).strip() if reg_col else None,
            )
            db.add(record)

        dataset.total_rows = len(parsed.rows)
        dataset.valid_rows = valid_count
        dataset.invalid_rows = invalid_count
        dataset.duplicate_rows = duplicate_count
        dataset.status = "imported"
        file_obj.status = "imported"

        await db.commit()
        await db.refresh(dataset)
        return dataset
