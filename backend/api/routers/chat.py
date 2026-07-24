import json

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from backend.dependencies import get_current_user, get_rag_system
from backend.schemas.chat import ChatRequest, ConversationOut, HistoryResponse, MessageOut
from backend.schemas.common import StatusResponse
from backend.services.chat_service import ChatService
from backend.services.conversation_service import ConversationService
from enterprise.tenant import TenantContext, active_tenant

router = APIRouter(tags=["chat"])


@router.post("/chat")
async def chat(
    body: ChatRequest,
    user: dict = Depends(get_current_user),
    rag_system=Depends(get_rag_system),
):
    service = ChatService(rag_system)
    tenant = TenantContext(body.tenant_id, body.department_id, body.project_id)

    async def event_source():
        token = active_tenant.set(tenant)
        try:
            async for event in service.stream(body.message, session_id=body.session_id, user_id=user["user_id"]):
                yield {"event": event["event"], "data": json.dumps(event["data"])}
        finally:
            active_tenant.reset(token)

    return EventSourceResponse(event_source())


@router.get("/history/{session_id}", response_model=HistoryResponse)
async def history(session_id: str, user: dict = Depends(get_current_user)):
    from repositories.chat_repository import ChatRepository
    chat_record = await ChatRepository.get_chat(session_id)
    if not chat_record:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if chat_record.userId != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this conversation")

    messages, summary = await ConversationService.get_history(session_id)
    
    def parse_metadata(metadata):
        if not metadata:
            return None
        if isinstance(metadata, dict):
            return metadata
        if isinstance(metadata, str):
            try:
                return json.loads(metadata)
            except Exception:
                return None
        return None

    return HistoryResponse(
        session_id=session_id,
        messages=[
            MessageOut(
                id=m.id,
                role=m.role,
                content=m.content,
                metadata=parse_metadata(m.metadata),
                timestamp=m.timestamp,
            )
            for m in messages
        ],
        summary=summary,
    )


@router.get("/conversations", response_model=list[ConversationOut])
async def conversations(user: dict = Depends(get_current_user)):
    chats = await ConversationService.list_conversations(user["user_id"])
    return [ConversationOut(id=c.id, title=c.title, created_at=c.createdAt) for c in chats]


@router.delete("/conversations/{session_id}", response_model=StatusResponse)
async def delete_conversation(
    session_id: str,
    user: dict = Depends(get_current_user),
    rag_system=Depends(get_rag_system),
):
    from repositories.chat_repository import ChatRepository
    chat_record = await ChatRepository.get_chat(session_id)
    if not chat_record:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if chat_record.userId != user["user_id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this conversation")

    deleted = await ConversationService.delete_conversation(rag_system, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return StatusResponse(status="deleted")
