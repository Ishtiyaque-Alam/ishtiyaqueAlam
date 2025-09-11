import numpy as np
import logging
from typing import Dict, Any, List

from debugger_agent import LLMClient, DebuggerAgent
from manage_chunks import TopicSwitchingRetriever, TopicNode

logger = logging.getLogger("conv_bot")


class ConversationalBot:
    def __init__(self, topic_retriever: TopicSwitchingRetriever, debugger_agent: DebuggerAgent, llm: LLMClient):
        self.topic_retriever = topic_retriever
        self.debugger_agent = debugger_agent
        self.llm = llm

        self.answer_prompt_template = (
            "You are a helpful software assistant.\n\n"
            "Conversation history (this topic only):\n{stm}\n\n"
            "Code snippets:\n{snippets}\n\n"
            "User query: {query}\n\n"
            "Answer:"
        )

    def _format_snippets(self, snippets: List[Dict[str, Any]], max_len: int = 2000) -> str:
        parts = []
        for s in snippets:
            md = s.get("metadata", {})
            doc = s.get("document", "")
            header = f"File: {md.get('file')} Function: {md.get('function')} Lines: {md.get('start_line')}-{md.get('end_line')}"
            body = doc if len(doc) <= max_len else doc[:max_len] + "\n...[truncated]"
            parts.append(header + "\n" + body)
        return "\n\n---\n\n".join(parts) if parts else "<no snippets>"

    def handle_query(self, user_query: str) -> str:
        # --- Debugger path ---
        if "think" in user_query.lower():
            logger.info("Routing to DebuggerAgent...")
            debug_result = self.debugger_agent.run(user_query)
            if not debug_result:
                return "DebuggerAgent could not resolve the issue."
            answer = f"DebuggerAgent says:\nAnalysis: {debug_result['analysis']}\nFix: {debug_result['fix']}"
            if self.topic_retriever.active_topic:
                self.topic_retriever.active_topic.memory.add_turn(user_query, answer)
            return answer

        # --- Retrieval path ---
        result = self.topic_retriever.retrieve(user_query, n_results=5)
        topic_id = result["topic_id"]
        chunks = result["chunks"]
        active_topic = self.topic_retriever.active_topic

        snippets_text = self._format_snippets(chunks)
        stm_context = active_topic.memory.get_context() if active_topic else "<none>"

        prompt = self.answer_prompt_template.format(stm=stm_context, snippets=snippets_text, query=user_query)
        answer = self.llm.call_llm(prompt)

        if active_topic:
            active_topic.memory.add_turn(user_query, answer)

        return answer
