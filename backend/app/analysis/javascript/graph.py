from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from app.analysis.javascript.parser import JSNode, ParseResult


@dataclass
class CallGraph:
    nodes: dict[str, JSNode] = field(default_factory=dict)  # qualified_name -> node
    edges: list[tuple[str, str, str]] = field(default_factory=list)  # (caller, callee, edge_type)
    modules: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))  # module -> qualified_names


def build_call_graph(parse_results: list[ParseResult]) -> CallGraph:
    """Build a call graph from parse results."""
    graph = CallGraph()

    # First pass: register all nodes
    for result in parse_results:
        for node in result.nodes:
            graph.nodes[node.qualified_name] = node
            graph.modules[result.module_name].append(node.qualified_name)

    # Second pass: build edges from call expressions
    # This is a simplified approach - in reality you'd need a proper AST walker
    for result in parse_results:
        # For each function, we'd need to parse its body for calls
        # This is a placeholder for the actual implementation
        pass

    return graph


def resolve_imports(parse_results: list[ParseResult]) -> dict[str, str]:
    """Resolve import statements to local modules."""
    # Map of module specifier -> qualified_name
    export_map: dict[str, str] = {}

    for result in parse_results:
        for exp in result.exports:
            export_map[f"{result.module_name}.{exp['name']}"] = f"{result.module_name}.{exp['name']}"
            export_map[exp["name"]] = f"{result.module_name}.{exp['name']}"

    return export_map


def find_call_edges(parse_results: list[ParseResult], export_map: dict[str, str]) -> list[tuple[str, str, str]]:
    """Find call edges between functions."""
    edges = []

    # Build a map of all function names for quick lookup
    func_map: dict[str, JSNode] = {}
    for result in parse_results:
        for node in result.nodes:
            if node.type == "function":
                func_map[node.name] = node
                if node.qualified_name:
                    func_map[node.qualified_name] = node

    # This is a simplified heuristic - would need proper AST analysis for accuracy
    for result in parse_results:
        try:
            with open(result.file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        # Find all function bodies and look for calls within them
        for node in result.nodes:
            if node.type != "function":
                continue

            # Extract function body (simplified - between first { and matching })
            body_start = content.find("{", content.find(node.name))
            if body_start == -1:
                continue

            # Find matching brace
            brace_count = 0
            body_end = body_start
            for i, ch in enumerate(content[body_start:], body_start):
                if ch == "{":
                    brace_count += 1
                elif ch == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        body_end = i
                        break

            body = content[body_start:body_end]

            # Find calls in body
            import re
            call_pattern = re.compile(r"(\w+(?:\.\w+)*)\s*\(")
            for match in call_pattern.finditer(body):
                call_name = match.group(1)
                # Try to resolve the call
                callee = func_map.get(call_name)
                if callee:
                    edges.append((node.qualified_name, callee.qualified_name, "calls"))

    return edges