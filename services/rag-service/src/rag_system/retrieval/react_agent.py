"""
ReAct RAG Agent with query classification and intelligent routing.

Implements the ReAct (Reasoning and Acting) pattern to decide whether to:
1. Answer conversational queries directly (no retrieval)
2. Use RAG for factual/knowledge queries (with retrieval)
3. Ask for clarification on ambiguous queries
"""

from typing import Dict, Any
from langchain_community.chat_models import ChatOllama

from src.rag_system.utils.logger import get_logger

logger = get_logger(__name__)


class ReActRAGAgent:
    """
    ReAct-based RAG Agent that intelligently routes queries.

    The agent classifies queries into three categories:
    - conversational: Greetings, thanks, small talk -> answer directly
    - factual: Domain knowledge, specific facts -> use RAG retrieval
    - ambiguous: Unclear intent -> ask for clarification
    """

    def __init__(
        self,
        llm: ChatOllama,
        smart_rag_agent,
        classification_temperature: float = 0.0,
    ):
        """
        Initialize ReAct RAG Agent.

        Args:
            llm: ChatOllama instance for query classification
            smart_rag_agent: SmartRAGAgent instance for RAG queries
            classification_temperature: Temperature for classification (0=deterministic)
        """
        self.llm = llm
        self.smart_rag_agent = smart_rag_agent
        self.classification_temperature = classification_temperature

        logger.info("ReActRAGAgent initialized with query classification")

    def classify_query(self, query: str) -> str:
        """
        Classify query intent using LLM.

        Args:
            query: User's query

        Returns:
            Classification: 'conversational', 'factual', or 'ambiguous'
        """
        classification_prompt = (
            "You are a query classifier for a RAG system. "
            "Analyze the user's query and classify it into ONE of these categories:\n\n"
            "1. conversational - Greetings, thanks, small talk, social interactions\n"
            "   Examples: Hi, Hello, Thank you, How are you?\n\n"
            "2. factual - Questions requiring specific facts, domain knowledge\n"
            "   Examples: Who invented..., What is..., Explain the concept of...\n\n"
            "3. ambiguous - Queries with unclear intent that need clarification\n"
            "   Examples: Tell me more, What about it?, Continue\n\n"
            f"Query: {query}\n\n"
            "Classification (respond with ONLY ONE WORD - conversational, factual, or ambiguous):"
        )

        try:
            response = self.llm.invoke(classification_prompt)
            classification = response.content.strip().lower() if hasattr(response, "content") else str(response).strip().lower()

            valid_classifications = ["conversational", "factual", "ambiguous"]
            if classification not in valid_classifications:
                logger.warning(f"Invalid classification '{classification}', defaulting to 'factual'")
                classification = "factual"

            logger.info(f"Query classified as: {classification}")
            return classification

        except Exception as e:
            logger.error(f"Query classification failed: {str(e)}")
            return "factual"

    def query(self, question: str) -> Dict[str, Any]:
        """
        Process query with ReAct pattern (Reason -> Act).

        Args:
            question: User's question

        Returns:
            Dictionary with answer, classification, and metadata
        """
        logger.info(f"ReActRAGAgent received query: {question}")

        try:
            classification = self.classify_query(question)

            if classification == "conversational":
                return self._handle_conversational(question)
            elif classification == "factual":
                return self._handle_factual(question)
            else:
                return self._handle_ambiguous(question)

        except Exception as e:
            logger.error(f"ReActRAGAgent query failed: {str(e)}")
            return {
                "question": question,
                "answer": f"Error processing query: {str(e)}",
                "classification": "error",
                "is_relevant": False,
                "source_documents": [],
                "num_sources": 0,
            }

    def _handle_conversational(self, question: str) -> Dict[str, Any]:
        """Handle conversational queries with direct LLM response (no retrieval)."""
        logger.info("Handling conversational query - no retrieval needed")

        prompt = f"You are a friendly AI assistant. Respond naturally to: {question}\n\nAssistant:"

        try:
            response = self.llm.invoke(prompt)
            answer = response.content if hasattr(response, "content") else str(response)

            return {
                "question": question,
                "answer": answer,
                "classification": "conversational",
                "is_relevant": False,
                "source_documents": [],
                "num_sources": 0,
            }

        except Exception as e:
            logger.error(f"Conversational query handling failed: {str(e)}")
            return {
                "question": question,
                "answer": "Sorry, I encountered an error responding to your message.",
                "classification": "conversational",
                "is_relevant": False,
                "source_documents": [],
                "num_sources": 0,
            }

    def _handle_factual(self, question: str) -> Dict[str, Any]:
        """Handle factual queries using SmartRAGAgent (with retrieval)."""
        logger.info("Handling factual query - using RAG retrieval")

        result = self.smart_rag_agent.query(question)
        result["classification"] = "factual"

        return result

    def _handle_ambiguous(self, question: str) -> Dict[str, Any]:
        """Handle ambiguous queries by asking for clarification."""
        logger.info("Handling ambiguous query - requesting clarification")

        message = (
            "I'm not sure I understand your question clearly. "
            "Could you please provide more details or rephrase your question?\n\n"
            "For example:\n"
            "- If you're looking for specific information, please provide more context\n"
            "- If you want to continue a previous topic, please refer to it explicitly\n"
            "- If you need general help, let me know what you'd like to know about"
        )

        return {
            "question": question,
            "answer": message,
            "classification": "ambiguous",
            "is_relevant": False,
            "source_documents": [],
            "num_sources": 0,
        }
