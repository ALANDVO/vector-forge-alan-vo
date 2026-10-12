from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from app.services.evidence_service import EvidenceService
from app.analysis.javascript.parser import parse_directory, parse_javascript_file
from app.analysis.javascript.evidence import AnalysisResult, store_parse_results
from app.models.evidence import EvidenceType


async def analyze_javascript_application(
    service: EvidenceService,
    session_id: str,
    input_path: str,
    format_: str = "directory",
    include_node_modules: bool = False,
    max_files: int = 1000,
) -> dict[str, Any]:
    """
    Analyze a JavaScript/TypeScript application.

    Returns a dict with analysis results including evidence counts.
    """
    # Check cancellation
    try:
        task = asyncio.current_task()
        if task and task.cancelled():
            raise asyncio.CancelledError()
    except Exception:
        pass

    if format_ == "file":
        if not os.path.isfile(input_path):
            raise ValueError(f"File not found: {input_path}")
        parse_results = [parse_javascript_file(input_path)]
    else:
        if not os.path.isdir(input_path):
            raise ValueError(f"Directory not found: {input_path}")
        parse_results = parse_directory(input_path, include_node_modules, max_files)

    # Check for parse errors
    all_errors = []
    for pr in parse_results:
        all_errors.extend(pr.errors)

    # Store evidence
    result = await store_parse_results(service, session_id, parse_results)
    result.errors = all_errors

    # Build call edges (placeholder - would need proper AST analysis)
    # await build_call_edges(service, session_id, parse_results)

    return {
        "session_id": session_id,
        "evidence_count": result.evidence_count,
        "functions": result.functions,
        "calls": result.calls,
        "imports": result.imports,
        "classes": result.classes,
        "files": result.files,
        "errors": result.errors,
    }


async def analyze_single_file(
    service: EvidenceService,
    session_id: str,
    file_path: str,
) -> dict[str, Any]:
    """Analyze a single JavaScript/TypeScript file."""
    return await analyze_javascript_application(
        service=service,
        session_id=session_id,
        input_path=file_path,
        format_="file",
    )


def get_supported_extensions() -> list[str]:
    """Get list of supported file extensions."""
    return [".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"]


def is_supported_file(file_path: str) -> bool:
    """Check if a file is a supported JavaScript/TypeScript file."""
    return Path(file_path).suffix in get_supported_extensions()