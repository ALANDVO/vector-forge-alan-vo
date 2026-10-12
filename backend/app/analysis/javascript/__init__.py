from __future__ import annotations

from app.analysis.javascript.parser import parse_javascript_file, parse_directory, ParseResult, JSNode
from app.analysis.javascript.graph import build_call_graph, resolve_imports, find_call_edges, CallGraph
from app.analysis.javascript.evidence import store_parse_results, build_call_edges, AnalysisResult
from app.analysis.javascript.tool import analyze_javascript_application, analyze_single_file, get_supported_extensions, is_supported_file

__all__ = [
    "parse_javascript_file",
    "parse_directory",
    "ParseResult",
    "JSNode",
    "build_call_graph",
    "resolve_imports",
    "find_call_edges",
    "CallGraph",
    "store_parse_results",
    "build_call_edges",
    "AnalysisResult",
    "analyze_javascript_application",
    "analyze_single_file",
    "get_supported_extensions",
    "is_supported_file",
]