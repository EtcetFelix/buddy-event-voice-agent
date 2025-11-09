"""
Interactive script to test RAG retrieval.
Tests ChromaDB queries before integrating with the voice agent.

Usage:
    python scripts/test_rag.py
"""

import chromadb
from pathlib import Path
from typing import List, Dict

class RAGTester:
    def __init__(self):
        project_root = Path(__file__).parent.parent
        chroma_path = project_root / 'chroma_db'
        
        if not chroma_path.exists():
            raise FileNotFoundError(
                "ChromaDB not found! Run 'python scripts/setup_vector_store.py' first"
            )
        
        self.client = chromadb.PersistentClient(path=str(chroma_path))
        self.collection = self.client.get_collection("buddy_knowledge")
        
        # Get collection stats
        count = self.collection.count()
        print(f"🐕 Connected to Buddy's knowledge base ({count} chunks)\n")
    
    def query(self, text: str, top_k: int = 3) -> List[Dict]:
        """Query the vector store and return results."""
        results = self.collection.query(
            query_texts=[text],
            n_results=top_k
        )
        
        # Format results
        formatted = []
        for i, (doc, metadata) in enumerate(zip(
            results['documents'][0], 
            results['metadatas'][0]
        )):
            formatted.append({
                'rank': i + 1,
                'text': doc,
                'page': metadata.get('page', 'unknown'),
                'distance': results['distances'][0][i] if 'distances' in results else None
            })
        
        return formatted
    
    def print_results(self, results: List[Dict]):
        """Pretty print query results."""
        for result in results:
            print(f"\n{'='*80}")
            print(f"Rank #{result['rank']} | Page {result['page']}", end="")
            if result['distance'] is not None:
                print(f" | Distance: {result['distance']:.3f}")
            else:
                print()
            print(f"{'='*80}")
            print(result['text'])
        print(f"\n{'='*80}\n")
    
    def interactive_mode(self):
        """Run interactive query loop."""
        print("🔍 Interactive RAG Testing")
        print("Type your queries (or 'quit' to exit)\n")
        
        while True:
            try:
                query_text = input("Query: ").strip()
                
                if not query_text:
                    continue
                
                if query_text.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                # Parse optional top_k parameter
                top_k = 3
                if query_text.startswith('/k='):
                    try:
                        parts = query_text.split(' ', 1)
                        top_k = int(parts[0][3:])
                        query_text = parts[1] if len(parts) > 1 else ""
                    except:
                        print("Invalid /k= syntax. Use: /k=5 your query here")
                        continue
                
                results = self.query(query_text, top_k=top_k)
                self.print_results(results)
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}\n")
    
    def run_sample_queries(self):
        """Run predefined test queries."""
        print("🧪 Running sample test queries...\n")
        
        test_queries = [
            "What is Buddy's backstory?",
            "Tell me about the Mission District",
            "What events are happening in November?",
            "What's Buddy's personality like?",
            "Tell me about outdoor activities in SF"
        ]
        
        for query in test_queries:
            print(f"📝 Query: '{query}'")
            results = self.query(query, top_k=2)
            
            # Just show first result
            if results:
                print(f"   ✓ Top result (page {results[0]['page']}): {results[0]['text'][:150]}...")
            else:
                print("   ✗ No results found")
            print()

def main():
    import sys
    
    tester = RAGTester()
    
    # Check for --samples flag
    if '--samples' in sys.argv:
        tester.run_sample_queries()
    else:
        tester.interactive_mode()

if __name__ == "__main__":
    main()