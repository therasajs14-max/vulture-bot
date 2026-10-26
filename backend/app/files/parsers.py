"""Vulture Bot - Multi-Format File Parser Registry.

Supports CSV, Excel (.xlsx, .xls), PDF, DOCX, TXT, JSON, and XML.
Uses a pluggable parser registry pattern.
"""

from __future__ import annotations

import csv
import json
import io
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class ParsedTable:
    """Standardized parsed tabular data from any document format."""
    columns: list[str]
    rows: list[dict[str, Any]]
    total_rows: int
    raw_text: Optional[str] = None


class BaseFileParser(ABC):
    """Abstract file parser interface."""

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """List of supported extensions, e.g. ['.csv']."""
        pass

    @abstractmethod
    async def parse(self, file_path: Path) -> ParsedTable:
        """Parse file into tabular representation."""
        pass


class CSVParser(BaseFileParser):
    def supported_extensions(self) -> list[str]:
        return [".csv"]

    async def parse(self, file_path: Path) -> ParsedTable:
        import pandas as pd
        # Try UTF-8 with fallbacks
        encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
        df = None
        for enc in encodings:
            try:
                df = pd.read_csv(file_path, encoding=enc, dtype=str)
                break
            except Exception:
                continue

        if df is None:
            raise ValueError(f"Could not parse CSV file {file_path.name} with standard encodings.")

        # Clean column names
        df.columns = [str(c).strip() for c in df.columns]
        # Replace NaN with empty string
        df = df.fillna("")
        rows = df.to_dict(orient="records")
        return ParsedTable(
            columns=list(df.columns),
            rows=rows,
            total_rows=len(rows)
        )


class ExcelParser(BaseFileParser):
    def supported_extensions(self) -> list[str]:
        return [".xlsx", ".xls"]

    async def parse(self, file_path: Path) -> ParsedTable:
        import pandas as pd
        df = pd.read_excel(file_path, dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        df = df.fillna("")
        rows = df.to_dict(orient="records")
        return ParsedTable(
            columns=list(df.columns),
            rows=rows,
            total_rows=len(rows)
        )


class JSONParser(BaseFileParser):
    def supported_extensions(self) -> list[str]:
        return [".json"]

    async def parse(self, file_path: Path) -> ParsedTable:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list) and all(isinstance(x, dict) for x in data):
            # Flatten or collect all keys
            keys = []
            for item in data:
                for k in item.keys():
                    if k not in keys:
                        keys.append(k)
            rows = [{k: str(item.get(k, "")) for k in keys} for item in data]
            return ParsedTable(columns=keys, rows=rows, total_rows=len(rows))
        elif isinstance(data, dict):
            # Key-value or nested records
            for key, val in data.items():
                if isinstance(val, list) and all(isinstance(x, dict) for x in val):
                    keys = list(val[0].keys()) if val else []
                    rows = [{k: str(item.get(k, "")) for k in keys} for item in val]
                    return ParsedTable(columns=keys, rows=rows, total_rows=len(rows))
            # Fallback single-object
            return ParsedTable(
                columns=list(data.keys()),
                rows=[{k: str(v) for k, v in data.items()}],
                total_rows=1
            )
        else:
            raise ValueError("Unsupported JSON structure: expected array of objects.")


class TextParser(BaseFileParser):
    def supported_extensions(self) -> list[str]:
        return [".txt", ".tsv"]

    async def parse(self, file_path: Path) -> ParsedTable:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [line.strip() for line in f if line.strip()]

        if not lines:
            return ParsedTable(columns=["content"], rows=[], total_rows=0)

        # Detect tab-separated
        if "\t" in lines[0]:
            reader = csv.reader(lines, delimiter="\t")
            all_rows = list(reader)
            headers = [h.strip() for h in all_rows[0]]
            data_rows = [
                {headers[i]: r[i] if i < len(r) else "" for i in range(len(headers))}
                for r in all_rows[1:]
            ]
            return ParsedTable(columns=headers, rows=data_rows, total_rows=len(data_rows))

        # Plain lines
        rows = [{"line_number": i + 1, "text": line} for i, line in enumerate(lines)]
        return ParsedTable(
            columns=["line_number", "text"],
            rows=rows,
            total_rows=len(rows),
            raw_text="\n".join(lines)
        )


class DocxParser(BaseFileParser):
    def supported_extensions(self) -> list[str]:
        return [".docx", ".doc"]

    async def parse(self, file_path: Path) -> ParsedTable:
        import docx
        doc = docx.Document(file_path)

        # Check for tables first
        if doc.tables:
            first_table = doc.tables[0]
            header_row = [cell.text.strip() for cell in first_table.rows[0].cells]
            rows = []
            for row in first_table.rows[1:]:
                row_data = {}
                for i, cell in enumerate(row.cells):
                    if i < len(header_row):
                        row_data[header_row[i]] = cell.text.strip()
                rows.append(row_data)
            return ParsedTable(columns=header_row, rows=rows, total_rows=len(rows))

        # Otherwise extract paragraphs
        text_lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        rows = [{"paragraph_number": i + 1, "text": t} for i, t in enumerate(text_lines)]
        return ParsedTable(
            columns=["paragraph_number", "text"],
            rows=rows,
            total_rows=len(rows),
            raw_text="\n".join(text_lines)
        )


class PDFParser(BaseFileParser):
    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    async def parse(self, file_path: Path) -> ParsedTable:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        all_text = []
        for page in doc:
            all_text.append(page.get_text())
        full_text = "\n".join(all_text)

        # Look for table structures or tabular text lines
        lines = [line.strip() for line in full_text.splitlines() if line.strip()]
        rows = [{"line_number": i + 1, "text": line} for i, line in enumerate(lines)]
        return ParsedTable(
            columns=["line_number", "text"],
            rows=rows,
            total_rows=len(rows),
            raw_text=full_text
        )


class XMLParser(BaseFileParser):
    def supported_extensions(self) -> list[str]:
        return [".xml"]

    async def parse(self, file_path: Path) -> ParsedTable:
        import xml.etree.ElementTree as ET
        tree = ET.parse(file_path)
        root = tree.getroot()

        records = []
        all_tags = set()
        for child in root:
            record = {}
            for sub in child:
                record[sub.tag] = (sub.text or "").strip()
                all_tags.add(sub.tag)
            if record:
                records.append(record)

        columns = sorted(list(all_tags)) if all_tags else ["content"]
        rows = [{col: r.get(col, "") for col in columns} for r in records]
        return ParsedTable(columns=columns, rows=rows, total_rows=len(rows))


class ParserRegistry:
    """Registry coordinating all file parsers."""

    def __init__(self):
        self._parsers: dict[str, BaseFileParser] = {}
        # Register standard parsers
        for parser_cls in [
            CSVParser,
            ExcelParser,
            JSONParser,
            TextParser,
            DocxParser,
            PDFParser,
            XMLParser,
        ]:
            self.register(parser_cls())

    def register(self, parser: BaseFileParser) -> None:
        for ext in parser.supported_extensions():
            self._parsers[ext.lower()] = parser

    def get_parser(self, extension: str) -> Optional[BaseFileParser]:
        ext = extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        return self._parsers.get(ext)

    def is_supported(self, extension: str) -> bool:
        return self.get_parser(extension) is not None


_registry: Optional[ParserRegistry] = None


def get_parser_registry() -> ParserRegistry:
    global _registry
    if _registry is None:
        _registry = ParserRegistry()
    return _registry
