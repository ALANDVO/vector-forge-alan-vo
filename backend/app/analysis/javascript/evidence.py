from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.analysis.javascript.parser import JSNode, ParseResult
from app.models.evidence import EvidenceType
from app.services.evidence_service import EvidenceService


@dataclass
class AnalysisResult:
    session_id: str
    evidence_count: int = 0
    functions: int = 0
    calls: int = 0
    imports: int = 0
    classes: int = 0
    files: int = 0
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


async def store_parse_results(
    service: EvidenceService,
    session_id: str,
    parse_results: list[ParseResult],
) -> AnalysisResult:
    """Convert parse results to evidence records and store them."""
    result = AnalysisResult(session_id=session_id)

    # Collect all nodes first
    all_nodes: list[JSNode] = []
    for pr in parse_results:
        all_nodes.extend(pr.nodes)
        result.files += 1
        result.errors.extend(pr.errors)

    # Create evidence records for functions
    func_nodes = [n for n in all_nodes if n.type == "function"]
    class_nodes = [n for n in all_nodes if n.type == "class"]

    # Batch create functions
    func_records = []
    for node in func_nodes:
        func_records.append(
            await service.create_evidence(
                session_id=session_id,
                evidence_type=EvidenceType.FUNCTION,
                name=node.name or "anonymous",
                qualified_name=node.qualified_name,
                source_file=node.properties.get("file_path"),
                source_line=node.start_line,
                source_column=node.start_column,
                source_end_line=node.end_line,
                source_end_column=node.end_column,
                properties={
                    "kind": node.properties.get("kind", "declaration"),
                    "async": node.properties.get("async", False),
                    "module": node.properties.get("module"),
                },
                provenance={
                    "parser": "regex",
                    "source_file": node.properties.get("file_path"),
                },
            )
        )
    result.functions = len(func_records)
    result.evidence_count += len(func_records)

    # Batch create classes
    class_records = []
    for node in class_nodes:
        class_records.append(
            await service.create_evidence(
                session_id=session_id,
                evidence_type=EvidenceType.CLASS,
                name=node.name or "anonymous",
                qualified_name=node.qualified_name,
                source_file=node.properties.get("file_path"),
                source_line=node.start_line,
                source_column=node.start_column,
                source_end_line=node.end_line,
                source_end_column=node.end_column,
                properties={
                    "kind": node.properties.get("kind", "declaration"),
                    "module": node.properties.get("module"),
                },
                provenance={
                    "parser": "regex",
                    "source_file": node.properties.get("file_path"),
                },
            )
        )
    result.classes = len(class_records)
    result.evidence_count += len(class_records)

    # Create import records
    import_records = []
    for pr in parse_results:
        for imp in pr.imports:
            import_records.append(
                await service.create_evidence(
                    session_id=session_id,
                    evidence_type=EvidenceType.IMPORT,
                    name=imp.get("name") or imp.get("module", "unknown"),
                    qualified_name=f"{pr.module_name}.{imp.get('name') or imp.get('module', 'unknown')}",
                    source_file=pr.file_path,
                    source_line=imp.get("line"),
                    source_column=imp.get("column"),
                    properties={
                        "module": imp.get("module"),
                        "kind": imp.get("kind", "named"),
                        "is_external": not imp.get("module", "").startswith("."),
                    },
                    provenance={
                        "parser": "regex",
                        "source_file": pr.file_path,
                    },
                )
            )
    result.imports = len(import_records)
    result.evidence_count += len(import_records)

    # Create file records
    for pr in parse_results:
        await service.create_evidence(
            session_id=session_id,
            evidence_type=EvidenceType.FILE,
            name=pr.file_path,
            qualified_name=pr.module_name,
            source_file=pr.file_path,
            properties={
                "extension": pr.file_path.split(".")[-1] if "." in pr.file_path else "",
                "function_count": len([n for n in pr.nodes if n.type == "function"]),
                "class_count": len([n for n in pr.nodes if n.type == "class"]),
                "import_count": len(pr.imports),
                "export_count": len(pr.exports),
            },
            provenance={
                "parser": "regex",
            },
        )
        result.evidence_count += 1

    # Create module records
    modules_seen = set()
    for pr in parse_results:
        if pr.module_name not in modules_seen:
            modules_seen.add(pr.module_name)
            await service.create_evidence(
                session_id=session_id,
                evidence_type=EvidenceType.MODULE,
                name=pr.module_name,
                qualified_name=pr.module_name,
                source_file=pr.file_path,
                properties={
                    "file_count": 1,  # Will be aggregated
                },
                provenance={
                    "parser": "regex",
                },
            )
            result.evidence_count += 1

    return result


async def build_call_edges(
    service: EvidenceService,
    session_id: str,
    parse_results: list[ParseResult],
) -> int:
    """Build call edges between functions."""
    # Build function map
    func_map: dict[str, str] = {}  # qualified_name -> evidence_id
    for pr in parse_results:
        for node in pr.nodes:
            if node.type == "function":
                # We need to find the evidence ID - in practice we'd track this during creation
                pass

    # For now, return 0 - edges would be built in a second pass
    # with proper evidence ID tracking
    return 0