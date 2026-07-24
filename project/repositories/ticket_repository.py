from database.supabase_client import prisma_client, connect_prisma
import logging

logger = logging.getLogger(__name__)

class TicketRepository:
    @staticmethod
    async def create_ticket(issue: str, customer_email: str, user_id: str = None, chat_id: str = None):
        """Create a support ticket record in Supabase using Prisma."""
        await connect_prisma()
        try:
            # Ensure the user exists if user_id is provided
            if user_id:
                user = await prisma_client.user.find_unique(where={"id": user_id})
                if not user:
                    await prisma_client.user.create(data={"id": user_id, "email": customer_email, "name": "Guest"})

            # Ensure the chat exists if chat_id is provided
            if chat_id:
                # ChatRepository dependency is inline here
                existing_chat = await prisma_client.chat.find_unique(where={"id": chat_id})
                if not existing_chat:
                    chat_data = {"id": chat_id}
                    if user_id:
                        chat_data["userId"] = user_id
                    await prisma_client.chat.create(data=chat_data)

            data = {
                "issue": issue,
                "customerEmail": customer_email,
                "status": "open"
            }
            if user_id:
                data["user"] = {"connect": {"id": user_id}}
            if chat_id:
                data["chat"] = {"connect": {"id": chat_id}}

            ticket = await prisma_client.ticket.create(data=data)
            return ticket
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            raise RuntimeError(f"Database error during ticket creation: {str(e)}")

    @staticmethod
    async def get_ticket(ticket_id: int):
        """Fetch a ticket by numerical ID."""
        await connect_prisma()
        try:
            return await prisma_client.ticket.find_unique(where={"id": ticket_id})
        except Exception as e:
            logger.error(f"Error fetching ticket {ticket_id}: {e}")
            return None

    @staticmethod
    async def list_tickets():
        """Retrieve all support tickets."""
        await connect_prisma()
        try:
            return await prisma_client.ticket.find_many(order={"createdAt": "desc"})
        except Exception as e:
            logger.error(f"Error listing tickets: {e}")
            return []
