"""
RAG Chain implementation with prompt engineering.

Combines retrieval and generation for context-based question answering.
"""

import time
import socket
from typing import Dict, Any, List, Optional
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from src.rag_system.utils.logger import get_logger

logger = get_logger(__name__)


class RAGChain:
    """RAG chain for context-based question answering."""

    def __init__(
        self,
        llm,
        retriever,
        system_prompt: Optional[str] = None,
        context_template: Optional[str] = None,
    ):
        """
        Initialize RAG chain.

        Args:
            llm: Language model instance
            retriever: Vector store retriever
            system_prompt: System prompt for LLM
            context_template: Template for formatting context and question
        """
        self.llm = llm
        self.retriever = retriever

        # Default system prompt emphasizing context-only answering
        self.system_prompt = system_prompt or """You are a helpful assistant that answers questions based ONLY on the provided context.

IMPORTANT RULES:
1. Answer ONLY using information from the context below
2. If the answer is not in the context, say "I don't have enough information to answer this question"
3. Do NOT use your pre-trained knowledge
4. Cite the source document when providing answers
5. Be concise and accurate"""

        # Default context template
        self.context_template = context_template or """Context:
{context}

Question: {question}

Answer: Let me answer based on the provided context:"""

        # Build the prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", self.context_template),
        ])

        # Build the chain
        self.chain = (
            {
                "context": self.retriever | self._format_docs,
                "question": RunnablePassthrough(),
            }
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

        logger.info("RAG chain initialized successfully")

    def _format_docs(self, docs: List[Document]) -> str:
        """
        Format retrieved documents for context.

        Args:
            docs: List of retrieved documents

        Returns:
            Formatted context string
        """
        formatted = []

        for idx, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "Unknown")
            page = doc.metadata.get("page", "N/A")

            formatted.append(
                f"Source {idx} [{source}, Page {page}]:\n{doc.page_content}\n"
            )

        return "\n".join(formatted)

    def query(self, question: str) -> Dict[str, Any]:
        """
        Query the RAG system.

        Args:
            question: User question

        Returns:
            Dictionary with answer and metadata
        """
        logger.info(f"Query: {question}")

        try:
            # Retrieve relevant documents
            retrieved_docs = self.retriever.invoke(question)

            logger.info(f"Retrieved {len(retrieved_docs)} documents")

            # Generate answer
            answer = self.chain.invoke(question)

            logger.info(f"Answer generated: {answer[:100]}...")

            # Prepare response
            response = {
                "question": question,
                "answer": answer,
                "source_documents": [
                    {
                        "content": doc.page_content[:200] + "...",
                        "metadata": doc.metadata,
                    }
                    for doc in retrieved_docs
                ],
                "num_sources": len(retrieved_docs),
            }

            return response

        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            return {
                "question": question,
                "answer": f"Error: {str(e)}",
                "source_documents": [],
                "num_sources": 0,
            }

    def query_with_scores(self, question: str) -> Dict[str, Any]:
        """
        Query the RAG system with relevance scores.

        Args:
            question: User question

        Returns:
            Dictionary with answer, sources, and relevance scores
        """
        logger.info(f"Query with scores: {question}")

        docs_with_scores = []  # Initialize to preserve on error
        source_documents = []  # Initialize for error handling

        try:
            # Get retriever's vector store for similarity search with scores
            vector_store = self.retriever.vectorstore

            # Retrieve with scores
            docs_with_scores = vector_store.similarity_search_with_score(
                question,
                k=self.retriever.search_kwargs.get("k", 4),
            )

            logger.info(f"Retrieved {len(docs_with_scores)} documents with scores")

            # Format source documents (before LLM generation)
            source_documents = [
                {
                    "content": doc.page_content[:200] + "...",
                    "metadata": doc.metadata,
                    "relevance_score": float(score),
                }
                for doc, score in docs_with_scores
            ]

            # Format context from retrieved documents
            docs = [doc for doc, _ in docs_with_scores]
            context = self._format_docs(docs)

            # Generate answer with retry logic for transient failures
            prompt_value = self.prompt.invoke({
                "context": context,
                "question": question,
            })

            # Retry logic for transient DNS/network failures
            max_retries = 3
            retry_delay = 1  # seconds
            answer = None

            for attempt in range(max_retries):
                try:
                    answer = self.llm.invoke(prompt_value)
                    logger.info(f"LLM invocation succeeded on attempt {attempt + 1}")
                    break  # Success - exit retry loop
                except (socket.gaierror, OSError, ConnectionError, Exception) as e:
                    # Catch network-related errors and retry
                    error_str = str(e)
                    is_network_error = (
                        "getaddrinfo" in error_str or
                        "DNS" in error_str or
                        "connection" in error_str.lower() or
                        isinstance(e, (socket.gaierror, OSError, ConnectionError))
                    )

                    if is_network_error and attempt < max_retries - 1:
                        logger.warning(
                            f"LLM invocation failed (attempt {attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {retry_delay}s..."
                        )
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff: 1s, 2s, 4s
                    else:
                        logger.error(f"LLM invocation failed after {max_retries} attempts: {e}")
                        raise  # Re-raise after final attempt or non-network error

            # Success - return full response
            response = {
                "question": question,
                "answer": answer.content if hasattr(answer, "content") else str(answer),
                "source_documents": source_documents,
                "num_sources": len(docs_with_scores),
            }

            return response

        except Exception as e:
            logger.error(f"Query with scores failed: {str(e)}")

            # IMPORTANT: Preserve retrieved documents even if LLM fails
            # This allows SmartRAGAgent to distinguish between:
            # 1. No documents in knowledge base (docs_with_scores empty)
            # 2. LLM connectivity issue (docs_with_scores populated)
            source_documents = [
                {
                    "content": doc.page_content[:200] + "...",
                    "metadata": doc.metadata,
                    "relevance_score": float(score),
                }
                for doc, score in docs_with_scores
            ] if docs_with_scores else []

            return {
                "question": question,
                "answer": f"LLM Error: {str(e)}",
                "source_documents": source_documents,
                "num_sources": len(docs_with_scores),
                "llm_error": True,  # Flag to indicate LLM failure
            }
