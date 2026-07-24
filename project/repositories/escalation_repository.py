from database.supabase_client import prisma_client, connect_prisma
import logging

logger = logging.getLogger(__name__)

class EscalationRepository:
    @staticmethod
    async def create_escalation(chat_id: str, reason: str, user_id: str = None):
        """Create a human escalation log record in Supabase."""
        await connect_prisma()
        try:
            # Ensure the user exists if user_id is provided
            if user_id:
                user = await prisma_client.user.find_unique(where={"id": user_id})
                if not user:
                    await prisma_client.user.create(data={"id": user_id, "email": f"{user_id}@guest.com", "name": "Guest"})

            # Ensure the chat exists
            existing_chat = await prisma_client.chat.find_unique(where={"id": chat_id})
            if not existing_chat:
                chat_data = {"id": chat_id}
                if user_id:
                    chat_data["userId"] = user_id
                await prisma_client.chat.create(data=chat_data)

            data = {
                "chat": {"connect": {"id": chat_id}},
                "reason": reason,
                "status": "pending"
            }
            if user_id:
                data["user"] = {"connect": {"id": user_id}}

            escalation = await prisma_client.escalation.create(data=data)
            return escalation
        except Exception as e:
            logger.error(f"Error creating escalation record: {e}")
            raise RuntimeError(f"Database error during human handoff log: {str(e)}")

    @staticmethod
    async def get_escalation(escalation_id: str):
        """Fetch a specific escalation profile by ID."""
        await connect_prisma()
        try:
            return await prisma_client.escalation.find_unique(where={"id": escalation_id})
        except Exception as e:
            logger.error(f"Error fetching escalation {escalation_id}: {e}")
            return None

    @staticmethod
    async def list_escalations():
        """Retrieve all active/inactive escalations."""
        await connect_prisma()
        try:
            return await prisma_client.escalation.find_many(order={"createdAt": "desc"})
        except Exception as e:
            logger.error(f"Error listing escalations: {e}")
            return []
