"""
Multi-Query Retriever for improved document retrieval.

Generates multiple query variations to improve recall and
retrieve more relevant documents from the vector store.
"""

from typing import List, Any
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.rag_system.utils.logger import get_logger

logger = get_logger(__name__)


class MultiQueryRetriever(BaseRetriever):
    """
    Multi-Query Retriever that generates multiple query variations.

    Improves retrieval by:
    1. Generating N variations of the original query
    2. Retrieving documents for each variation
    3. Merging and deduplicating results
    """

    retriever: BaseRetriever
    llm: Any  # ChatOllama or compatible LLM
    num_queries: int = 3
    k: int = 4

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        retriever: BaseRetriever,
        llm: Any,
        num_queries: int = 3,
        k: int = 4,
    ):
        """
        Initialize Multi-Query Retriever.

        Args:
            retriever: Base retriever to use for document retrieval
            llm: LLM for query generation
            num_queries: Number of query variations to generate
            k: Number of documents to retrieve per query
        """
        super().__init__(
            retriever=retriever,
            llm=llm,
            num_queries=num_queries,
            k=k,
        )

        logger.info(f"MultiQueryRetriever initialized (num_queries={num_queries}, k={k})")

    @property
    def vectorstore(self):
        """
        Expose the underlying vector store for compatibility with RAGChain.

        Handles both direct vector retrievers and HybridRetriever which has
        a vector_retriever attribute.
        """
        # Try direct vectorstore attribute
        if hasattr(self.retriever, 'vectorstore'):
            return self.retriever.vectorstore
        # Handle HybridRetriever which has vector_retriever
        if hasattr(self.retriever, 'vector_retriever'):
            return self.retriever.vector_retriever.vectorstore
        raise AttributeError("Underlying retriever does not have a vectorstore")

    @property
    def search_kwargs(self):
        """Expose search_kwargs from underlying retriever for compatibility."""
        if hasattr(self.retriever, 'search_kwargs'):
            return self.retriever.search_kwargs
        # For HybridRetriever, construct equivalent kwargs
        if hasattr(self.retriever, 'k'):
            return {"k": self.retriever.k}
        return {"k": self.k}

    def _generate_queries(self, question: str) -> List[str]:
        """
        Generate multiple query variations.

        Args:
            question: Original query

        Returns:
            List of query variations
        """
        prompt_template = (
            "You are an AI assistant helping to improve document retrieval. "
            "Generate {num_queries} different versions of the given question "
            "to retrieve relevant documents from a vector database. "
            "The variations should cover different aspects and phrasings "
            "while maintaining the original intent.\n\n"
            "Original question: {question}\n\n"
            "Provide {num_queries} alternative questions (one per line, no numbering):"
        )

        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["question", "num_queries"],
        )

        chain = prompt | self.llm | StrOutputParser()

        try:
            response = chain.invoke({
                "question": question,
                "num_queries": self.num_queries
            })

            queries = [q.strip() for q in response.strip().split('\n') if q.strip()]
            queries = queries[:self.num_queries]

            if len(queries) < self.num_queries:
                queries = [question] + queries

            logger.info(f"Generated {len(queries)} query variations")
            for idx, q in enumerate(queries, 1):
                logger.debug(f"  Query {idx}: {q[:50]}...")

            return queries

        except Exception as e:
            logger.error(f"Query generation failed: {str(e)}")
            return [question]

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun = None
    ) -> List[Document]:
        """
        Retrieve documents using multiple query variations.

        Args:
            query: Original query
            run_manager: Callback manager

        Returns:
            Merged and deduplicated documents
        """
        logger.info(f"MultiQueryRetriever processing: {query[:50]}...")

        queries = self._generate_queries(query)

        all_documents = []
        for idx, q in enumerate(queries, 1):
            logger.debug(f"Retrieving with query {idx}/{len(queries)}: {q[:50]}...")
            docs = self.retriever.get_relevant_documents(q)
            all_documents.extend(docs)
            logger.debug(f"  Retrieved {len(docs)} documents")

        seen_content = set()
        unique_documents = []

        for doc in all_documents:
            doc_id = doc.page_content[:100]
            if doc_id not in seen_content:
                seen_content.add(doc_id)
                unique_documents.append(doc)

        results = unique_documents[:self.k]

        logger.info(
            f"MultiQueryRetriever: {len(all_documents)} total docs -> "
            f"{len(unique_documents)} unique -> {len(results)} returned"
        )

        return results
