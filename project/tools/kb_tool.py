from db.vector_db_manager import VectorDbManager
import config

def search_kb(query: str) -> str:
    """Search the knowledge base for documentation about a topic or issue.
    
    Args:
        query: Search keywords or query.
    """
    if not query:
        return "Error: Search query is required."
    try:
        vector_db = VectorDbManager()
        collection = vector_db.get_collection(config.CHILD_COLLECTION)
        results = collection.similarity_search(
            query, 
            k=3, 
            score_threshold=config.RETRIEVAL_SCORE_THRESHOLD
        )
        if not results:
            return "No relevant information found in the knowledge base."
        
        formatted_results = []
        for i, doc in enumerate(results, 1):
            source = doc.metadata.get("source", "Unknown")
            formatted_results.append(f"[{i}] Source: {source}\nContent: {doc.page_content.strip()}")
        return "\n\n".join(formatted_results)
    except Exception as e:
        return f"Error searching knowledge base: {str(e)}"
