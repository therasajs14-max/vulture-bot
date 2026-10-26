"""Vulture Bot - File Upload and Extraction Endpoints."""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.database.session import get_db
from app.database.models.file import UploadedFile
from app.database.models.user import User
from app.auth.dependencies import get_current_user
from app.files.service import FileService
from app.security.auth import sanitize_filename

router = APIRouter(prefix="/api/files", tags=["files"])
file_service = FileService()


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Securely upload and parse a document/dataset file."""
    settings = get_settings()

    # 1. Validate file extension
    ext = Path(file.filename or "").suffix.lower()
    clean_ext = ext.lstrip(".")
    if clean_ext not in settings.allowed_file_types_list:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed types: {settings.allowed_file_types}",
        )

    # 2. Prepare safe destination
    upload_dir = settings.upload_path
    safe_name = f"{uuid.uuid4()}_{sanitize_filename(file.filename or 'upload')}"
    dest_path = upload_dir / safe_name

    # 3. Stream to disk while checking file size limit
    total_bytes = 0
    max_bytes = settings.max_upload_size_bytes

    try:
        with open(dest_path, "wb") as f_out:
            while chunk := await file.read(64 * 1024):
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds maximum allowed size of {settings.max_upload_size_mb} MB.",
                    )
                f_out.write(chunk)
    except Exception as e:
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # 4. Save metadata record in DB
    uploaded_file = UploadedFile(
        user_id=user.id,
        conversation_id=conversation_id,
        original_filename=file.filename or "uploaded_file",
        safe_filename=safe_name,
        file_type=clean_ext,
        mime_type=file.content_type,
        file_size=total_bytes,
        storage_path=str(dest_path),
        status="processing",
    )
    db.add(uploaded_file)
    await db.commit()
    await db.refresh(uploaded_file)

    # 5. Parse and generate preview
    try:
        preview_data = await file_service.parse_and_preview(dest_path, uploaded_file.original_filename)
        uploaded_file.status = "parsed"
        uploaded_file.row_count = preview_data.get("total_rows")
        uploaded_file.column_count = len(preview_data.get("columns", []))
        await db.commit()

        return {
            "file_id": uploaded_file.id,
            "filename": uploaded_file.original_filename,
            "file_type": uploaded_file.file_type,
            "file_size": uploaded_file.file_size,
            "preview": preview_data,
        }
    except Exception as e:
        uploaded_file.status = "error"
        uploaded_file.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=422, detail=f"Error parsing file: {str(e)}")


@router.get("/{file_id}/preview")
async def get_file_preview(
    file_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve parsing preview and statistics for an uploaded file."""
    stmt = select(UploadedFile).where(
        UploadedFile.id == file_id,
        UploadedFile.user_id == user.id,
    )
    f = (await db.execute(stmt)).scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found.")

    file_path = Path(f.storage_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Stored file could not be found.")

    preview_data = await file_service.parse_and_preview(file_path, f.original_filename)
    return {
        "file_id": f.id,
        "filename": f.original_filename,
        "status": f.status,
        "preview": preview_data,
    }
