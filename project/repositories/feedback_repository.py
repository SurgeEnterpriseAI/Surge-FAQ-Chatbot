from database.supabase_client import prisma_client, connect_prisma
import logging

logger = logging.getLogger(__name__)

class FeedbackRepository:
    @staticmethod
    async def add_feedback(chat_id: str, rating: int, comment: str = None, user_id: str = None):
        """Submit a rating and comment for a chat session."""
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
                "rating": rating,
                "comment": comment
            }
            if user_id:
                data["user"] = {"connect": {"id": user_id}}

            feedback = await prisma_client.feedback.create(data=data)
            return feedback
        except Exception as e:
            logger.error(f"Error saving feedback: {e}")
            raise RuntimeError(f"Database error during feedback submission: {str(e)}")

    @staticmethod
    async def get_feedback_by_chat(chat_id: str):
        """Fetch all feedback associated with a chat."""
        await connect_prisma()
        try:
            return await prisma_client.feedback.find_many(where={"chatId": chat_id})
        except Exception as e:
            logger.error(f"Error fetching feedback for chat {chat_id}: {e}")
            return []
