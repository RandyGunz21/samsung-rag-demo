"""
Conversation Context Manager for context-aware query handling.

Maintains conversation history and expands queries with relevant context
to handle follow-up questions with ambiguous references.
"""

import re
from typing import Dict, Any, List, Optional
from langchain_community.chat_models import ChatOllama

from src.rag_system.utils.logger import get_logger

logger = get_logger(__name__)


class ConversationContextManager:
    """
    Manages conversation history and context-aware query expansion.

    Enables the agent to understand follow-up questions like:
    - Q1: "When was 'A Logical Calculus...' published?"
    - Q2: "Who wrote the paper?" -> Expands to include paper title from Q1
    """

    # Patterns indicating query might need context expansion
    AMBIGUOUS_PATTERNS = [
        r'\b(it|its|they|them|their|this|that|these|those)\b',
        r'\bthe (paper|article|document|study|research|author|person|book)\b',
        r'\bthe same\b',
        r'\bmentioned (above|earlier|before|previously)\b',
        r'^(who|what|when|where|why|how)\b.*\??\s*$',  # Short questions
    ]

    def __init__(
        self,
        llm: ChatOllama,
        max_history: int = 5,
    ):
        """
        Initialize Conversation Context Manager.

        Args:
            llm: LLM for query expansion
            max_history: Maximum conversation turns to keep (default: 5)
        """
        self.llm = llm
        self.max_history = max_history
        self.history: List[Dict[str, str]] = []

        logger.info(f"ConversationContextManager initialized (max_history={max_history})")

    def add_turn(self, question: str, answer: str) -> None:
        """
        Add a conversation turn to history.

        Args:
            question: User's question
            answer: Agent's answer
        """
        self.history.append({
            "question": question,
            "answer": answer[:500]  # Truncate long answers
        })

        # Trim history if exceeds max
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        logger.debug(f"Added turn to history. Total turns: {len(self.history)}")

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.history = []
        logger.info("Conversation history cleared")

    def get_history_summary(self) -> str:
        """Get formatted history for display."""
        if not self.history:
            return "No conversation history."

        summary = []
        for i, turn in enumerate(self.history, 1):
            summary.append(f"Turn {i}:")
            summary.append(f"  Q: {turn['question'][:100]}...")
            summary.append(f"  A: {turn['answer'][:100]}...")
        return "\n".join(summary)

    def _needs_context_expansion(self, query: str) -> bool:
        """
        Check if query contains ambiguous references that need expansion.

        Args:
            query: User's query

        Returns:
            True if query likely needs context expansion
        """
        if not self.history:
            return False

        query_lower = query.lower()

        # Check for ambiguous patterns
        for pattern in self.AMBIGUOUS_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                logger.debug(f"Query matches ambiguous pattern: {pattern}")
                return True

        # Very short queries often need context
        if len(query.split()) <= 4 and not query.lower().startswith(('hi', 'hello', 'thanks', 'bye')):
            logger.debug("Short query detected, may need context")
            return True

        return False

    def _format_history_for_prompt(self) -> str:
        """Format conversation history for the expansion prompt."""
        if not self.history:
            return "No previous conversation."

        formatted = []
        for i, turn in enumerate(self.history, 1):
            formatted.append(f"Q{i}: {turn['question']}")
            formatted.append(f"A{i}: {turn['answer'][:200]}")
        return "\n".join(formatted)

    def expand_query(self, query: str) -> str:
        """
        Expand query with context from conversation history.

        If the query contains ambiguous references (like "the paper", "it"),
        rewrites it to be self-contained using context from history.

        Args:
            query: User's current query

        Returns:
            Expanded query (or original if no expansion needed)
        """
        # Check if expansion is needed
        if not self._needs_context_expansion(query):
            logger.debug("Query does not need context expansion")
            return query

        logger.info(f"Expanding query with conversation context: {query[:50]}...")

        expansion_prompt = f"""You are a query rewriter. Given the conversation history below, rewrite the user's current question to be completely self-contained.

RULES:
1. If the question references something from previous conversation (like "the paper", "it", "they", "this topic"), replace those references with the actual entities mentioned earlier.
2. Keep the rewritten question concise and natural.
3. If the question is already self-contained or there's no relevant context, return it EXACTLY as-is.
4. Do NOT answer the question, just rewrite it.
5. Return ONLY the rewritten question, nothing else.

Conversation History:
{self._format_history_for_prompt()}

Current Question: {query}

Rewritten Question:"""

        try:
            response = self.llm.invoke(expansion_prompt)
            expanded = response.content.strip() if hasattr(response, "content") else str(response).strip()

            # Clean up any extra quotes or prefixes
            expanded = expanded.strip('"\'')
            if expanded.lower().startswith("rewritten question:"):
                expanded = expanded[18:].strip()

            # Sanity check - if expansion is way longer or completely different, use original
            if len(expanded) > len(query) * 3 or not expanded:
                logger.warning("Expansion seems invalid, using original query")
                return query

            logger.info(f"Query expanded: '{query}' -> '{expanded}'")
            return expanded

        except Exception as e:
            logger.error(f"Query expansion failed: {str(e)}")
            return query


class ContextAwareRAGAgent:
    """
    Context-aware wrapper around ReActRAGAgent.

    Maintains conversation history and expands queries with relevant
    context before passing to the underlying ReActRAGAgent.
    """

    def __init__(
        self,
        react_agent,
        llm: ChatOllama,
        max_history: int = 5,
    ):
        """
        Initialize Context-Aware RAG Agent.

        Args:
            react_agent: ReActRAGAgent instance
            llm: LLM for query expansion
            max_history: Maximum conversation turns to keep
        """
        self.react_agent = react_agent
        self.context_manager = ConversationContextManager(
            llm=llm,
            max_history=max_history,
        )

        logger.info("ContextAwareRAGAgent initialized")

    def query(self, question: str) -> Dict[str, Any]:
        """
        Process query with context awareness.

        Args:
            question: User's question

        Returns:
            Response dictionary with answer and metadata
        """
        # Expand query with conversation context
        original_question = question
        expanded_question = self.context_manager.expand_query(question)

        # Track if query was expanded
        was_expanded = expanded_question != original_question

        # Process with ReActRAGAgent
        result = self.react_agent.query(expanded_question)

        # Add context info to result
        result["original_question"] = original_question
        result["expanded_question"] = expanded_question if was_expanded else None
        result["context_used"] = was_expanded

        # Update conversation history
        self.context_manager.add_turn(
            question=original_question,
            answer=result.get("answer", "")
        )

        return result

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.context_manager.clear_history()

    def get_history_summary(self) -> str:
        """Get formatted history summary."""
        return self.context_manager.get_history_summary()
