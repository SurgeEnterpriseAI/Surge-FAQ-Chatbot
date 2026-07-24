from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None
    tenant_id: str | None = None
    department_id: str | None = None
    project_id: str | None = None


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    metadata: Any = None
    timestamp: datetime | None = None


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[MessageOut]
    summary: str | None = None


class ConversationOut(BaseModel):
    id: str
    title: str | None = None
    created_at: datetime | None = None
