import os
import json
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai
from src.vector_db.chroma_manager import ChromaManager

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("debugger_agent")

# -----------------------
# CONFIG
# -----------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# -----------------------
# LLM Client
# -----------------------
class LLMClient:
    def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key:
            logger.warning("Gemini API key not set!")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model)

    def call_llm(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.0) -> str:
        try:
            resp = self.model.generate_content(prompt, generation_config={"temperature": temperature})
            return resp.text
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return "{}"
    def call_llm_json(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.0) -> Dict[str, Any]:
        try:
            resp = self.model.generate_content(prompt, generation_config={"temperature": temperature, "response_mime_type": "application/json"})
            return resp.text
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return {}


# -----------------------
# Prompts
# -----------------------
Planner_prompt = """
You are an engineer-planner that receives a debugging request.YOu are provided with a query about the codebase.
Generate 3 subqueries that will be used to extract the relevant code snippets from the vectorDB.Do not include any extra text.
Output JSON:
{
  "query1": "...",
  "query2": "...",
  "query3": "..."
}

Here is the query:

"""

main_llm_prompt = """
You are an engineer-debugger that receives:
- Issue metadata
- Target code snippets
- count 

Task:
If you can identify the issue or solve the problem or count == 3, output JSON :
{
  "enough": true,
  "analysis": "<short analysis>",
  "fix": "<detailed fix with file + line numbers>"
}

Else if you need more context is needed then:
{
  "enough": false,
  "Required_queries": ["...", "...", "..."]
}
 the required queries should be such u could retrieve relevant code snippets.
Constraints:
- Only output valid JSON. No extra prose.
"""


# -----------------------
# Planner
# -----------------------
class Planner:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def plan(self, query: str) -> List[str]:
        raw = self.llm.call_llm_json(Planner_prompt + "\n\n" + query, max_tokens=512)
        try:
            parsed = json.loads(raw)
            return [parsed.get("query1"), parsed.get("query2"), parsed.get("query3")]
        except Exception:
            logger.warning("Planner returned unparseable JSON")
            return []


# -----------------------
# Analyzer
# -----------------------
class DebugMain:
    def __init__(self, llm: LLMClient):
        self.llm = llm



    def analyze(self, query: str, snippets: List[Dict[str, Any]],count:int) -> Dict[str, Any]:
        prompt = main_llm_prompt + f"\nUser query: {query}\n"
        for r in snippets:
            md = r.get("metadata", {})
            doc = r.get("document", "")
            prompt += f"\nMetadata: {md}\nCode:\n{doc}\n + count: {count}\n"
        raw = self.llm.call_llm_json(prompt, max_tokens=1024)
        
        try:
            return json.loads(raw)
        except Exception as e:
            logger.error("Analyzer returned invalid JSON: %s", e)
            return {}
        

# -----------------------
# Debugger Agent
# -----------------------
class DebuggerAgent:
    def __init__(self, planner: Planner, retriever:ChromaManager, analyzer: DebugMain, max_iter: int = 3):
        self.planner = planner
        self.retriever = retriever
        self.analyzer = analyzer
        self.max_iter = max_iter

    def run(self, user_query: str) -> Optional[Dict[str, Any]]:
        logger.info("Planning subqueries...")
        subqueries = self.planner.plan(user_query)
        all_snippets: List[Dict[str, Any]] = []

        for q in subqueries:
            if not q:
                continue
            snippets = self.retriever.search_code(q)
            all_snippets.extend(snippets)

        for i in range(self.max_iter):
            result = self.analyzer.analyze(user_query, all_snippets,i+1)
            print(result)
            if result.get("enough") is True:
                return {"analysis": result.get("analysis"), "fix": result.get("fix")}

            queries = result.get("Required_queries", [])
            new_snippets = []
            for q in queries:
                new_snippets.extend(self.retriever.search_code(q))
            all_snippets.extend(new_snippets)

        return None

