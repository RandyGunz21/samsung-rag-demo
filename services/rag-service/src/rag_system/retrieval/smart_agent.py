"""
Smart RAG Agent with relevance checking.

Answers questions only when relevant documents are found in the knowledge base.
If no relevant documents exist, asks the user to provide resources.
"""

from typing import Dict, Any
from src.rag_system.retrieval.rag_chain import RAGChain
from src.rag_system.utils.logger import get_logger

logger = get_logger(__name__)


class SmartRAGAgent:
    """
    Smart RAG Agent that checks document relevance before answering.

    This agent enhances the standard RAG chain by:
    1. Checking if retrieved documents are relevant enough to answer the question
    2. Only answering when relevant documents are found
    3. Asking for resources when no relevant documents exist
    """

    def __init__(
        self,
        rag_chain: RAGChain,
        relevance_threshold: float = 0.5,
    ):
        """
        Initialize Smart RAG Agent.

        Args:
            rag_chain: The underlying RAG chain for retrieval and generation
            relevance_threshold: Maximum distance score for relevance (ChromaDB uses cosine distance, lower = more similar)
                                 Default: 0.5 (documents with score < 0.5 are considered relevant)
        """
        self.rag_chain = rag_chain
        self.relevance_threshold = relevance_threshold

        logger.info(f"SmartRAGAgent initialized with relevance_threshold={relevance_threshold}")

    def query(self, question: str) -> Dict[str, Any]:
        """
        Query the agent with relevance checking.

        The agent will:
        1. Retrieve documents with similarity scores
        2. Check if any documents are relevant (score < threshold)
        3. If relevant: answer the question using RAG
        4. If not relevant: ask user to provide resources

        Args:
            question: User's question

        Returns:
            Dictionary containing:
                - question: Original question
                - answer: Generated answer or resource request message
                - is_relevant: Whether relevant documents were found
                - source_documents: Retrieved documents with scores (if any)
                - num_sources: Number of retrieved documents
                - relevance_info: Information about relevance check
        """
        logger.info(f"SmartRAGAgent received query: {question}")

        try:
            # Get documents with relevance scores
            result = self.rag_chain.query_with_scores(question)

            # Check if LLM failed but documents were retrieved
            if result.get("llm_error", False):
                logger.error("LLM connectivity error during answer generation")
                return self._generate_llm_error_response(question, result)

            # Extract source documents and scores
            source_documents = result.get("source_documents", [])

            if not source_documents:
                # No documents retrieved at all
                logger.warning("No documents retrieved from vector store")
                return self._generate_no_documents_response(question)

            # Check relevance using the best (lowest) score
            # ChromaDB uses cosine distance: 0 = identical, 2 = opposite
            # Lower scores = more similar = more relevant
            scores = [doc["relevance_score"] for doc in source_documents]
            best_score = min(scores)

            logger.info(f"Best relevance score: {best_score} (threshold: {self.relevance_threshold})")

            # Check if best document is relevant enough
            if best_score < self.relevance_threshold:
                # Relevant documents found - use RAG to answer
                logger.info("Relevant documents found - generating answer")

                return {
                    "question": question,
                    "answer": result["answer"],
                    "is_relevant": True,
                    "source_documents": source_documents,
                    "num_sources": len(source_documents),
                    "relevance_info": {
                        "best_score": float(best_score),
                        "threshold": self.relevance_threshold,
                        "all_scores": [float(s) for s in scores],
                    }
                }
            else:
                # No relevant documents - ask for resources
                logger.info("No relevant documents found - requesting resources")
                return self._generate_ask_for_resources_response(
                    question,
                    source_documents,
                    best_score
                )

        except Exception as e:
            logger.error(f"SmartRAGAgent query failed: {str(e)}")
            return {
                "question": question,
                "answer": f"Error processing query: {str(e)}",
                "is_relevant": False,
                "source_documents": [],
                "num_sources": 0,
                "relevance_info": {"error": str(e)}
            }

    def _generate_ask_for_resources_response(
        self,
        question: str,
        source_documents: list,
        best_score: float
    ) -> Dict[str, Any]:
        """
        Generate response asking user to provide resources.

        Args:
            question: Original question
            source_documents: Retrieved documents (not relevant enough)
            best_score: Best relevance score found

        Returns:
            Response dictionary with resource request message
        """
        message = (
            "I don't have sufficient information in my knowledge base to answer this question accurately. "
            "The documents I found are not closely related to your query.\n\n"
            "Could you please provide me with relevant documents or resources about this topic? "
            "You can:\n"
            "1. Upload documents using the ingest command\n"
            "2. Point me to specific files or resources\n"
            "3. Provide more context about what you're looking for\n\n"
            "Once I have the right information, I'll be happy to help you!"
        )

        return {
            "question": question,
            "answer": message,
            "is_relevant": False,
            "source_documents": source_documents,
            "num_sources": len(source_documents),
            "relevance_info": {
                "best_score": float(best_score),
                "threshold": self.relevance_threshold,
                "reason": "best_score exceeds threshold",
            }
        }

    def _generate_llm_error_response(
        self,
        question: str,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate response when LLM fails but documents were retrieved.

        Args:
            question: Original question
            result: RAG chain result with llm_error flag

        Returns:
            Response dictionary with LLM connectivity error message
        """
        source_documents = result.get("source_documents", [])
        num_sources = result.get("num_sources", 0)
        error_msg = result.get("answer", "Unknown error")

        message = (
            f"⚠️ **LLM Connectivity Error**\n\n"
            f"I found {num_sources} relevant document(s) in the knowledge base, "
            f"but I'm having trouble connecting to the language model server to generate an answer.\n\n"
            f"**Error Details:** {error_msg}\n\n"
            f"**What you can try:**\n"
            f"1. Check if the Ollama server/Cloudflare tunnel is running\n"
            f"2. Verify the `llm.base_url` in config.yaml is correct\n"
            f"3. Test connectivity: `curl {error_msg.split('(')[0] if '(' in error_msg else 'SERVER_URL'}`\n"
            f"4. Check network connectivity and DNS resolution\n\n"
            f"The documents are ready - just need to fix the LLM connection!"
        )

        return {
            "question": question,
            "answer": message,
            "is_relevant": False,
            "source_documents": source_documents,
            "num_sources": num_sources,
            "relevance_info": {
                "reason": "llm_connectivity_error",
                "num_documents_found": num_sources,
                "error": error_msg,
            }
        }

    def _generate_no_documents_response(self, question: str) -> Dict[str, Any]:
        """
        Generate response when no documents are retrieved at all.

        Args:
            question: Original question

        Returns:
            Response dictionary with empty knowledge base message
        """
        message = (
            "I don't have any documents in my knowledge base yet to answer this question.\n\n"
            "To get started, please:\n"
            "1. Ingest documents using: python src/main.py ingest --path <your-documents-path>\n"
            "2. Upload relevant files or documents\n"
            "3. Provide me with resources about the topics you want to query\n\n"
            "Once documents are loaded, I'll be able to help answer your questions!"
        )

        return {
            "question": question,
            "answer": message,
            "is_relevant": False,
            "source_documents": [],
            "num_sources": 0,
            "relevance_info": {
                "reason": "no_documents_in_knowledge_base",
            }
        }

    def set_relevance_threshold(self, threshold: float):
        """
        Update the relevance threshold.

        Args:
            threshold: New threshold value (lower = more strict)
        """
        logger.info(f"Updating relevance threshold: {self.relevance_threshold} -> {threshold}")
        self.relevance_threshold = threshold
