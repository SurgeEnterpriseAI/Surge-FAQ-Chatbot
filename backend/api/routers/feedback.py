from fastapi import APIRouter, Depends, HTTPException

from backend.dependencies import get_current_user
from backend.schemas.common import StatusResponse
from backend.schemas.feedback import EscalateRequest, FeedbackRequest

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=StatusResponse)
async def submit_feedback(body: FeedbackRequest, user: dict = Depends(get_current_user)):
    from repositories.feedback_repository import FeedbackRepository

    try:
        await FeedbackRepository.add_feedback(
            chat_id=body.session_id,
            rating=body.rating,
            comment=body.comment,
            user_id=user["user_id"],
        )
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Could not save feedback. Please try again later.")
    return StatusResponse(status="ok")


@router.post("/escalate", response_model=StatusResponse)
async def escalate(body: EscalateRequest, user: dict = Depends(get_current_user)):
    from repositories.escalation_repository import EscalationRepository
    from repositories.ticket_repository import TicketRepository

    try:
        await EscalationRepository.create_escalation(
            chat_id=body.session_id,
            reason=body.reason,
            user_id=user["user_id"],
        )
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Could not create escalation. Please try again later.")

    detail = None
    if body.customer_email:
        try:
            await TicketRepository.create_ticket(
                issue=body.reason,
                customer_email=body.customer_email,
                user_id=user["user_id"],
                chat_id=body.session_id,
            )
            detail = "Escalation and support ticket created"
        except Exception:
            detail = "Escalation created; ticket creation failed"

    return StatusResponse(status="ok", detail=detail)
