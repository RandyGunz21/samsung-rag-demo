"""
Pipeline Orchestrator using Prefect.

Implements FR-ORCH-001: Automated Data Pipeline
Implements FR-ORCH-002: Incremental Knowledge Updates
Implements FR-ORCH-003: Pipeline Monitoring
Implements OR-PIPE-001: Prefect Orchestration Framework

Uses Prefect for workflow orchestration with:
- @flow and @task decorators for pipeline stages
- Automatic retries with exponential backoff
- Caching for deduplication
- Comprehensive logging and monitoring
"""

import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from prefect import flow, task, get_run_logger
from prefect.tasks import exponential_backoff

from src.rag_system.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentHashCache:
    """Manages document hash cache for deduplication."""

    def __init__(self, hash_file: Union[str, Path] = "data/processed/.document_hashes.json"):
        self._hash_file = Path(hash_file)
        self._processed_hashes: Dict[str, str] = {}
        self._load_hashes()

    def _load_hashes(self):
        """Load previously processed document hashes."""
        if self._hash_file.exists():
            try:
                with open(self._hash_file, "r") as f:
                    self._processed_hashes = json.load(f)
                logger.info(f"Loaded {len(self._processed_hashes)} document hashes")
            except Exception as e:
                logger.warning(f"Could not load hash file: {e}")
                self._processed_hashes = {}

    def save_hashes(self):
        """Save processed document hashes."""
        self._hash_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._hash_file, "w") as f:
            json.dump(self._processed_hashes, f, indent=2)
        logger.debug(f"Saved {len(self._processed_hashes)} document hashes")

    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file content."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def is_duplicate(self, file_path: Path) -> bool:
        """Check if file has already been processed."""
        file_hash = self.compute_file_hash(file_path)
        file_key = str(file_path.absolute())

        if file_key in self._processed_hashes:
            if self._processed_hashes[file_key] == file_hash:
                return True
            else:
                logger.info(f"File modified, will re-process: {file_path.name}")
                return False
        return False

    def mark_processed(self, file_path: Path):
        """Mark file as processed."""
        file_hash = self.compute_file_hash(file_path)
        file_key = str(file_path.absolute())
        self._processed_hashes[file_key] = file_hash

    def clear(self):
        """Clear the hash cache."""
        self._processed_hashes = {}
        if self._hash_file.exists():
            self._hash_file.unlink()

    @property
    def count(self) -> int:
        return len(self._processed_hashes)


# =============================================================================
# Prefect Tasks - Pipeline Stages
# =============================================================================

@task(
    name="extract_archive",
    description="Extract archives (.7z, .zip) for processing",
    retries=2,
    retry_delay_seconds=exponential_backoff(backoff_factor=2),
)
def extract_archive_task(
    source_path: str,
    output_dir: str = "data/raw"
) -> Dict[str, Any]:
    """
    Prefect Task: Extract archives (.7z, .zip).

    Handles FR-ORCH-001: Automated extraction of SecondDatasets.7z
    """
    prefect_logger = get_run_logger()
    source = Path(source_path)
    result = {
        "source_path": source_path,
        "was_archive": False,
        "extracted_path": None,
        "status": "success",
    }

    if not source.exists():
        result["status"] = "error"
        result["error"] = f"Source path not found: {source_path}"
        prefect_logger.error(result["error"])
        return result

    # Check if archive
    if source.suffix.lower() in [".7z", ".zip", ".tar", ".gz"]:
        prefect_logger.info(f"Extracting archive: {source}")
        extract_path = Path(output_dir) / source.stem

        try:
            if source.suffix.lower() == ".7z":
                # Try 7z command first
                try:
                    proc = subprocess.run(
                        ["7z", "x", str(source), f"-o{extract_path}", "-y"],
                        capture_output=True,
                        text=True,
                    )
                    if proc.returncode != 0:
                        raise Exception(f"7z extraction failed: {proc.stderr}")
                except FileNotFoundError:
                    # 7z not installed, try Python fallback
                    prefect_logger.warning("7z not found, attempting py7zr")
                    import py7zr
                    with py7zr.SevenZipFile(source, mode='r') as z:
                        z.extractall(extract_path)

            elif source.suffix.lower() == ".zip":
                shutil.unpack_archive(source, extract_path)
            else:
                shutil.unpack_archive(source, extract_path)

            result["extracted_path"] = str(extract_path)
            result["was_archive"] = True
            prefect_logger.info(f"Extracted to: {extract_path}")

        except ImportError:
            result["status"] = "error"
            result["error"] = "7z extraction requires either '7z' command or 'py7zr' package"
            prefect_logger.error(result["error"])
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            prefect_logger.error(f"Archive extraction failed: {e}")

    return result


