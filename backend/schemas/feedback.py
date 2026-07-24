from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    session_id: str
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class EscalateRequest(BaseModel):
    session_id: str
    reason: str = Field(min_length=1)
    customer_email: str | None = None
