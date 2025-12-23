"""
Chat Agent - Orchestrates LLM and RAG for conversations.

Handles query classification, context management, and response generation.
Includes context-aware query expansion following the pattern from
src/rag_system/retrieval/context_manager.py for handling follow-up questions.
"""

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

# Add project root for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ..rag_client import RAGClient, RAGServiceError, get_rag_client
from .session_manager import SessionManager, get_session_manager


class ChatAgent:
    """
    Chat Agent for handling user conversations.

    Orchestrates:
    - Query classification (factual, conversational, ambiguous)
    - Context-aware query expansion with ambiguous reference detection
    - RAG retrieval via RAG Service
    - LLM response generation

    Context awareness follows the pattern from ConversationContextManager
    to handle follow-up questions like:
    - Q1: "When was 'Attention is All You Need' published?"
    - Q2: "Who wrote that paper?" -> Expands to include paper title from Q1
    """

    # Patterns indicating query might need context expansion
    # Following src/rag_system/retrieval/context_manager.py
    AMBIGUOUS_PATTERNS = [
        r'\b(it|its|they|them|their|this|that|these|those)\b',
        r'\bthe (paper|article|document|study|research|author|person|book|topic|subject)\b',
        r'\bthe same\b',
        r'\bmentioned (above|earlier|before|previously)\b',
        r'\b(more|another|other) (details?|information|examples?)\b',
        r'^(who|what|when|where|why|how)\b.*\??\s*$',  # Short questions
    ]

    # Patterns for queries that don't need expansion (greetings, thanks)
    SKIP_EXPANSION_PATTERNS = [
        r'^(hi|hello|hey|thanks|thank you|bye|goodbye|ok|okay)\b',
    ]

    def __init__(
        self,
        rag_client: Optional[RAGClient] = None,
        session_manager: Optional[SessionManager] = None,
    ):
        """Initialize chat agent."""
        self.rag_client = rag_client or get_rag_client()
        self.session_manager = session_manager or get_session_manager()
        self._llm = None

    def _get_llm(self):
        """Lazy load LLM."""
        if self._llm is None:
            from ..llm import load_config, OllamaLLM

            config = load_config()
            self._llm = OllamaLLM(
                model=config.get("llm.model"),
                base_url=config.get("llm.base_url"),
                temperature=config.get("llm.temperature", 0.1),
                max_tokens=config.get("llm.max_tokens", 512),
                timeout=config.get("llm.timeout", 60),
            )
        return self._llm

    def classify_query(self, query: str) -> str:
        """Classify query type using LLM."""
        llm = self._get_llm()

        classification_prompt = f"""Classify this query into one of these categories:
- factual: Seeks specific information from documents
- conversational: Casual chat, greetings, or general questions
- ambiguous: Unclear what information is needed

Query: {query}

Respond with only the category name:"""

        try:
            result = llm.llm.invoke(classification_prompt)
            classification = result.content.strip().lower()

            if classification in ["factual", "conversational", "ambiguous"]:
                return classification
            return "ambiguous"
        except Exception:
            return "factual"

    def _needs_context_expansion(self, query: str, has_history: bool) -> bool:
        """
        Check if query contains ambiguous references that need expansion.

        Following the pattern from src/rag_system/retrieval/context_manager.py
        to intelligently detect when context expansion is actually needed.

        Args:
            query: User's query
            has_history: Whether conversation history exists

        Returns:
            True if query likely needs context expansion
        """
        if not has_history:
            return False

        query_lower = query.lower().strip()

        # Skip expansion for greetings/thanks
        for pattern in self.SKIP_EXPANSION_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return False

        # Check for ambiguous patterns
        for pattern in self.AMBIGUOUS_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return True

        # Very short queries (≤4 words) often need context
        word_count = len(query.split())
        if word_count <= 4:
            return True

        return False

    def expand_query_with_context(self, query: str, context_summary: str) -> str:
        """
        Expand query with context from conversation history.

        If the query contains ambiguous references (like "the paper", "it", "that"),
        rewrites it to be self-contained using context from history.

        Following the enhanced pattern from src/rag_system/retrieval/context_manager.py.

        Args:
            query: User's current query
            context_summary: Formatted conversation history

        Returns:
            Expanded query (or original if no expansion needed)
        """
        # Check if expansion is actually needed
        has_history = bool(context_summary and context_summary.strip())
        if not self._needs_context_expansion(query, has_history):
            return query

        llm = self._get_llm()

        # Enhanced expansion prompt with specific rules (from ConversationContextManager)
        expansion_prompt = f"""You are a query rewriter. Given the conversation history below, rewrite the user's current question to be completely self-contained.

RULES:
1. If the question references something from previous conversation (like "the paper", "it", "they", "this topic", "that"), replace those references with the actual entities mentioned earlier.
2. Keep the rewritten question concise and natural.
3. If the question is already self-contained or there's no relevant context, return it EXACTLY as-is.
4. Do NOT answer the question, just rewrite it.
5. Return ONLY the rewritten question, nothing else.

Conversation History:
{context_summary}

Current Question: {query}

Rewritten Question:"""

        try:
            result = llm.llm.invoke(expansion_prompt)
            expanded = result.content.strip() if hasattr(result, "content") else str(result).strip()

            # Clean up any extra quotes or prefixes
            expanded = expanded.strip('"\'')
            if expanded.lower().startswith("rewritten question:"):
                expanded = expanded[18:].strip()

            # Enhanced sanity checks (from ConversationContextManager)
            # 1. If expansion is way too long, use original
            if len(expanded) > len(query) * 3:
                return query

            # 2. If expansion is empty or too short, use original
            if not expanded or len(expanded) < len(query) * 0.3:
                return query

            # 3. If expansion contains answer-like content, use original
            answer_indicators = ["the answer is", "it was published", "the author is", "yes,", "no,"]
            if any(indicator in expanded.lower() for indicator in answer_indicators):
                return query

            return expanded

        except Exception:
            return query

    async def chat(
        self,
        message: str,
        session_id: Optional[UUID] = None,
        show_sources: bool = True,
        similarity_threshold: float = 0.5,
        max_sources: int = 4,
    ) -> Dict[str, Any]:
        """Process a chat message and generate response."""
        session = self.session_manager.get_or_create_session(session_id)
        session.add_message(role="user", content=message)

        classification = self.classify_query(message)

        response = {
            "session_id": session.session_id,
            "classification": classification,
            "is_relevant": False,
            "context_used": False,
            "expanded_question": None,
            "relevance_info": None,
            "sources": [],
            "num_sources": 0,
        }

        if classification == "conversational":
            answer = await self._handle_conversational(message)
            response["answer"] = answer

        elif classification == "ambiguous":
            answer = await self._handle_ambiguous(message)
            response["answer"] = answer

        else:
            # Factual query - use RAG
            context_summary = session.get_context_summary()
            expanded_query = message

            if context_summary:
                expanded_query = self.expand_query_with_context(message, context_summary)
                if expanded_query != message:
                    response["context_used"] = True
                    response["expanded_question"] = expanded_query

            try:
                rag_result = await self.rag_client.multi_query_retrieve(
                    query=expanded_query,
                    num_queries=3,
                    top_k=max_sources,
                    similarity_threshold=similarity_threshold,
                )

                relevance_info = rag_result.get("relevance_info", {})
                documents = rag_result.get("documents", [])

                response["is_relevant"] = relevance_info.get("is_relevant", False)
                response["relevance_info"] = {
                    "best_score": relevance_info.get("best_score", 0),
                    "threshold": similarity_threshold,
                    "documents_found": len(documents),
                }

                if show_sources and documents:
                    response["sources"] = documents[:max_sources]
                    response["num_sources"] = len(documents)

                if response["is_relevant"] and documents:
                    answer = await self._generate_rag_answer(expanded_query, documents)
                else:
                    answer = await self._handle_no_relevant_docs(message)

                response["answer"] = answer

            except RAGServiceError as e:
                response["answer"] = f"Knowledge base unavailable: {e.message}"

        session.add_message(
            role="assistant",
            content=response["answer"],
            classification=classification,
            sources=response.get("sources") if show_sources else None,
        )

        return response

    async def _handle_conversational(self, message: str) -> str:
        """Handle conversational queries."""
        llm = self._get_llm()
        prompt = f"You are a helpful AI assistant. Respond naturally:\n\nUser: {message}\n\nAssistant:"
        try:
            result = llm.llm.invoke(prompt)
            return result.content.strip()
        except Exception as e:
            return f"I'm here to help! What would you like to know?"

    async def _handle_ambiguous(self, message: str) -> str:
        """Handle ambiguous queries."""
        return (
            "I'd like to help, but I need a bit more context. "
            "Could you please be more specific about what information you're looking for?"
        )

    async def _handle_no_relevant_docs(self, message: str) -> str:
        """Handle queries with no relevant documents."""
        return (
            "I couldn't find relevant information in the knowledge base for your question. "
            "Please try rephrasing your question or ask about a different topic."
        )

    async def _generate_rag_answer(
        self,
        question: str,
        documents: List[Dict[str, Any]],
    ) -> str:
        """Generate answer using LLM with retrieved context."""
        llm = self._get_llm()

        context = "\n\n".join([
            f"[Source: {doc.get('metadata', {}).get('source', 'Unknown')}]\n{doc['content']}"
            for doc in documents[:4]
        ])

        prompt = f"""Based on the following context, answer the question. If the context doesn't contain enough information, say so.

Context:
{context}

Question: {question}

Answer:"""

        try:
            result = llm.llm.invoke(prompt)
            return result.content.strip()
        except Exception as e:
            return f"Error generating response: {str(e)}"


# Singleton
_chat_agent: Optional[ChatAgent] = None


def get_chat_agent() -> ChatAgent:
    """Get chat agent singleton."""
    global _chat_agent
    if _chat_agent is None:
        _chat_agent = ChatAgent()
    return _chat_agent
