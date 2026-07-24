from database.supabase_client import prisma_client, connect_prisma
import logging

logger = logging.getLogger(__name__)

class UserRepository:
    @staticmethod
    async def create_user(user_id: str, email: str, name: str = None):
        """Create a new user record in Supabase using Prisma."""
        try:
            await connect_prisma()
            if prisma_client and prisma_client.is_connected():
                existing = await prisma_client.user.find_unique(where={"id": user_id})
                if existing:
                    return existing
                    
                user = await prisma_client.user.create(
                    data={
                        "id": user_id,
                        "email": email,
                        "name": name
                    }
                )
                return user
        except Exception as e:
            logger.warning(f"Database error during user creation: {e}")
        return None

    @staticmethod
    async def get_user(user_id: str):
        """Retrieve user profile by ID."""
        try:
            await connect_prisma()
            if prisma_client and prisma_client.is_connected():
                return await prisma_client.user.find_unique(where={"id": user_id})
        except Exception as e:
            logger.warning(f"Database error fetching user by ID: {e}")
        return None

    @staticmethod
    async def get_user_by_email(email: str):
        """Retrieve user profile by email address."""
        try:
            await connect_prisma()
            if prisma_client and prisma_client.is_connected():
                return await prisma_client.user.find_unique(where={"email": email})
        except Exception as e:
            logger.warning(f"Database error fetching user by email: {e}")
        return None