@task(
    name="discover_files",
    description="Discover files to process from source path",
)
def discover_files_task(
    source_path: str,
    supported_formats: List[str],
    recursive: bool = True
) -> Dict[str, Any]:
    """Prefect Task: Discover files to process."""
    prefect_logger = get_run_logger()
    source = Path(source_path)
    result = {
        "source_path": source_path,
        "discovered_files": [],
        "total_discovered": 0,
        "status": "success",
    }

    if not source.exists():
        result["status"] = "error"
        result["error"] = f"Source path not found: {source_path}"
        return result

    files_to_process = []

    if source.is_file():
        files_to_process = [str(source)]
    elif source.is_dir():
        pattern = "**/*" if recursive else "*"
        for file_path in source.glob(pattern):
            if file_path.is_file():
                ext = file_path.suffix.lower().lstrip(".")
                if ext in supported_formats:
                    files_to_process.append(str(file_path))

    result["discovered_files"] = files_to_process
    result["total_discovered"] = len(files_to_process)

    prefect_logger.info(f"Discovered {len(files_to_process)} files to process")
    return result


@task(
    name="filter_duplicates",
    description="Filter out already processed files for incremental updates",
)
def filter_duplicates_task(
    discovered_files: List[str],
    hash_cache: DocumentHashCache,
    skip_duplicates: bool = True
) -> Dict[str, Any]:
    """
    Prefect Task: Filter out duplicate files.

    Implements FR-ORCH-002: Deduplicate documents if re-ingested
    """
    prefect_logger = get_run_logger()
    result = {
        "files_to_ingest": [],
        "duplicates_skipped": 0,
        "status": "success",
    }

    if not skip_duplicates:
        result["files_to_ingest"] = discovered_files
        return result

    files_to_ingest = []
    duplicates_skipped = 0

    for file_path_str in discovered_files:
        file_path = Path(file_path_str)
        if hash_cache.is_duplicate(file_path):
            duplicates_skipped += 1
        else:
            files_to_ingest.append(file_path_str)

    result["files_to_ingest"] = files_to_ingest
    result["duplicates_skipped"] = duplicates_skipped

    if duplicates_skipped > 0:
        prefect_logger.info(f"Skipping {duplicates_skipped} duplicate files")

    return result


@task(
    name="ingest_file",
    description="Ingest a single file into vector store",
    retries=3,
    retry_delay_seconds=exponential_backoff(backoff_factor=2),
)
def ingest_file_task(
    file_path: str,
    ingestion_pipeline,
    hash_cache: DocumentHashCache
) -> Dict[str, Any]:
    """Prefect Task: Ingest a single file."""
    prefect_logger = get_run_logger()

    try:
        result = ingestion_pipeline.ingest_file(file_path)

        if result["status"] == "success":
            hash_cache.mark_processed(Path(file_path))
            prefect_logger.info(f"Ingested: {Path(file_path).name} ({result.get('chunks_stored', 0)} chunks)")

        return result

    except Exception as e:
        prefect_logger.error(f"Error ingesting {file_path}: {e}")
        return {
            "file": file_path,
            "status": "failed",
            "error": str(e),
        }


@task(
    name="generate_report",
    description="Generate pipeline execution report",
)
def generate_report_task(
    ingestion_results: List[Dict],
    discovery_result: Dict,
    dedup_result: Dict,
    archive_result: Dict,
    stats_tracker: "PipelineStats"
) -> Dict[str, Any]:
    """
    Prefect Task: Generate pipeline report.

    Implements FR-ORCH-003: Pipeline Monitoring
    """
    prefect_logger = get_run_logger()

    total_chunks = sum(r.get("chunks_stored", 0) for r in ingestion_results if r.get("status") == "success")
    errors = sum(1 for r in ingestion_results if r.get("status") == "failed")

    report = {
        "timestamp": datetime.now().isoformat(),
        "source": discovery_result.get("source_path"),
        "was_archive": archive_result.get("was_archive", False),
        "files_discovered": discovery_result.get("total_discovered", 0),
        "duplicates_skipped": dedup_result.get("duplicates_skipped", 0),
        "files_ingested": len(dedup_result.get("files_to_ingest", [])),
        "chunks_created": total_chunks,
        "errors": errors,
        "status": "success" if errors == 0 else "partial",
    }

    # Update statistics
    stats_tracker.update(report)

    prefect_logger.info(
        f"Pipeline complete: {report['files_ingested']}/{report['files_discovered']} files, "
        f"{report['chunks_created']} chunks, {report['duplicates_skipped']} duplicates skipped"
    )

    return report


