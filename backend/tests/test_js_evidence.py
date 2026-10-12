import pytest
import pytest_asyncio
import tempfile
import os
from pathlib import Path

from app.core.database import init_db, close_db, get_session_factory
from app.models.evidence import Base
from app.services.evidence_service import EvidenceService
from app.analysis.javascript.parser import parse_javascript_file
from app.analysis.javascript.evidence import store_parse_results, AnalysisResult
from app.analysis.javascript.tool import analyze_javascript_application



@pytest_asyncio.fixture
async def evidence_service(db_session):
    return EvidenceService(db_session)


@pytest.mark.asyncio
async def test_store_parse_results(evidence_service):
    # Create a test session
    session = await evidence_service.create_session("javascript", "/test/path", "abc123")

    # Parse a simple JS file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write("""
function hello() { return 'world'; }
async function fetchData() { return await fetch('/api'); }
class User { constructor(name) { this.name = name; } }
import React from 'react';
export { hello, fetchData };
""")
        f.flush()
        try:
            parse_result = parse_javascript_file(f.name)
            result = await store_parse_results(evidence_service, session.id, [parse_result])

            assert result.session_id == session.id
            assert result.functions == 2
            assert result.classes == 1
            assert result.imports >= 1
            assert result.files == 1
            assert result.evidence_count >= 5  # 2 functions + 1 class + 1 import + 1 file + 1 module
        finally:
            os.unlink(f.name)


@pytest.mark.asyncio
async def test_analyze_javascript_application(evidence_service):
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        (Path(tmpdir) / "main.js").write_text("""
function main() { helper(); }
function helper() { return 42; }
import { something } from './utils';
""")
        (Path(tmpdir) / "utils.js").write_text("""
export function util() { return 'util'; }
""")

        session = await evidence_service.create_session("javascript", tmpdir, "hash123")
        result = await analyze_javascript_application(
            service=evidence_service,
            session_id=session.id,
            input_path=tmpdir,
            format_="directory",
        )

        assert result["session_id"] == session.id
        assert result["functions"] == 3  # main, helper, util
        assert result["imports"] >= 0
        assert result["files"] == 2
        assert result["evidence_count"] > 0


@pytest.mark.asyncio
async def test_analyze_single_file(evidence_service):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write("function single() { return 'test'; }")
        f.flush()
        try:
            session = await evidence_service.create_session("javascript", f.name, "hash456")
            result = await analyze_javascript_application(
                service=evidence_service,
                session_id=session.id,
                input_path=f.name,
                format_="file",
            )

            assert result["session_id"] == session.id
            assert result["functions"] == 1
            assert result["files"] == 1
        finally:
            os.unlink(f.name)