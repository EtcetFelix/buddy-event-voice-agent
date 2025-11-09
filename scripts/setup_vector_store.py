"""
One-time script to chunk PDF and load into ChromaDB.
Run this once after cloning the repo or when updating the knowledge base.

Usage:
    python scripts/setup_vector_store.py
"""

import chromadb
from pathlib import Path
from pypdf import PdfReader
from typing import List, Dict

def extract_text_from_pdf(pdf_path: Path) -> List[Dict[str, any]]:
    """
    Extract text from PDF, keeping track of page numbers.
    Returns list of dicts with 'text' and 'page' keys.
    """
    reader = PdfReader(pdf_path)
    documents = []
    
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text.strip():  # Only add non-empty pages
            documents.append({
                'text': text,
                'page': page_num
            })
    
    print(f"📄 Extracted text from {len(documents)} pages")
    return documents

def chunk_text(documents: List[Dict], chunk_size: int = 500, overlap: int = 50) -> List[Dict]:
    """
    Split documents into chunks with overlap.
    Preserves metadata (page numbers).
    """
    chunks = []
    chunk_id = 0
    
    for doc in documents:
        text = doc['text']
        page = doc['page']
        
        # Simple character-based chunking
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for last period, question mark, or exclamation
                last_sentence = max(
                    chunk_text.rfind('. '),
                    chunk_text.rfind('? '),
                    chunk_text.rfind('! ')
                )
                if last_sentence > chunk_size * 0.5:  # Only if we find one in latter half
                    chunk_text = chunk_text[:last_sentence + 1]
                    end = start + last_sentence + 1
            
            chunks.append({
                'text': chunk_text.strip(),
                'page': page,
                'id': f"chunk_{chunk_id}"
            })
            
            chunk_id += 1
            start = end - overlap  # Overlap for context continuity
    
    print(f"✂️  Created {len(chunks)} chunks (avg {sum(len(c['text']) for c in chunks) // len(chunks)} chars/chunk)")
    return chunks

def setup_chroma(force_recreate: bool = False):
    """
    Main setup function: load PDF, chunk, and store in ChromaDB.
    """
    print("🐕 Setting up Buddy's knowledge base...\n")
    
    # Paths
    project_root = Path(__file__).parent.parent
    pdf_path = project_root / 'data' / 'All_about_buddy.pdf'
    chroma_path = project_root / 'chroma_db'
    
    # Validate PDF exists
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found at {pdf_path}")
    
    # Extract text from PDF
    documents = extract_text_from_pdf(pdf_path)
    
    # Chunk the text
    chunks = chunk_text(documents, chunk_size=800, overlap=100)
    
    # Initialize ChromaDB
    client = chromadb.PersistentClient(path=str(chroma_path))
    
    # Delete existing collection if force recreate
    if force_recreate:
        try:
            client.delete_collection("buddy_knowledge")
            print("🗑️  Deleted existing collection")
        except Exception:
            pass
    
    # Create collection
    collection = client.get_or_create_collection(
        name="buddy_knowledge",
        metadata={"description": "Buddy's backstory, personality, and SF knowledge"}
    )
    
    # Add chunks to collection
    collection.add(
        documents=[chunk['text'] for chunk in chunks],
        metadatas=[{'page': chunk['page']} for chunk in chunks],
        ids=[chunk['id'] for chunk in chunks]
    )
    
    print(f"✅ Successfully loaded {len(chunks)} chunks into ChromaDB")
    print(f"📍 Vector store saved to: {chroma_path}\n")
    
    # Quick validation query
    print("🔍 Testing retrieval with sample query...")
    results = collection.query(
        query_texts=["Tell me about Buddy's personality"],
        n_results=2
    )
    print(f"   Found {len(results['documents'][0])} relevant chunks")
    print(f"   Sample: {results['documents'][0][0][:100]}...\n")
    
    print("🎉 Setup complete! You can now run the agent.")

if __name__ == "__main__":
    import sys
    
    # Optional: pass --force to recreate the collection
    force = '--force' in sys.argv
    
    try:
        setup_chroma(force_recreate=force)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)