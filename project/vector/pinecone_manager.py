import os
import sys
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

try:
    from pinecone import Pinecone, ServerlessSpec
except ImportError:
    Pinecone = None
    ServerlessSpec = None

class PineconeManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(PineconeManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.api_key = settings.PINECONE_API_KEY
        self.index_name = settings.PINECONE_INDEX
        self.environment = settings.PINECONE_ENVIRONMENT

        self.pc = None
        self.index = None

        if self.api_key and Pinecone:
            try:
                self.pc = Pinecone(api_key=self.api_key)
                self._initialized = True
                logger.info("✓ Pinecone client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Pinecone Client: {e}")
        else:
            logger.warning("⚠️ PINECONE_API_KEY is not defined in settings. Vector DB operations will fail.")

    def _reinit_if_needed(self):
        """Re-attempt initialization if we previously had no API key."""
        if not self.pc:
            fresh_key = settings.PINECONE_API_KEY
            if fresh_key and Pinecone:
                self.api_key = fresh_key
                self.index_name = settings.PINECONE_INDEX
                self.environment = settings.PINECONE_ENVIRONMENT
                try:
                    self.pc = Pinecone(api_key=fresh_key)
                    self._initialized = True
                    logger.info("✓ Pinecone client initialized on retry.")
                except Exception as e:
                    logger.error(f"Failed to initialize Pinecone Client on retry: {e}")

    def get_index(self, dimension: int = 1536):
        """Get or automatically create a Pinecone index of the required dimension."""
        self._reinit_if_needed()
        if not self.pc:
            raise RuntimeError("Pinecone client is not initialized. Please verify your PINECONE_API_KEY.")

        try:
            # Check if index exists
            indexes = [idx.name for idx in self.pc.list_indexes()]
            
            if self.index_name not in indexes:
                logger.info(f"Pinecone index '{self.index_name}' not found. Creating index automatically...")
                
                # Setup serverless spec
                spec = ServerlessSpec(
                    cloud="aws",
                    region=self.environment or "us-east-1"
                )
                
                self.pc.create_index(
                    name=self.index_name,
                    dimension=dimension,
                    metric="cosine",
                    spec=spec
                )
                logger.info(f"✓ Pinecone index '{self.index_name}' created successfully.")
                
            self.index = self.pc.Index(self.index_name)
            return self.index
        except Exception as e:
            logger.error(f"Error accessing or creating Pinecone index: {e}")
            raise RuntimeError(f"Pinecone service unavailable: {str(e)}")
            
    def check_connection(self) -> bool:
        """Check if Pinecone is available and connected."""
        self._reinit_if_needed()
        if not self.pc:
            return False
        try:
            self.pc.list_indexes()
            return True
        except Exception as e:
            logger.error(f"Pinecone connection check failed: {e}")
            return False

