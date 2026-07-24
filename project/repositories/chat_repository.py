from database.supabase_client import prisma_client, connect_prisma
import logging
import json
from prisma import Json

logger = logging.getLogger(__name__)

class ChatRepository:
    @staticmethod
    async def create_chat(chat_id: str, user_id: str = None, title: str = None):
        """Create a new chat session in Supabase."""
        await connect_prisma()
        try:
            # Check if chat already exists
            existing = await prisma_client.chat.find_unique(where={"id": chat_id})
            if existing:
                return existing
                
            data = {"id": chat_id, "title": title}
            if user_id:
                # Double check if user exists, otherwise create user in DB if they are guest
                user = await prisma_client.user.find_unique(where={"id": user_id})
                if not user:
                    await prisma_client.user.create(data={"id": user_id, "email": f"{user_id}@guest.com", "name": "Guest User"})
                data["userId"] = user_id
                
            chat = await prisma_client.chat.create(data=data)
            return chat
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Error creating chat in Supabase: {e}")
            raise RuntimeError(f"Database error during chat creation: {str(e)}")

    @staticmethod
    async def get_chat(chat_id: str):
        """Fetch chat metadata."""
        await connect_prisma()
        try:
            return await prisma_client.chat.find_unique(where={"id": chat_id})
        except Exception as e:
            logger.error(f"Error fetching chat by ID: {e}")
            return None

    @staticmethod
    async def delete_chat(chat_id: str):
        """Delete a chat and its cascade objects."""
        await connect_prisma()
        try:
            await prisma_client.chat.delete(where={"id": chat_id})
            return True
        except Exception as e:
            logger.error(f"Error deleting chat {chat_id}: {e}")
            return False

    @staticmethod
    async def add_message(chat_id: str, role: str, content: str, metadata: dict = None):
        """Add a conversation message history record."""
        await connect_prisma()
        try:
            # Ensure the chat exists
            await ChatRepository.create_chat(chat_id)
            
            data = {
                "chat": {"connect": {"id": chat_id}},
                "role": role,
                "content": content
            }
            if metadata is not None:
                data["metadata"] = Json(metadata)

            message = await prisma_client.message.create(data=data)
            return message
        except Exception as e:
            logger.error(f"Error adding message to chat {chat_id}: {e}")
            # Graceful fallback to avoid interrupting execution
            return None

    @staticmethod
    async def get_messages(chat_id: str):
        """Fetch messages for a specific chat."""
        await connect_prisma()
        try:
            return await prisma_client.message.find_many(
                where={"chatId": chat_id},
                order={"timestamp": "asc"}
            )
        except Exception as e:
            logger.error(f"Error getting messages for chat {chat_id}: {e}")
            return []

    @staticmethod
    async def list_chats(user_id: str = None):
        """List chats (newest first), optionally filtered by owner."""
        await connect_prisma()
        try:
            where = {"userId": user_id} if user_id else {}
            return await prisma_client.chat.find_many(
                where=where,
                order={"createdAt": "desc"}
            )
        except Exception as e:
            logger.error(f"Error listing chats: {e}")
            return []

    @staticmethod
    async def get_or_create_session(thread_id: str, user_id: str = None, chat_id: str = None):
        """Create or fetch session matching LangGraph thread_id."""
        await connect_prisma()
        try:
            session = await prisma_client.session.find_unique(where={"id": thread_id})
            if session:
                return session

            # If user_id is provided, check if user exists
            if user_id:
                user = await prisma_client.user.find_unique(where={"id": user_id})
                if not user:
                    await prisma_client.user.create(data={"id": user_id, "email": f"{user_id}@guest.com", "name": "Guest"})

            # Ensure the chat exists if chat_id is provided
            if chat_id:
                await ChatRepository.create_chat(chat_id, user_id)
                
            data = {"id": thread_id}
            if user_id:
                data["userId"] = user_id
            if chat_id:
                data["chatId"] = chat_id
                
            return await prisma_client.session.create(data=data)
        except Exception as e:
            logger.error(f"Error creating session mapping for thread {thread_id}: {e}")
            return None

    @staticmethod
    async def log_agent_action(thread_id: str, node_name: str, event_type: str, payload: dict, chat_id: str = None):
        """Log agent routing, decision, tool, or error payloads."""
        await connect_prisma()
        try:
            if chat_id:
                await ChatRepository.create_chat(chat_id)
            else:
                # Find matching session to retrieve chat_id
                session = await prisma_client.session.find_unique(where={"id": thread_id})
                if session and session.chatId:
                    chat_id = session.chatId
            
            data = {
                "threadId": thread_id,
                "nodeName": node_name,
                "eventType": event_type,
            }
            if payload is not None:
                data["payload"] = Json(payload)
            if chat_id:
                data["chat"] = {"connect": {"id": chat_id}}
                
            return await prisma_client.agentlog.create(data=data)
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Error logging agent action: {e}")
            return None

    @staticmethod
    async def save_safety_report(chat_id: str, approved: bool, confidence: float, issues: list, message_id: str = None):
        """Log the result of a safety agent check."""
        await connect_prisma()
        try:
            await ChatRepository.create_chat(chat_id)
            
            data = {
                "chat": {"connect": {"id": chat_id}},
                "approved": approved,
                "confidence": confidence
            }
            if issues is not None:
                data["issues"] = Json(issues)
            if message_id:
                data["message"] = {"connect": {"id": message_id}}
                
            return await prisma_client.safetyreport.create(data=data)
        except Exception as e:
            logger.error(f"Error saving safety report: {e}")
            return None

    @staticmethod
    async def save_conversation_summary(chat_id: str, summary: str):
        """Save chat summaries generated by LangGraph history summarization."""
        await connect_prisma()
        try:
            await ChatRepository.create_chat(chat_id)
            return await prisma_client.conversationsummary.create(
                data={
                    "chat": {"connect": {"id": chat_id}},
                    "summary": summary
                }
            )
        except Exception as e:
            logger.error(f"Error saving conversation summary: {e}")
            return None

    @staticmethod
    async def get_conversation_summary(chat_id: str):
        """Retrieve latest summary of the chat."""
        await connect_prisma()
        try:
            summaries = await prisma_client.conversationsummary.find_many(
                where={"chatId": chat_id},
                order={"timestamp": "desc"},
                take=1
            )
            return summaries[0] if summaries else None
        except Exception as e:
            logger.error(f"Error fetching summary: {e}")
            return None
