"""
RAG Service - Ingestion Routes.

Endpoints for document ingestion and pipeline operations.
"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..schemas import (
    AutoIngestRequest,
    AutoIngestResponse,
    IncrementalRequest,
    IncrementalResponse,
    IngestResponse,
)
from ..dependencies import get_rag_engine

router = APIRouter(prefix="/api/v1", tags=["Ingestion"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_file(
    file: UploadFile = File(...),
    metadata: str = Form(default="{}"),
    engine=Depends(get_rag_engine),
):
    """
    Upload and ingest a single document file.

    Supported formats: PDF, DOCX, TXT, MD, HTML, etc.
    """
    try:
        # Save uploaded file to temp location
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        try:
            result = engine.ingest_file(temp_path)

            return IngestResponse(
                status=result["status"],
                file_name=file.filename,
                chunks_created=result["chunks_created"],
                processing_time_ms=result["processing_time_ms"],
                metadata=result["metadata"],
            )
        finally:
            # Cleanup temp file
            Path(temp_path).unlink(missing_ok=True)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-ingest", response_model=AutoIngestResponse)
async def auto_ingest(
    request: AutoIngestRequest,
    engine=Depends(get_rag_engine),
):
    """
    Trigger Prefect-orchestrated ingestion pipeline.

    Supports files, directories, and archives (.7z, .zip).
    """
    # Check if source path exists
    source = Path(request.source_path)
    if not source.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Source path not found: {request.source_path}"
        )

    try:
        result = engine.auto_ingest(
            source_path=request.source_path,
            recursive=request.recursive,
            skip_duplicates=request.skip_duplicates,
            output_dir=request.output_dir,
        )

        return AutoIngestResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/incremental", response_model=IncrementalResponse)
async def incremental_update(
    request: IncrementalRequest,
    engine=Depends(get_rag_engine),
):
    """
    Process only new or modified documents.

    Implements FR-ORCH-002: Incremental Knowledge Updates.
    """
    # Check if source path exists
    source = Path(request.source_path)
    if not source.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Source path not found: {request.source_path}"
        )

    try:
        result = engine.incremental_update(
            source_path=request.source_path,
            recursive=request.recursive,
        )

        return IncrementalResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
