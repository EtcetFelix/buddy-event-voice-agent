"""
RAG retrieval system for Buddy's knowledge base.
Retrieves relevant context from ChromaDB to augment LLM responses.
"""

import logging
from pathlib import Path
from typing import Optional

import chromadb

logger = logging.getLogger("rag")


class BuddyRAG:
    """
    Retrieves relevant context from Buddy's knowledge base stored in ChromaDB.
    """
    
    def __init__(self, chroma_path: Optional[str] = None, top_k: int = 3):
        """
        Initialize the RAG retriever.
        
        Args:
            chroma_path: Path to ChromaDB storage. Defaults to ./chroma_db
            top_k: Number of chunks to retrieve per query
        """
        if chroma_path is None:
            # Default to project root's chroma_db folder
            project_root = Path(__file__).parent.parent
            chroma_path = str(project_root / "chroma_db")
        
        self.top_k = top_k
        self.chroma_path = chroma_path
        
        try:
            self.client = chromadb.PersistentClient(path=chroma_path)
            self.collection = self.client.get_collection("buddy_knowledge")
            chunk_count = self.collection.count()
            logger.info(f"🐕 RAG initialized with {chunk_count} chunks from {chroma_path}")
        except Exception as e:
            logger.error(f"Failed to initialize RAG: {e}")
            logger.error("Make sure to run 'python scripts/setup_vector_store.py' first!")
            raise
    
    def retrieve(self, query: str, top_k: Optional[int] = None) -> str:
        """
        Retrieve relevant context for a query.
        
        Args:
            query: The user's message or question
            top_k: Override default top_k for this query
            
        Returns:
            Formatted string with retrieved context, or empty string if no results
        """
        k = top_k if top_k is not None else self.top_k
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=k
            )
            
            # Check if we got results
            if not results['documents'] or not results['documents'][0]:
                logger.debug(f"No RAG results found for query: {query[:50]}...")
                return ""
            
            # Format retrieved documents
            docs = results['documents'][0]
            metadatas = results['metadatas'][0] if 'metadatas' in results else [{}] * len(docs)
            
            logger.info(f"RAG Query: '{query}'")
            for i, (doc, meta) in enumerate(zip(docs, metadatas), 1):
                logger.info(f"  Chunk {i} (page {meta.get('page', '?')}): {doc[:100]}...")
            
            # Build context string - simple and clean for the LLM
            context_parts = [doc.strip() for doc in docs]
            context = "\n\n".join(context_parts)
            
            logger.debug(f"Retrieved {len(docs)} chunks for query: {query[:50]}...")
            return context
            
        except Exception as e:
            logger.error(f"RAG retrieval error: {e}")
            return ""


# Singleton instance for easy import
_rag_instance: Optional[BuddyRAG] = None


def get_rag(top_k: int = 3) -> BuddyRAG:
    """
    Get or create the singleton RAG instance.
    Useful for avoiding multiple ChromaDB connections.
    """
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = BuddyRAG(top_k=top_k)
    return _rag_instance