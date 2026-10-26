"""Vulture Bot - Datasets API for structured querying and export."""

from __future__ import annotations

import csv
import io
import json
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from app.database.session import get_db
from app.database.models.file import Dataset, DatasetRecord, DatasetColumn
from app.database.models.user import User
from app.auth.dependencies import get_current_user
from app.files.service import FileService
from app.security.auth import escape_spreadsheet_formula

router = APIRouter(prefix="/api/datasets", tags=["datasets"])
file_service = FileService()


class ImportDatasetRequest(BaseModel):
    file_id: str
    name: str
    field_mappings: Dict[str, str]  # { "col_header": "email" | "name" | "department" | ... }


@router.post("/import")
async def import_dataset(
    payload: ImportDatasetRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm field mappings and import validated records into the database."""
    try:
        dataset = await file_service.import_dataset(
            db=db,
            user_id=user.id,
            file_id=payload.file_id,
            name=payload.name,
            field_mappings=payload.field_mappings,
        )
        return {
            "success": True,
            "dataset_id": dataset.id,
            "name": dataset.name,
            "total_rows": dataset.total_rows,
            "valid_rows": dataset.valid_rows,
            "invalid_rows": dataset.invalid_rows,
            "duplicate_rows": dataset.duplicate_rows,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{dataset_id}")
async def get_dataset(
    dataset_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get dataset metadata, column definitions, and summary."""
    stmt = select(Dataset).where(Dataset.id == dataset_id, Dataset.user_id == user.id)
    ds = (await db.execute(stmt)).scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    cols_stmt = select(DatasetColumn).where(DatasetColumn.dataset_id == ds.id).order_by(DatasetColumn.column_index)
    columns = (await db.execute(cols_stmt)).scalars().all()

    return {
        "id": ds.id,
        "name": ds.name,
        "total_rows": ds.total_rows,
        "valid_rows": ds.valid_rows,
        "invalid_rows": ds.invalid_rows,
        "duplicate_rows": ds.duplicate_rows,
        "status": ds.status,
        "columns": [
            {
                "original_name": c.original_name,
                "display_name": c.display_name,
                "data_type": c.data_type,
                "mapped_field": c.mapped_field,
            }
            for c in columns
        ],
    }


@router.get("/{dataset_id}/query")
async def query_dataset_records(
    dataset_id: str,
    department: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    valid_only: bool = Query(True),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Filter records by department, year, section, email validity, or text search."""
    # Verify dataset ownership
    ds_stmt = select(Dataset).where(Dataset.id == dataset_id, Dataset.user_id == user.id)
    ds = (await db.execute(ds_stmt)).scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    conditions = [DatasetRecord.dataset_id == dataset_id]

    if valid_only:
        conditions.append(DatasetRecord.is_valid == True)
        conditions.append(DatasetRecord.email.isnot(None))

    if department:
        conditions.append(func.lower(DatasetRecord.department).contains(department.lower().strip()))

    if year:
        conditions.append(func.lower(DatasetRecord.year).contains(year.lower().strip()))

    if section:
        conditions.append(func.lower(DatasetRecord.section) == section.lower().strip())

    if search:
        s = f"%{search.lower().strip()}%"
        conditions.append(
            or_(
                func.lower(DatasetRecord.name).like(s),
                func.lower(DatasetRecord.email).like(s),
                func.lower(DatasetRecord.register_number).like(s),
            )
        )

    # Count total matching
    count_stmt = select(func.count(DatasetRecord.id)).where(and_(*conditions))
    total_matching = (await db.execute(count_stmt)).scalar() or 0

    # Fetch paginated rows
    stmt = (
        select(DatasetRecord)
        .where(and_(*conditions))
        .order_by(DatasetRecord.row_number.asc())
        .offset(offset)
        .limit(limit)
    )
    records = (await db.execute(stmt)).scalars().all()

    return {
        "dataset_id": dataset_id,
        "total_matching": total_matching,
        "limit": limit,
        "offset": offset,
        "records": [
            {
                "id": r.id,
                "row_number": r.row_number,
                "name": r.name,
                "email": r.email,
                "department": r.department,
                "year": r.year,
                "section": r.section,
                "register_number": r.register_number,
                "is_valid": r.is_valid,
                "is_duplicate": r.is_duplicate,
                "validation_errors": r.validation_errors,
                "raw_data": json.loads(r.data_json) if r.data_json else {},
            }
            for r in records
        ],
    }


@router.get("/{dataset_id}/export")
async def export_dataset(
    dataset_id: str,
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    department: Optional[str] = Query(None),
    year: Optional[str] = Query(None),
    valid_only: bool = Query(True),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export filtered dataset records with spreadsheet formula injection protection."""
    # Verify dataset ownership
    ds_stmt = select(Dataset).where(Dataset.id == dataset_id, Dataset.user_id == user.id)
    ds = (await db.execute(ds_stmt)).scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    conditions = [DatasetRecord.dataset_id == dataset_id]
    if valid_only:
        conditions.append(DatasetRecord.is_valid == True)
    if department:
        conditions.append(func.lower(DatasetRecord.department).contains(department.lower().strip()))
    if year:
        conditions.append(func.lower(DatasetRecord.year).contains(year.lower().strip()))

    stmt = select(DatasetRecord).where(and_(*conditions)).order_by(DatasetRecord.row_number.asc())
    records = (await db.execute(stmt)).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Row", "Name", "Email", "Department", "Year", "Section", "Register Number", "Valid"])

    for r in records:
        writer.writerow([
            r.row_number,
            escape_spreadsheet_formula(r.name or ""),
            escape_spreadsheet_formula(r.email or ""),
            escape_spreadsheet_formula(r.department or ""),
            escape_spreadsheet_formula(r.year or ""),
            escape_spreadsheet_formula(r.section or ""),
            escape_spreadsheet_formula(r.register_number or ""),
            "Yes" if r.is_valid else "No",
        ])

    csv_data = output.getvalue()
    filename = f"export_{ds.name.replace(' ', '_')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
