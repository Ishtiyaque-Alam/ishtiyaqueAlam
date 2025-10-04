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
        confidence_threshold: float = 0.5,
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
            embedding_function=self.embeddings
        )

        self.confidence_threshold = confidence_threshold
        self.debugger_agent = debugger_agent
        self.chroma_manager = chroma_manager
        self.chat_window = []
    # -------------------------
    # Store turns into VDB
    # -------------------------
    def save_turn_to_vdb(self, role: str, content: str=None,docs: List[Document]=None):
        doc_id = str(uuid4())
        if role == "context":
            for doc in docs:
                self.vectorstore.add_texts(
                    texts=[doc.page_content],
                    ids=[str(uuid4())],
                    metadatas=[{"role": role}]
                )
            return
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
You are an expert AI assistant specializing in **technical query analysis** and **code conversation contextualization**.

Your goal is to determine if a user's query about a **programming topic, code snippet, or error message** can be answered directly using the `last_chats` history. If not, you will rewrite the query into a standalone, searchable technical question.

Follow these rules:
1.  Analyze the `query` in the context of the `last_chats`, paying close attention to any code snippets, libraries, or error messages mentioned.
2.  **If the chat history provides enough context to directly answer the query**, output a JSON object with `"enough": true` and the complete technical answer in the `"response"` field.
3.  **If the query is a follow-up that requires external information not present in the chats**, rewrite it into a clear, self-contained technical question. Output a JSON object with `"enough": false` and the new question in the `"new_query"` field.
4.  Your entire output must be a single, valid JSON object and nothing else.

---
**Examples:**

**Example 1: The answer can be found in the provided code snippet.**
* **last_chats:** "User: How can I create a simple web server in Python? \n Assistant: You can use the `http.server` module. Here's a basic example: \n```python\nimport http.server\nimport socketserver\n\nPORT = 8000\nHandler = http.server.SimpleHTTPRequestHandler\n\nwith socketserver.TCPServer(('', PORT), Handler) as httpd:\n    print('serving at port', PORT)\n    httpd.serve_forever()\n```"
* **query:** "What does the `Handler` variable do in that code?"
* **OUTPUT:**
    ```json
    {{
      "enough": true,
      "response": "In that Python code, the `Handler` variable is assigned `http.server.SimpleHTTPRequestHandler`. This is a built-in class that handles incoming HTTP requests by serving files from the current directory. When the server receives a request, this handler is responsible for processing it."
    }}
    ```

**Example 2: The query needs to be rewritten for a more specific technical search.**
* **last_chats:** "User: What's a Python decorator? \n Assistant: A decorator is a design pattern in Python that allows a user to add new functionality to an existing object without modifying its structure. Decorators are usually called before the definition of a function you want to decorate."
* **query:** "How would I use one for logging?"
* **OUTPUT:**
    ```json
    {{
      "enough": false,
      "new_query": "How do I create and use a Python decorator for logging function calls and their arguments?"
    }}
    ```

**Example 3: The query is already a self-contained technical question.**
* **last_chats:** ""
* **query:** "How do you reverse a string in JavaScript?"
* **OUTPUT:**
    ```json
    {{
      "enough": true,
      "response": "You can reverse a string in JavaScript by chaining the `split()`, `reverse()`, and `join()` methods. For example: `const reversed = 'hello'.split('').reverse().join('');` would result in `'olleh'`."
    }}
    ```
---

**Current Task:**

* **last_chats:** {last_chats}
* **query:** {query}
* **OUTPUT:**
```json
{{
  // Your JSON output here
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

        If the Context is related to the query only then Answer the query concisely and accurately 
        and mention the context used in newlines.
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
            self.save_turn_to_vdb(role="user",content= user_query)
            self.save_turn_to_vdb(role="bot",content= answer)
            return answer

        last_chats=[f"user:{turn['user']}\nbot:{turn['bot']}\ncontext:{turn['context']}" for turn in self.chat_window]
        planner_result = self.planner_restructure(user_query, last_chats)
        if planner_result.get("enough"):
            answer = planner_result["response"]
            # logging.info("Planner provided direct answer.")#for testing
        else:
            new_query = planner_result["new_query"]
            # logging.info("Planner indicated not enough info Given to the Engineer LLM.")#for testing
            # logging.info(f"Planner restructured query: {new_query}")#for testing 

            # Step 1: Try retrieving from chat memory
            chat_docs, confidence = self.retrieve_from_chat_memory(new_query)

            if confidence < self.confidence_threshold:
                # Step 2: Fallback to main DB
                context_docs = self.fetch_from_main_db(new_query)
            else:
                context_docs = []

            answer = self.engineer_answer(new_query, chat_docs, context_docs)

        # Save to chat memory VDB
        self.save_turn_to_vdb(role="context", docs=context_docs)
        self.save_turn_to_vdb(role="user",content= user_query)
        self.save_turn_to_vdb(role="bot",content= answer)
        self.chat_window.append({"user": user_query, "bot": answer,"context": context_docs})
        if len(self.chat_window) > 5:
            self.chat_window.pop(0)
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
