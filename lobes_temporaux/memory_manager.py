import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from datetime import datetime
from typing import List, Dict, Any

class MemoryManager:
    def __init__(self):
        # Client ChromaDB local
        self.client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Modèle d'embeddings français
        self.embedder = SentenceTransformer('distiluse-base-multilingual-cased-v2')
        
        # Collections
        self.user_profile = self.client.get_or_create_collection("user_profile")
        self.conversations = self.client.get_or_create_collection("conversations")
        
    async def store_conversation(self, role: str, user_msg: str, assistant_msg: str):
        """Stocke une conversation avec contexte"""
        timestamp = datetime.now().isoformat()
        
        # Créer embedding du contenu
        embedding = self.embedder.encode(f"{user_msg} {assistant_msg}")
        
        self.conversations.add(
            embeddings=[embedding.tolist()],
            documents=[assistant_msg],
            metadatas=[{
                "role": role,
                "user_msg": user_msg,
                "timestamp": timestamp
            }],
            ids=[f"conv_{timestamp}"]
        )
    
    async def get_relevant_context(self, query: str, role: str = None, limit: int = 3):
        """Récupère le contexte pertinent"""
        embedding = self.embedder.encode(query)
        
        where_clause = {"role": role} if role else None
        
        results = self.conversations.query(
            query_embeddings=[embedding.tolist()],
            n_results=limit,
            where=where_clause
        )
        
        return results