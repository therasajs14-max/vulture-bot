"""Vulture Bot - File and Dataset database models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text, func, Index, BigInteger
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class UploadedFile(Base):
    """Uploaded file metadata model."""

    __tablename__ = "uploaded_files"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # File metadata
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    safe_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # csv, xlsx, pdf, etc.
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)

    # Processing status
    status: Mapped[str] = mapped_column(
        String(20), default="uploaded"
    )  # uploaded, processing, parsed, imported, error
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Parsing results summary
    row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    column_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parsed_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="uploaded_files")
    dataset: Mapped[Optional["Dataset"]] = relationship(
        back_populates="source_file", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<UploadedFile '{self.original_filename}' ({self.status})>"


class Dataset(Base):
    """Imported dataset model — structured data from a parsed file."""

    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    file_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("uploaded_files.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Schema information
    columns_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: column definitions
    field_mappings_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: detected mappings

    # Import statistics
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="preview"
    )  # preview, importing, imported, error

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    source_file: Mapped["UploadedFile"] = relationship(back_populates="dataset")
    records: Mapped[list["DatasetRecord"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    columns: Mapped[list["DatasetColumn"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Dataset '{self.name}' ({self.total_rows} rows)>"


class DatasetColumn(Base):
    """Dataset column definition with field mapping."""

    __tablename__ = "dataset_columns"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    dataset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str] = mapped_column(String(50), default="string")  # string, number, email, date
    mapped_field: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # name, email, department, year, section, register_number, phone
    column_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    dataset: Mapped["Dataset"] = relationship(back_populates="columns")

    def __repr__(self) -> str:
        return f"<DatasetColumn '{self.original_name}' -> {self.mapped_field}>"


class DatasetRecord(Base):
    """Individual record (row) in an imported dataset."""

    __tablename__ = "dataset_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    dataset_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    data_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: row data

    # Validation
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    validation_errors: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)

    # Extracted common fields for efficient querying
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    year: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    section: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    register_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    dataset: Mapped["Dataset"] = relationship(back_populates="records")

    __table_args__ = (
        Index("ix_records_dataset_valid", "dataset_id", "is_valid"),
        Index("ix_records_dept_year", "dataset_id", "department", "year"),
    )

    def __repr__(self) -> str:
        return f"<DatasetRecord row={self.row_number} valid={self.is_valid}>"
