import os
import json
import logging
from typing import List, Dict, Any
from uuid import uuid4
from dotenv import load_dotenv

import google.generativeai as genai
from langchain_chroma import Chroma
from langchain.schema import Document

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from src.qa_agent.debugger_agent import DebuggerAgent
from src.vector_db.chroma_manager import ChromaManager

logger = logging.getLogger("conv_bot")

load_dotenv()
EMBEDDINGS = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


class ConversationalBot:
    def __init__(
        self,
        api_key: str=GEMINI_API_KEY,
        persist_dir: str = "chat_memory",
        planner_model: str = "gemini-2.5-flash",
        engineer_model: str = "gemini-2.5-flash",
        embedding_model: str = EMBEDDINGS,
        confidence_threshold: float = 0.6,
        debugger_agent: DebuggerAgent = None,
        chroma_manager: ChromaManager = None,
    ):
        # Configure Gemini
        genai.configure(api_key=api_key)

        # LLMs
        self.planner = genai.GenerativeModel(planner_model)
        self.engineer = genai.GenerativeModel(engineer_model)

        # Embeddings + VectorStore (chat memory)
        self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
        self.vectorstore = Chroma(
            persist_directory=persist_dir, embedding_function=self.embeddings
        )

        self.confidence_threshold = confidence_threshold
        self.debugger_agent = debugger_agent
        self.chroma_manager = chroma_manager

    # -------------------------
    # Store turns into VDB
    # -------------------------
    def save_turn_to_vdb(self, role: str, content: str):
        doc_id = str(uuid4())
        self.vectorstore.add_texts(
            texts=[f"{role}: {content}"],
            ids=[doc_id],
            metadatas=[{"role": role}]
        )

    # -------------------------
    # Planner
    # -------------------------
    def planner_restructure(self, query: str, last_chats: List[str]) -> dict:
        prompt = f"""
        You are a reasoning and planning assistant.

Inputs:
- Query: {query}
- Last chats: {last_chats}

Your task:
1. Decide if the last chats provide enough information to fully and literally answer the current query.
   - "Enough" means the answer can be derived using the chats or by using your external knowledge.
2. If enough:
   - Provide the answer directly.
   - Output only valid JSON:
     {{
       "enough": true,
       "response": "<your answer>"
     }}
3. If not enough:
   - Rewrite the query into a clear, self-contained question that can be used for retrieval in a vector database.
   - Output only valid JSON:
     {{
       "enough": false,
       "new_query": "<rewritten query>"
     }}
        """
        resp = self.planner.generate_content(
            prompt, generation_config={"response_mime_type": "application/json"}
        )
        try:
            return json.loads(resp.text)
        except Exception as e:
            raise ValueError(f"Planner failed to return valid JSON: {resp.text}") from e

    # -------------------------
    # Retrieval from chat memory
    # -------------------------
    def retrieve_from_chat_memory(self, query: str):
        docs_with_scores = self.vectorstore.similarity_search_with_score(query, k=5)
        if not docs_with_scores:
            return [], 0.0

        docs, scores = zip(*docs_with_scores)
        best_score = min(scores)  # lower distance = better match
        confidence = 1 - best_score
        return list(docs), confidence

    # -------------------------
    # Retrieval from main DB
    # -------------------------
    def fetch_from_main_db(self, query: str) -> List[Document]:
        if not self.chroma_manager:
            return [Document(page_content="(No main DB configured)")]
        search = self.chroma_manager.search_code(query, n_results=3)
        docs = []
        for s in search:
            docs.append(Document(page_content=s['document'], metadata=s['metadata']))
        return docs

    # -------------------------
    # Engineer Answer
    # -------------------------
    def engineer_answer(self, query: str, chat_docs: List[Document], context_docs: List[Document]) -> str:
        chat_history = (
            "\n".join([doc.page_content for doc in chat_docs])
            if chat_docs else "No relevant chat history found."
        )
        context_text = (
            "\n".join([doc.page_content for doc in context_docs])
            if context_docs else "No external context found."
        )

        prompt = f"""
        You are the engineer LLM.
        Query: {query}

        Conversation history (from chat memory):
        {chat_history}

        Context (from DB):
        {context_text}

        Answer the query concisely and accurately.
        """
        resp = self.engineer.generate_content(prompt)
        return resp.text.strip()

    # -------------------------
    # Handle Query
    # -------------------------
    def handle_query(self, user_query: str) -> str:
        # Debugger path
        if "think" in user_query.lower() and self.debugger_agent:
            logger.info("Routing to DebuggerAgent...")
            debug_result = self.debugger_agent.run(user_query)
            if not debug_result:
                return "DebuggerAgent could not resolve the issue."
            answer = f"DebuggerAgent says:\nAnalysis: {debug_result['analysis']}\nFix: {debug_result['fix']}"
            self.save_turn_to_vdb("user", user_query)
            self.save_turn_to_vdb("bot", answer)
            return answer

        # Use planner with last few chats from memory
        chat_history_docs, _ = self.retrieve_from_chat_memory(user_query)
        last_chats = [doc.page_content for doc in chat_history_docs[-5:]]
        planner_result = self.planner_restructure(user_query, last_chats)

        if planner_result.get("enough"):
            answer = planner_result["response"]
        else:
            new_query = planner_result["new_query"]

            # Step 1: Try retrieving from chat memory
            chat_docs, confidence = self.retrieve_from_chat_memory(new_query)

            if confidence < self.confidence_threshold:
                # Step 2: Fallback to main DB
                context_docs = self.fetch_from_main_db(new_query)
            else:
                context_docs = []

            answer = self.engineer_answer(new_query, chat_docs, context_docs)

        # Save to chat memory VDB
        self.save_turn_to_vdb("user", user_query)
        self.save_turn_to_vdb("bot", answer)
        return answer


# -------------------------
# Example Usage
# -------------------------
# if __name__ == "__main__":
#     llm = LLMClient()
#     planner = Planner(llm)
#     chroma_manager = ChromaManager()
#     analyzer = DebugMain(llm)
#     debugger_agent = DebuggerAgent(planner, chroma_manager, analyzer)

#     bot = ConversationalBot(api_key=GEMINI_API_KEY, debugger_agent=debugger_agent, chroma_manager=chroma_manager)

#     print("ConversationalBot CLI. Type 'exit' to quit.")
#     while True:
#         try:
#             user_query = input("You: ").strip()
#             if user_query.lower() in ("exit", "quit"):
#                 break
#             response = bot.handle_query(user_query)
#             print(f"Bot: {response}\n")
#         except (KeyboardInterrupt, EOFError):
#             print("\nExiting chat.")
#             break
