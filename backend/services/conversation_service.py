import asyncio

from repositories.chat_repository import ChatRepository


class ConversationService:

    @staticmethod
    async def get_history(session_id: str) -> tuple[list, str | None]:
        messages = await ChatRepository.get_messages(session_id)
        summary_record = await ChatRepository.get_conversation_summary(session_id)
        summary = summary_record.summary if summary_record else None
        return messages, summary

    @staticmethod
    async def list_conversations(user_id: str | None):
        return await ChatRepository.list_chats(user_id)

    @staticmethod
    async def delete_conversation(rag_system, session_id: str) -> bool:
        deleted = await ChatRepository.delete_chat(session_id)
        checkpointer = getattr(rag_system.agent_graph, "checkpointer", None)
        if checkpointer is not None:
            try:
                await checkpointer.adelete_thread(session_id)
            except AttributeError:
                try:
                    await asyncio.to_thread(checkpointer.delete_thread, session_id)
                except Exception as e:
                    print(f"Warning: Could not delete thread {session_id}: {e}")
            except Exception as e:
                print(f"Warning: Could not delete thread {session_id}: {e}")
        return deleted
