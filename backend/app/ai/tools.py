"""Vulture Bot - Controlled Tool Registry.

Provides validated tools for LLMs with strict backend validation.
Never executes arbitrary SQL or shell commands.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Coroutine
from pydantic import BaseModel, Field

from app.ai.base import ToolDefinition


AVAILABLE_TOOLS: list[ToolDefinition] = [
    ToolDefinition(
        name="search_students",
        description="Search and filter student records from an uploaded dataset using structured criteria (department, year, section, email validity).",
        parameters={
            "type": "object",
            "properties": {
                "dataset_id": {
                    "type": "string",
                    "description": "ID of the dataset to query (optional if only one exists in conversation)."
                },
                "department": {
                    "type": "string",
                    "description": "Filter by department (e.g. 'CSE', 'AI & DS', 'ECE', 'Mechanical'). Case-insensitive."
                },
                "year": {
                    "type": "string",
                    "description": "Filter by academic year (e.g. '1', '2', '3', '4', 'Final', 'First')."
                },
                "section": {
                    "type": "string",
                    "description": "Filter by class section (e.g. 'A', 'B', 'C')."
                },
                "valid_email_only": {
                    "type": "boolean",
                    "description": "If true, return only students with verified valid email addresses.",
                    "default": True
                },
                "limit": {
                    "type": "integer",
                    "description": "Max rows to return for preview",
                    "default": 10
                }
            }
        }
    ),
    ToolDefinition(
        name="get_dataset_summary",
        description="Get statistical summary of an uploaded dataset (total rows, column list, department breakdown, missing fields count).",
        parameters={
            "type": "object",
            "properties": {
                "dataset_id": {
                    "type": "string",
                    "description": "Optional dataset ID."
                }
            }
        }
    ),
    ToolDefinition(
        name="create_email_draft",
        description="Create an email draft for admin review and approval. Does NOT send emails. Generates a preview with recipient count.",
        parameters={
            "type": "object",
            "required": ["task_name", "subject", "body_template"],
            "properties": {
                "task_name": {
                    "type": "string",
                    "description": "Short human-readable title for the task (e.g. 'Final Year Project Review Guidelines')."
                },
                "subject": {
                    "type": "string",
                    "description": "The exact subject line of the email."
                },
                "body_template": {
                    "type": "string",
                    "description": "Email body text. Can use placeholders like {name}, {department}, {register_number}."
                },
                "department_filter": {
                    "type": "string",
                    "description": "Department filter applied for recipients."
                },
                "year_filter": {
                    "type": "string",
                    "description": "Year filter applied for recipients."
                },
                "is_personalized": {
                    "type": "boolean",
                    "description": "Whether each student gets a personalized email greeting and details.",
                    "default": True
                }
            }
        }
    ),
    ToolDefinition(
        name="request_batch_approval",
        description="Submit an email draft to the administrator approval queue. The admin must explicitly click Approve in the UI.",
        parameters={
            "type": "object",
            "required": ["draft_id"],
            "properties": {
                "draft_id": {
                    "type": "string",
                    "description": "The ID of the email draft to submit for admin approval."
                }
            }
        }
    ),
    ToolDefinition(
        name="get_email_batch_status",
        description="Check sending status, sent count, and failure count for an email batch.",
        parameters={
            "type": "object",
            "required": ["batch_id"],
            "properties": {
                "batch_id": {
                    "type": "string",
                    "description": "The ID of the batch."
                }
            }
        }
    )
]


def get_available_tools() -> list[ToolDefinition]:
    return AVAILABLE_TOOLS
