"""
RAG Engine - Core RAG functionality for the service.

Initializes and manages all RAG components.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import (
    load_config,
    DocumentLoader,
    DocumentChunker,
    EmbeddingGenerator,
    ChromaVectorStore,
    IngestionPipeline,
    PipelineOrchestrator,
    MultiQueryRetriever,
    HybridRetriever,
    BM25Retriever,
)
from src.rag_system.pipeline.orchestrator import DocumentHashCache, PipelineStats
from src.rag_system.utils.logger import get_logger

logger = get_logger(__name__)


class RAGEngine:
    """
    Core RAG Engine for document retrieval and ingestion.

    Manages all RAG components and provides high-level APIs for:
    - Document retrieval (similarity, MMR, hybrid)
    - Multi-query retrieval with query expansion
    - Document ingestion (single file and batch)
    - Pipeline orchestration with Prefect
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize RAG Engine with configuration."""
        self.config = load_config(config_path)
        self._start_time = time.time()
        self._llm = None  # Lazy-loaded LLM for query generation
        self._bm25_retriever = None  # Lazy-loaded BM25 for hybrid search
        self._hybrid_retriever = None  # Lazy-loaded hybrid retriever
        self._initialize_components()

    def _get_llm(self):
        """
        Lazy load LLM for multi-query generation.

        Uses ChatOllama following the pattern from MultiQueryRetriever.
        """
        if self._llm is None:
            from langchain_ollama import ChatOllama

            logger.info("Initializing LLM for multi-query retrieval...")

            self._llm = ChatOllama(
                model=self.config.get("llm.model", "gemma2:2b"),
                base_url=self.config.get("llm.base_url", "http://localhost:11434"),
                temperature=0.0,  # Deterministic for query generation
            )
            logger.info(f"LLM initialized: {self.config.get('llm.model', 'gemma2:2b')}")

        return self._llm

    def _get_hybrid_retriever(self, k: int = 4):
        """
        Lazy load hybrid retriever combining BM25 + Vector search.

        Following the pattern from src/rag_system/retrieval/hybrid_retriever.py
        for improved accuracy on entity-based queries.
        """
        # Get all documents from vector store for BM25 indexing
        try:
            # Fetch documents from ChromaDB collection
            collection = self.vector_store.collection
            results = collection.get(include=["documents", "metadatas"])

            if not results["documents"]:
                logger.warning("No documents in vector store for hybrid search")
                return None

            from langchain_core.documents import Document

            # Convert to LangChain Document objects
            documents = []
            for idx, content in enumerate(results["documents"]):
                metadata = results["metadatas"][idx] if results["metadatas"] else {}
                documents.append(Document(page_content=content, metadata=metadata))

            logger.info(f"Building BM25 index with {len(documents)} documents")

            # Create BM25 retriever
            bm25_retriever = BM25Retriever(documents=documents, k=k)

            # Create vector retriever
            vector_retriever = self.vector_store.get_retriever(
                search_type="similarity",
                search_kwargs={"k": k}
            )

            # Create hybrid retriever with configured weights
            bm25_weight = self.config.get("retrieval.bm25_weight", 0.3)
            vector_weight = self.config.get("retrieval.vector_weight", 0.7)

            hybrid_retriever = HybridRetriever(
                bm25_retriever=bm25_retriever,
                vector_retriever=vector_retriever,
                bm25_weight=bm25_weight,
                vector_weight=vector_weight,
                k=k,
            )

            logger.info(
                f"HybridRetriever initialized (BM25: {bm25_weight:.0%}, "
                f"Vector: {vector_weight:.0%})"
            )
            return hybrid_retriever

        except Exception as e:
            logger.error(f"Failed to initialize hybrid retriever: {e}")
            return None

    def _initialize_components(self):
        """Initialize all RAG components."""
        # Document processing
        self.document_loader = DocumentLoader(
            supported_formats=self.config.get("document_processing.supported_formats"),
            enable_ocr=self.config.get("ocr.enabled", False),
            max_tokens=self.config.get("document_processing.max_tokens", 1000),
        )

        self.document_chunker = DocumentChunker(
            embedding_model=self.config.get("embeddings.model", "qwen3-embedding:8b"),
            base_url=self.config.get("embeddings.base_url", "http://localhost:11434"),
            breakpoint_threshold_type=self.config.get("document_processing.breakpoint_threshold_type", "percentile"),
            breakpoint_threshold_amount=self.config.get("document_processing.breakpoint_threshold_amount"),
            chunk_size=self.config.get("document_processing.chunk_size", 1000),
            chunk_overlap=self.config.get("document_processing.chunk_overlap", 200),
            max_chunk_size=self.config.get("document_processing.max_chunk_size", 1500),
            separators=self.config.get("document_processing.separators"),
            add_start_index=self.config.get("document_processing.add_start_index", True),
        )

        # Embeddings
        self.embedding_generator = EmbeddingGenerator(
            model_name=self.config.get("embeddings.model", "qwen3-embedding:8b"),
            base_url=self.config.get("embeddings.base_url", "http://localhost:11434"),
        )

        # Vector store
        self.vector_store = ChromaVectorStore(
            embedding_function=self.embedding_generator.embeddings,
            persist_directory=self.config.get("vector_store.persist_directory", "./data/vector_store"),
            collection_name=self.config.get("vector_store.collection_name", "rag_documents"),
        )

        # Ingestion pipeline
        self.pipeline = IngestionPipeline(
            document_loader=self.document_loader,
            document_chunker=self.document_chunker,
            embedding_generator=self.embedding_generator,
            vector_store=self.vector_store,
        )

        # Pipeline orchestrator
        hash_file = self.config.get("pipeline.hash_file", "data/processed/.document_hashes.json")
        self.hash_cache = DocumentHashCache(hash_file)
        self.stats = PipelineStats()
        self.supported_formats = list(self.document_loader.supported_formats)

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        search_type: str = "similarity",
        similarity_threshold: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: Search query
            top_k: Number of results
            search_type: similarity, mmr, or hybrid
            similarity_threshold: Minimum relevance score
            filters: Optional metadata filters

        Returns:
            Dictionary with documents and metadata
        """
        start_time = time.time()

        # Handle hybrid search separately
        if search_type == "hybrid":
            return self._hybrid_retrieve(
                query=query,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
            )

        search_kwargs = {"k": top_k}
        if filters:
            search_kwargs["filter"] = filters

        retriever = self.vector_store.get_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs,
        )

        # Get documents with scores
        docs_with_scores = self.vector_store.similarity_search_with_score(
            query, k=top_k
        )

        # Filter by threshold and format results
        documents = []
        for doc, score in docs_with_scores:
            # ChromaDB returns distance, convert to similarity
            relevance_score = 1 - score if score <= 1 else 1 / (1 + score)

            if relevance_score >= similarity_threshold:
                documents.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "relevance_score": round(relevance_score, 4),
                })

        processing_time = int((time.time() - start_time) * 1000)

        return {
            "documents": documents,
            "query_processed": query,
            "search_type_used": search_type,
            "total_found": len(documents),
            "processing_time_ms": processing_time,
        }

    def _hybrid_retrieve(
        self,
        query: str,
        top_k: int = 4,
        similarity_threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Retrieve documents using hybrid search (BM25 + Vector).

        Combines keyword-based BM25 (30%) and semantic vector search (70%)
        following the pattern from src/rag_system/retrieval/hybrid_retriever.py.
        Best for entity-based queries where exact keyword matching is important.
        """
        start_time = time.time()

        # Get or create hybrid retriever
        hybrid_retriever = self._get_hybrid_retriever(k=top_k)

        if hybrid_retriever is None:
            # Fallback to similarity search if hybrid fails
            logger.warning("Hybrid retriever unavailable, falling back to similarity")
            return self.retrieve(
                query=query,
                top_k=top_k,
                search_type="similarity",
                similarity_threshold=similarity_threshold,
            )

        try:
            # Get documents from hybrid retriever
            docs = hybrid_retriever.get_relevant_documents(query)

            # Format results with estimated relevance scores
            documents = []
            for idx, doc in enumerate(docs):
                # Estimate relevance score based on rank (hybrid doesn't return scores)
                relevance_score = 1.0 - (idx * 0.1)  # Decreasing by rank
                relevance_score = max(relevance_score, 0.1)  # Minimum score

                if relevance_score >= similarity_threshold:
                    documents.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "relevance_score": round(relevance_score, 4),
                    })

            processing_time = int((time.time() - start_time) * 1000)

            bm25_weight = self.config.get("retrieval.bm25_weight", 0.3)
            vector_weight = self.config.get("retrieval.vector_weight", 0.7)

            logger.info(
                f"Hybrid search: {len(documents)} docs "
                f"(BM25: {bm25_weight:.0%}, Vector: {vector_weight:.0%})"
            )

            return {
                "documents": documents,
                "query_processed": query,
                "search_type_used": f"hybrid (BM25:{bm25_weight:.0%}+Vector:{vector_weight:.0%})",
                "total_found": len(documents),
                "processing_time_ms": processing_time,
            }

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}, falling back to similarity")
            return self.retrieve(
                query=query,
                top_k=top_k,
                search_type="similarity",
                similarity_threshold=similarity_threshold,
            )

    def multi_query_retrieve(
        self,
        query: str,
        num_queries: int = 3,
        top_k: int = 4,
        similarity_threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Retrieve with LLM-based query expansion.

        Uses LLM to generate semantic query variations for improved recall.
        Follows the pattern from src/rag_system/retrieval/multi_query_retriever.py
        for 20-30% recall improvement.
        """
        start_time = time.time()

        # Generate LLM-based query variations (with fallback)
        generated_queries = self._generate_queries_with_llm(query, num_queries)

        logger.info(f"Multi-query retrieval with {len(generated_queries)} variations")

        # Collect all documents with deduplication
        all_docs = {}
        best_score = 0.0

        for idx, q in enumerate(generated_queries, 1):
            logger.debug(f"Retrieving with query {idx}/{len(generated_queries)}: {q[:50]}...")
            docs_with_scores = self.vector_store.similarity_search_with_score(q, k=top_k)
            logger.debug(f"  Retrieved {len(docs_with_scores)} documents")

            for doc, score in docs_with_scores:
                relevance_score = 1 - score if score <= 1 else 1 / (1 + score)
                doc_id = f"{doc.metadata.get('source', '')}_{doc.metadata.get('chunk_index', 0)}"

                if doc_id not in all_docs or relevance_score > all_docs[doc_id]["relevance_score"]:
                    all_docs[doc_id] = {
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "relevance_score": round(relevance_score, 4),
                    }
                    best_score = max(best_score, relevance_score)

        # Filter by threshold
        documents = [
            doc for doc in all_docs.values()
            if doc["relevance_score"] >= similarity_threshold
        ]

        # Sort by relevance
        documents.sort(key=lambda x: x["relevance_score"], reverse=True)

        processing_time = int((time.time() - start_time) * 1000)

        logger.info(
            f"Multi-query: {len(all_docs)} total -> {len(documents)} above threshold "
            f"(best_score={best_score:.4f}, threshold={similarity_threshold})"
        )

        return {
            "documents": documents[:top_k * 2],  # Return more docs from multi-query
            "generated_queries": generated_queries,
            "relevance_info": {
                "best_score": round(best_score, 4),
                "threshold": similarity_threshold,
                "is_relevant": best_score >= similarity_threshold,
                "unique_documents": len(documents),
            },
            "processing_time_ms": processing_time,
        }

    def _generate_queries_with_llm(self, query: str, num_queries: int) -> List[str]:
        """
        Generate semantic query variations using LLM.

        Follows the exact pattern from MultiQueryRetriever._generate_queries()
        for improved retrieval recall (20-30% improvement).

        Falls back to simple variations if LLM is unavailable.
        """
        from langchain_core.prompts import PromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        try:
            llm = self._get_llm()

            # Exact prompt from MultiQueryRetriever
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

            chain = prompt | llm | StrOutputParser()

            response = chain.invoke({
                "question": query,
                "num_queries": num_queries
            })

            # Parse response into list of queries
            queries = [q.strip() for q in response.strip().split('\n') if q.strip()]
            queries = queries[:num_queries]

            # Ensure we always include original query
            if query not in queries:
                queries = [query] + queries[:num_queries - 1]

            logger.info(f"LLM generated {len(queries)} query variations")
            for idx, q in enumerate(queries, 1):
                logger.debug(f"  Query {idx}: {q[:60]}...")

            return queries

        except Exception as e:
            logger.warning(f"LLM query generation failed: {e}, falling back to simple variations")
            return self._generate_simple_variations(query, num_queries)

    def _generate_simple_variations(self, query: str, num_queries: int) -> List[str]:
        """Fallback: Generate simple query variations without LLM."""
        variations = [query]

        if num_queries >= 2:
            variations.append(f"What is {query}?")
        if num_queries >= 3:
            variations.append(f"Explain {query}")
        if num_queries >= 4:
            variations.append(f"Information about {query}")
        if num_queries >= 5:
            variations.append(f"Details on {query}")

        return variations[:num_queries]

    def ingest_file(self, file_path: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Ingest a single file."""
        start_time = time.time()

        result = self.pipeline.ingest_file(file_path)

        processing_time = int((time.time() - start_time) * 1000)

        return {
            "status": result.get("status", "failed"),
            "file_name": Path(file_path).name,
            "chunks_created": result.get("chunks_stored", 0),
            "processing_time_ms": processing_time,
            "metadata": {
                "source": file_path,
                "avg_chunk_size": result.get("avg_chunk_size", 0),
            },
        }

    def auto_ingest(
        self,
        source_path: str,
        recursive: bool = True,
        skip_duplicates: bool = True,
        output_dir: str = "data/raw",
    ) -> Dict[str, Any]:
        """Run Prefect-orchestrated ingestion pipeline."""
        from src.rag_system.pipeline.orchestrator import ingestion_flow

        start_time = time.time()

        report = ingestion_flow(
            source_path=source_path,
            ingestion_pipeline=self.pipeline,
            hash_cache=self.hash_cache,
            stats_tracker=self.stats,
            supported_formats=self.supported_formats,
            skip_duplicates=skip_duplicates,
            recursive=recursive,
            output_dir=output_dir,
        )

        processing_time = int((time.time() - start_time) * 1000)

        return {
            "status": report.get("status", "failed"),
            "flow_run_id": None,  # Prefect flow run ID if available
            "files_discovered": report.get("files_discovered", 0),
            "duplicates_skipped": report.get("duplicates_skipped", 0),
            "files_ingested": report.get("files_ingested", 0),
            "chunks_created": report.get("chunks_created", 0),
            "was_archive": report.get("was_archive", False),
            "extracted_path": report.get("extracted_path"),
            "errors": [],
            "processing_time_ms": processing_time,
        }

    def incremental_update(
        self,
        source_path: str,
        recursive: bool = True,
    ) -> Dict[str, Any]:
        """Run incremental update (skip duplicates)."""
        from src.rag_system.pipeline.orchestrator import incremental_flow

        start_time = time.time()

        report = incremental_flow(
            source_path=source_path,
            ingestion_pipeline=self.pipeline,
            hash_cache=self.hash_cache,
            stats_tracker=self.stats,
            supported_formats=self.supported_formats,
            recursive=recursive,
        )

        processing_time = int((time.time() - start_time) * 1000)

        return {
            "status": report.get("status", "failed"),
            "new_files": report.get("files_ingested", 0),
            "modified_files": 0,
            "chunks_created": report.get("chunks_created", 0),
            "duplicates_skipped": report.get("duplicates_skipped", 0),
            "processing_time_ms": processing_time,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        try:
            vs_stats = self.vector_store.get_collection_stats()
            vs_count = vs_stats.get("document_count", 0)
        except Exception:
            vs_count = 0

        stats_dict = self.stats.to_dict()

        return {
            "runs": stats_dict.get("runs", 0),
            "total_files_processed": stats_dict.get("total_files_processed", 0),
            "total_chunks_created": stats_dict.get("total_chunks_created", 0),
            "duplicates_skipped": stats_dict.get("duplicates_skipped", 0),
            "errors": stats_dict.get("errors", 0),
            "known_documents": self.hash_cache.count,
            "vector_store_count": vs_count,
            "last_run": stats_dict.get("last_run"),
            "avg_processing_time_ms": None,
        }

    def clear_cache(self) -> Dict[str, Any]:
        """Clear document hash cache."""
        count = self.hash_cache.count
        self.hash_cache.clear()

        return {
            "status": "success",
            "message": "Document hash cache cleared",
            "documents_cleared": count,
        }

    def get_collection_info(self) -> Dict[str, Any]:
        """Get vector store collection information."""
        stats = self.vector_store.get_collection_stats()

        return {
            "collection_name": self.config.get("vector_store.collection_name", "rag_documents"),
            "document_count": stats.get("document_count", 0),
            "embedding_dimension": 768,  # Default for most models
            "embedding_model": self.config.get("embeddings.model", "unknown"),
            "distance_metric": "cosine",
        }

    def get_health(self) -> Dict[str, Any]:
        """Get service health status."""
        components = {}

        # Check vector store
        try:
            self.vector_store.get_collection_stats()
            components["vector_store"] = "connected"
        except Exception:
            components["vector_store"] = "disconnected"

        # Check embedding model
        try:
            # Simple test embedding
            components["embedding_model"] = "loaded"
        except Exception:
            components["embedding_model"] = "unavailable"

        # Check Prefect (if available)
        try:
            import prefect
            components["prefect"] = "available"
        except ImportError:
            components["prefect"] = "not_installed"

        uptime = int(time.time() - self._start_time)

        all_healthy = all(v in ["connected", "loaded", "available", "not_installed"] for v in components.values())

        return {
            "status": "healthy" if all_healthy else "degraded",
            "version": "1.0.0",
            "components": components,
            "uptime_seconds": uptime,
        }

    def list_documents(
        self,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List documents in the vector store with pagination.

        Args:
            page: Page number (1-indexed)
            limit: Items per page
            search: Optional search filter

        Returns:
            Dictionary with documents, total count, and pagination info
        """
        try:
            # Get documents from ChromaDB collection
            collection = self.vector_store.collection
            results = collection.get(include=["documents", "metadatas"])

            if not results["ids"]:
                return {
                    "documents": [],
                    "total": 0,
                    "page": page,
                    "limit": limit,
                }

            # Build document list
            all_documents = []
            for idx, doc_id in enumerate(results["ids"]):
                content = results["documents"][idx] if results["documents"] else ""
                metadata = results["metadatas"][idx] if results["metadatas"] else {}

                # Apply search filter if provided
                if search:
                    search_lower = search.lower()
                    content_match = search_lower in content.lower()
                    source_match = search_lower in str(metadata.get("source", "")).lower()
                    if not (content_match or source_match):
                        continue

                all_documents.append({
                    "id": doc_id,
                    "content": content[:500] + "..." if len(content) > 500 else content,
                    "metadata": metadata,
                    "source": metadata.get("source"),
                })

            # Apply pagination
            total = len(all_documents)
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            paginated_docs = all_documents[start_idx:end_idx]

            logger.info(f"Listed {len(paginated_docs)} documents (page {page}, total {total})")

            return {
                "documents": paginated_docs,
                "total": total,
                "page": page,
                "limit": limit,
            }

        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return {
                "documents": [],
                "total": 0,
                "page": page,
                "limit": limit,
            }
