from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Float, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
import sys

# Ensure project path is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from supabase import create_client, Client
from prisma import Prisma

# Initialize Supabase client
supabase_url = settings.SUPABASE_URL
supabase_key = settings.SUPABASE_KEY
supabase_client: Client = None

if supabase_url and supabase_key:
    try:
        supabase_client = create_client(supabase_url, supabase_key)
    except Exception as e:
        print(f"WARNING: Error initializing Supabase client: {e}")

# Initialize Prisma client
prisma_client = Prisma(
    http={
        "timeout": 60.0
    }
)

# SQLAlchemy Setup
DATABASE_URL = settings.DATABASE_URL

# Strip pgBouncer-specific params that psycopg2 doesn't understand;
# those params are needed only for Prisma's connection string.
_SQLA_URL = DATABASE_URL
if _SQLA_URL:
    from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
    _parsed = urlparse(_SQLA_URL)
    _qs = parse_qs(_parsed.query, keep_blank_values=True)
    _qs.pop("pgbouncer", None)
    _qs.pop("prepared_statements", None)
    _new_query = urlencode({k: v[0] for k, v in _qs.items()})
    _SQLA_URL = urlunparse(_parsed._replace(query=_new_query))

# Replace postgresql:// with postgresql+psycopg2:// if needed
if _SQLA_URL and _SQLA_URL.startswith("postgresql://") and not _SQLA_URL.startswith("postgresql+psycopg2://"):
    _SQLA_URL = _SQLA_URL.replace("postgresql://", "postgresql+psycopg2://")

engine = None
SessionLocal = None
Base = declarative_base()

if _SQLA_URL:
    try:
        # Use a modest pool — Supabase pgBouncer has a max connection cap
        engine = create_engine(
            _SQLA_URL,
            pool_size=5,
            max_overflow=10,
            pool_recycle=300,
            pool_pre_ping=True,
            # Disable server-side prepared statements so pgBouncer transaction
            # mode doesn't produce "prepared statement already exists" errors.
            connect_args={"options": "-c statement_timeout=30000"},
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    except Exception as e:
        print(f"WARNING: Error initializing SQLAlchemy engine: {e}")

# Define SQLAlchemy ORM Models
class UserModel(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatModel(Base):
    __tablename__ = "chats"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class MessageModel(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True)
    chat_id = Column(String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    msg_metadata = Column("metadata", JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class SessionModel(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True)  # maps to thread_id
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    chat_id = Column(String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FeedbackModel(Base):
    __tablename__ = "feedback"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    chat_id = Column(String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class TicketModel(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    chat_id = Column(String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=True)
    issue = Column(Text, nullable=False)
    status = Column(String, default="open")
    customer_email = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class EscalationModel(Base):
    __tablename__ = "escalations"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    chat_id = Column(String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

class SafetyReportModel(Base):
    __tablename__ = "safety_reports"
    id = Column(String, primary_key=True)
    chat_id = Column(String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(String, ForeignKey("messages.id", ondelete="CASCADE"), nullable=True)
    approved = Column(Boolean, nullable=False)
    confidence = Column(Float, nullable=False)
    issues = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class AgentLogModel(Base):
    __tablename__ = "agent_logs"
    id = Column(String, primary_key=True)
    chat_id = Column(String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=True)
    thread_id = Column(String, nullable=False)
    node_name = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class ConversationSummaryModel(Base):
    __tablename__ = "conversation_summaries"
    id = Column(String, primary_key=True)
    chat_id = Column(String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    summary = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

class DocumentModel(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True)
    filename = Column(String, unique=True, nullable=False)
    chunk_count = Column(Integer, default=0)
    status = Column(String, default="pending")
    doc_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ParentChunkModel(Base):
    __tablename__ = "parent_chunks"
    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, nullable=False)
    chunk_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    if SessionLocal is None:
        raise RuntimeError("SQLAlchemy SessionLocal is not initialized. Check your DATABASE_URL.")
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        raise e

import asyncio
import logging

logger = logging.getLogger(__name__)

_prisma_locks = {}
prisma_loop = None
prisma_main_loop = None

def get_prisma_lock():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop not in _prisma_locks:
        _prisma_locks[loop] = asyncio.Lock()
    return _prisma_locks[loop]

async def connect_prisma():
    global prisma_loop, prisma_main_loop
    if prisma_client is None:
        return
    try:
        current_loop = asyncio.get_running_loop()
        lock = get_prisma_lock()

        async with lock:
            if prisma_main_loop is None:
                prisma_main_loop = current_loop

            if prisma_client.is_connected():
                return

            # Connecting to Supabase/pgBouncer can transiently fail while the
            # server is still warming up. Retry once with a short backoff so the
            # first request after boot isn't served against a disconnected
            # client (which would otherwise degrade or error intermittently).
            last_error = None
            for attempt in range(2):
                try:
                    await prisma_client.connect()
                    prisma_loop = current_loop
                    return
                except Exception as e:  # noqa: BLE001
                    last_error = e
                    if attempt == 0:
                        await asyncio.sleep(0.5)
            raise last_error
    except Exception as e:
        logger.warning("Prisma database connection could not be established: %s", e)

async def disconnect_prisma():
    lock = get_prisma_lock()
    async with lock:
        if prisma_client.is_connected():
            await prisma_client.disconnect()