# =============================================================================
# Prefect Flows - Pipeline Orchestration
# =============================================================================

@flow(
    name="RAG Document Ingestion Pipeline",
    description="Automated document ingestion with deduplication and monitoring",
    log_prints=True,
)
def ingestion_flow(
    source_path: str,
    ingestion_pipeline,
    hash_cache: DocumentHashCache,
    stats_tracker: "PipelineStats",
    supported_formats: List[str],
    skip_duplicates: bool = True,
    recursive: bool = True,
    output_dir: str = "data/raw",
) -> Dict[str, Any]:
    """
    Prefect Flow: Complete document ingestion pipeline.

    Stages:
    1. Extract archive (if applicable)
    2. Discover files
    3. Filter duplicates
    4. Ingest files
    5. Generate report
    """
    prefect_logger = get_run_logger()
    prefect_logger.info(f"Starting ingestion pipeline for: {source_path}")

    # Stage 1: Extract archive
    archive_result = extract_archive_task(source_path, output_dir)

    if archive_result.get("status") == "error":
        return {"status": "error", "error": archive_result.get("error")}

    # Use extracted path if archive was extracted
    effective_path = archive_result.get("extracted_path") or source_path

    # Stage 2: Discover files
    discovery_result = discover_files_task(effective_path, supported_formats, recursive)

    if discovery_result.get("status") == "error":
        return {"status": "error", "error": discovery_result.get("error")}

    # Stage 3: Filter duplicates
    dedup_result = filter_duplicates_task(
        discovery_result["discovered_files"],
        hash_cache,
        skip_duplicates
    )

    # Stage 4: Ingest files
    ingestion_results = []
    files_to_ingest = dedup_result["files_to_ingest"]

    for file_path in files_to_ingest:
        result = ingest_file_task(file_path, ingestion_pipeline, hash_cache)
        ingestion_results.append(result)

    # Save hash cache after all ingestions
    hash_cache.save_hashes()

    # Stage 5: Generate report
    report = generate_report_task(
        ingestion_results,
        discovery_result,
        dedup_result,
        archive_result,
        stats_tracker
    )

    return report


@flow(
    name="Incremental Knowledge Update",
    description="Process only new or modified documents",
    log_prints=True,
)
def incremental_flow(
    source_path: str,
    ingestion_pipeline,
    hash_cache: DocumentHashCache,
    stats_tracker: "PipelineStats",
    supported_formats: List[str],
    recursive: bool = True,
) -> Dict[str, Any]:
    """
    Prefect Flow: Incremental update (always skip duplicates).

    Implements FR-ORCH-002: Incremental Knowledge Updates
    """
    return ingestion_flow(
        source_path=source_path,
        ingestion_pipeline=ingestion_pipeline,
        hash_cache=hash_cache,
        stats_tracker=stats_tracker,
        supported_formats=supported_formats,
        skip_duplicates=True,
        recursive=recursive,
    )


# =============================================================================
# Pipeline Statistics Tracker
# =============================================================================

class PipelineStats:
    """Tracks pipeline execution statistics."""

    def __init__(self):
        self.runs = 0
        self.total_files_processed = 0
        self.total_chunks_created = 0
        self.duplicates_skipped = 0
        self.errors = 0
        self.last_run = None

    def update(self, report: Dict[str, Any]):
        """Update stats from pipeline report."""
        self.runs += 1
        self.total_files_processed += report.get("files_ingested", 0)
        self.total_chunks_created += report.get("chunks_created", 0)
        self.duplicates_skipped += report.get("duplicates_skipped", 0)
        self.errors += report.get("errors", 0)
        self.last_run = report.get("timestamp")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "runs": self.runs,
            "total_files_processed": self.total_files_processed,
            "total_chunks_created": self.total_chunks_created,
            "duplicates_skipped": self.duplicates_skipped,
            "errors": self.errors,
            "last_run": self.last_run,
        }


