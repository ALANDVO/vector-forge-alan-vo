from __future__ import annotations

import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from app.analysis.binary.snapshot_cache import SnapshotCache, compute_target_hash

logger = logging.getLogger(__name__)


class GhidraAnalysisError(RuntimeError):
    """Error during Ghidra analysis."""


class GhidraProvider:
    """Provider for launching Ghidra headless analyzer."""

    def __init__(self, cache: SnapshotCache | None = None):
        self.cache = cache or SnapshotCache()
        self._ghidra_path: Optional[Path] = None
        self._max_memory_mb: int = 2048

    @property
    def ghidra_path(self) -> Path | None:
        """Path to Ghidra installation directory."""
        return self._ghidra_path

    @ghidra_path.setter
    def ghidra_path(self, value: Path | str | None) -> None:
        """Set Ghidra installation path."""
        if value is None:
            self._ghidra_path = None
        else:
            self._ghidra_path = Path(value).resolve()
            if not self._ghidra_path.exists():
                logger.warning("ghidra_path_not_found", path=str(self._ghidra_path))

    @property
    def max_memory_mb(self) -> int:
        """Maximum memory in MB for Ghidra analysis."""
        return self._max_memory_mb

    @max_memory_mb.setter
    def max_memory_mb(self, value: int) -> None:
        self._max_memory_mb = max(64, value)

    async def analyze(
        self,
        target_path: str | Path,
        session_id: str,
        input_path: str | None = None,
    ) -> Dict[str, Any]:
        """
        Launch Ghidra headless analyzer on a binary target.

        Returns analysis results dict with evidence data.
        """
        target_path = Path(target_path).resolve()
        if not target_path.exists():
            msg = f"Target not found: {target_path}"
            logger.error("target_not_found", path=str(target_path))
            raise GhidraAnalysisError(msg)

        # Compute content hash for cache lookup
        content = target_path.read_bytes()
        target_hash = compute_target_hash(content)

        # Check cache first
        cached = await self.cache.get(target_hash)
        if cached is not None:
            logger.info("analysis_cached", target_hash=target_hash[:16])
            return {
                "session_id": session_id,
                "target_path": str(target_path),
                "target_hash": target_hash,
                "evidence": cached["evidence"],
                "from_cache": True,
            }

        # Launch Ghidra headless
        result = await self._launch_ghidra(content, target_path, session_id)
        if result.get("error"):
            raise GhidraAnalysisError(result["error"])

        # Cache the result
        await self.cache.set(target_hash, result, session_id)

        return {
            "session_id": session_id,
            "target_path": str(target_path),
            "target_hash": target_hash,
            "evidence": result,
            "from_cache": False,
        }

    async def _launch_ghidra(
        self,
        content: bytes,
        target_path: Path,
        session_id: str,
    ) -> Dict[str, Any]:
        """Internal method to launch Ghidra headless analyzer."""
        jar_path = self._find_ghidra_jar()
        if jar_path is None:
            return {
                "error": "Ghidra not installed. Please set ghidra_path on the provider.",
                "session_id": session_id,
            }

        # Write target to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # Build ghidra command
            cmd = [
                "java",
                "-Xmx{}m".format(self._max_memory_mb),
                "-jar",
                str(jar_path),
                str(target_path),
                "-process",
                "-headless",
                "-log",
                "INFO",
            ]

            logger.info("launching_ghidra", cmd=["java", "-Xmx..."], target=str(target_path))

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await proc.communicate(timeout=300)

            if proc.returncode != 0:
                error_msg = stderr.decode(errors="replace")[:2000]
                logger.error(
                    "ghidra_failed",
                    returncode=proc.returncode,
                    stderr=error_msg,
                    session_id=session_id,
                )
                return {"error": f"Ghidra analysis failed: {error_msg}", "session_id": session_id}

            # Parse output for analysis results
            result = self._parse_ghidra_output(stdout.decode(errors="replace"))
            return result

        except asyncio.TimeoutError:
            logger.error("ghidra_timeout", session_id=session_id)
            return {"error": "Ghidra analysis timed out after 300s", "session_id": session_id}
        finally:
            try:
                target_path.unlink(missing_ok=True)
            except Exception:
                pass
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass

    def _find_ghidra_jar(self) -> Optional[Path]:
        """Find the Ghidra launcher JAR file."""
        if self._ghidra_path is None:
            return None
        # Look for common Ghidra JAR names
        candidates = [
            self._ghidra_path / "ghidra.jar",
            self._ghidra_path / "support" / "ghidra.jar",
        ]
        for c in candidates:
            if c.exists():
                return c
        # Fallback: check PATH
        import shutil
        if shutil.which("ghidra"):
            return Path("ghidra")
        return None

    def _parse_ghidra_output(self, output: str) -> Dict[str, Any]:
        """Parse Ghidra headless analysis output."""
        # Placeholder: in a real implementation, this would parse
        # Ghidra's structured output (JSON, XML, or custom format)
        # For now, return a minimal structured result
        return {
            "target": output.splitlines()[0] if output else "",
            "functions": [],
            "imports": [],
            "exports": [],
            "symbols": [],
            "analysis_complete": True,
        }

    async def cancel(self, session_id: str) -> bool:
        """Cancel an ongoing Ghidra analysis session."""
        # In a full implementation, this would send a cancel command
        # to the running Ghidra process. For now, return False
        # to indicate cancellation is not yet supported.
        logger.warning("cancellation_not_implemented", session_id=session_id)
        return False
