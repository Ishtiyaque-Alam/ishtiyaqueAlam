import os
import time
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import chromadb
from dotenv import load_dotenv
# -----------------------
# CONFIG
# -----------------------
load_dotenv()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "analysis_output\chroma_db")

# -----------------------
# Topic Node with Memory
# -----------------------
class ShortTermMemory:
    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.buffer: List[Dict[str, str]] = []

    def add_turn(self, user_text: str, assistant_text: str):
        self.buffer.append({"user": user_text, "assistant": assistant_text})
        if len(self.buffer) > self.window_size:
            self.buffer.pop(0)

    def get_context(self) -> str:
        if not self.buffer:
            return "<none>"
        return "\n".join(
            [f"USER: {t['user']}\nASSISTANT: {t['assistant']}" for t in self.buffer]
        )


class TopicNode:
    def __init__(self, topic_id: str, query: str, embedding: np.ndarray, chunks: List[Dict[str, Any]]):
        self.topic_id = topic_id
        self.query = query
        self.embedding = embedding
        self.chunks = chunks
        self.created_at = time.time()
        self.memory = ShortTermMemory(window_size=10)


# -----------------------
# Retriever
# -----------------------
class TopicSwitchingRetriever:
    def __init__(self, chroma_manager, threshold: float = 0.6):
        self.chroma_manager = chroma_manager
        self.client = chroma_manager.client
        self.collection = chroma_manager.code_collection
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)
        self.topics: Dict[str, TopicNode] = {}
        self.active_topic: TopicNode = None
        self.threshold = threshold

    def _embed(self, text: str) -> np.ndarray:
        return self.embedder.encode(text, convert_to_numpy=True)

    def retrieve(self, query: str, n_results: int = 2) -> Dict[str, Any]:
        q_emb = self._embed(query)

        # Compare with existing topics
        best_sim, best_topic = -1.0, None
        for t in self.topics.values():
            sim = float(np.dot(q_emb, t.embedding) / (np.linalg.norm(q_emb) * np.linalg.norm(t.embedding)))
            
            if sim > best_sim:
                best_sim, best_topic = sim, t

        if best_topic and best_sim >= self.threshold:
            self.active_topic = best_topic
            return {"topic_id": best_topic.topic_id, "chunks": best_topic.chunks, "reused": True}

        # New topic → query ChromaDB

        results = self.collection.query(query_texts=[query], n_results=n_results)
        docs = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        chunks = [{"document": d, "metadata": m} for d, m in zip(docs, metadatas)]

        topic_id = f"topic_{len(self.topics)+1}"
        new_topic = TopicNode(topic_id, query, q_emb, chunks)
        self.topics[topic_id] = new_topic
        self.active_topic = new_topic

        return {"topic_id": topic_id, "chunks": chunks, "reused": False}


if __name__=="__main__":
    retriever = TopicSwitchingRetriever()
    queries = [
        "How to visualize the dependency graph?",
        "How to build the dependency graph?",
        "How to improve it?",
        "How to parse Python files?",
        "How to build the dependency graph?",
    ]
    for q in queries:
        res = retriever.retrieve(q)
        print(f"Query: {q}\nTopic: {res['topic_id']} (reused: {res['reused']})\nChunks: {len(res['chunks'])}\n---similarity: {res.get('similarity', None)}\n")