"""Pydantic request/response models for the FinSplit API.

The split `result` payload is Claude-generated JSON. We keep it loosely typed
(`dict`) so we never reject a valid split just because the model added or
reshaped a field — the frontend tolerates the documented shape.
"""

from typing import Any

from pydantic import BaseModel, Field


class SplitRequest(BaseModel):
    description: str = Field(..., description="Plain English description of the meal/outing")


class CorrectRequest(BaseModel):
    original_description: str
    previous_result: dict[str, Any]
    correction: str = Field(..., description="Plain English correction to apply")


class SplitResponse(BaseModel):
    id: str | None
    result: dict[str, Any]


class StoredSplitResponse(BaseModel):
    id: str
    result: dict[str, Any]
    created_at: str