# =============================================================================
# Pipeline Orchestrator - High-Level API
# =============================================================================

class PipelineOrchestrator:
    """
    Prefect-based Pipeline Orchestrator for automated document ingestion.

    Features:
    - Prefect @flow and @task decorators for pipeline stages
    - Automatic retries with exponential backoff
    - Archive extraction (.7z, .zip)
    - Document deduplication
    - Incremental updates
    - Comprehensive monitoring and statistics
    """

    def __init__(self, ingestion_pipeline, vector_store, config: Optional[Dict] = None):
        """
        Initialize orchestrator.

        Args:
            ingestion_pipeline: IngestionPipeline instance
            vector_store: ChromaVectorStore instance
            config: Optional configuration dictionary
        """
        self.pipeline = ingestion_pipeline
        self.vector_store = vector_store
        self.config = config or {}

        # Document hash cache for deduplication
        hash_file = self.config.get("hash_file", "data/processed/.document_hashes.json")
        self.hash_cache = DocumentHashCache(hash_file)

        # Statistics tracker
        self.stats = PipelineStats()

        # Supported formats from document loader
        self.supported_formats = list(self.pipeline.document_loader.supported_formats)

        logger.info("PipelineOrchestrator initialized with Prefect orchestration")

    def run(
        self,
        source_path: Union[str, Path],
        skip_duplicates: bool = True,
        recursive: bool = True,
        output_dir: str = "data/raw",
    ) -> Dict[str, Any]:
        """
        Run the full orchestrated pipeline.

        Args:
            source_path: Path to file, directory, or archive
            skip_duplicates: Whether to skip already processed files
            recursive: Whether to process subdirectories
            output_dir: Directory for extracted archives

        Returns:
            Pipeline execution report
        """
        logger.info(f"Starting Prefect orchestrated pipeline for: {source_path}")

        return ingestion_flow(
            source_path=str(source_path),
            ingestion_pipeline=self.pipeline,
            hash_cache=self.hash_cache,
            stats_tracker=self.stats,
            supported_formats=self.supported_formats,
            skip_duplicates=skip_duplicates,
            recursive=recursive,
            output_dir=output_dir,
        )

    def run_incremental(
        self,
        source_path: Union[str, Path],
        recursive: bool = True,
    ) -> Dict[str, Any]:
        """
        Run incremental update (always skip duplicates).

        Implements FR-ORCH-002: Incremental Knowledge Updates
        """
        return incremental_flow(
            source_path=str(source_path),
            ingestion_pipeline=self.pipeline,
            hash_cache=self.hash_cache,
            stats_tracker=self.stats,
            supported_formats=self.supported_formats,
            recursive=recursive,
        )

    def run_full_reindex(
        self,
        source_path: Union[str, Path],
        recursive: bool = True,
    ) -> Dict[str, Any]:
        """
        Run full reindex (process all files, even duplicates).
        """
        return self.run(
            source_path=source_path,
            skip_duplicates=False,
            recursive=recursive,
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get pipeline execution statistics."""
        # Get vector store count via collection stats
        try:
            vs_stats = self.vector_store.get_collection_stats()
            vs_count = vs_stats.get("document_count", 0)
        except Exception:
            vs_count = 0

        return {
            **self.stats.to_dict(),
            "known_documents": self.hash_cache.count,
            "vector_store_count": vs_count,
        }

    def clear_hash_cache(self):
        """Clear the document hash cache (for full re-ingestion)."""
        self.hash_cache.clear()
        logger.info("Document hash cache cleared")


def create_orchestrator(rag_system) -> PipelineOrchestrator:
    """
    Factory function to create orchestrator from RAGSystem.

    Args:
        rag_system: RAGSystem instance

    Returns:
        Configured PipelineOrchestrator
    """
    return PipelineOrchestrator(
        ingestion_pipeline=rag_system.pipeline,
        vector_store=rag_system.vector_store,
        config=rag_system.config._config if hasattr(rag_system.config, '_config') else {},
    )
