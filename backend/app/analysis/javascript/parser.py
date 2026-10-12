from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# JavaScript/TypeScript parsing using regex patterns (since Python ast doesn't parse JS)
# For production, consider using a proper JS parser like esprima via subprocess or tree-sitter


@dataclass
class JSNode:
    type: str
    name: Optional[str] = None
    qualified_name: Optional[str] = None
    start_line: int = 0
    start_column: int = 0
    end_line: int = 0
    end_column: int = 0
    properties: dict = field(default_factory=dict)
    children: list["JSNode"] = field(default_factory=list)


@dataclass
class ParseResult:
    file_path: str
    module_name: str
    nodes: list[JSNode] = field(default_factory=list)
    imports: list[dict] = field(default_factory=list)
    exports: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# Regex patterns for JavaScript/TypeScript
PATTERNS = {
    "function_declaration": re.compile(
        r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\([^)]*\)",
        re.MULTILINE,
    ),
    "function_expression": re.compile(
        r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>",
        re.MULTILINE,
    ),
    "arrow_function": re.compile(
        r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>",
        re.MULTILINE,
    ),
    "method_definition": re.compile(
        r"^\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{",
        re.MULTILINE,
    ),
    "class_declaration": re.compile(
        r"^\s*(?:export\s+)?class\s+(\w+)",
        re.MULTILINE,
    ),
    "import_statement": re.compile(
        r"^\s*import\s+(?:(?:\w+(?:\s*,\s*\w+)*)?\s+from\s+)?[\"']([^\"']+)[\"']",
        re.MULTILINE,
    ),
    "import_namespace": re.compile(
        r"^\s*import\s+\*\s+as\s+(\w+)\s+from\s+[\"']([^\"']+)[\"']",
        re.MULTILINE,
    ),
    "import_default": re.compile(
        r"^\s*import\s+(\w+)\s+from\s+[\"']([^\"']+)[\"']",
        re.MULTILINE,
    ),
    "export_statement": re.compile(
        r"^\s*export\s+(?:default\s+)?(?:class|function|const|let|var)\s+(\w+)",
        re.MULTILINE,
    ),
    "export_named": re.compile(
        r"^\s*export\s+\{([^}]+)\}",
        re.MULTILINE,
    ),
    "call_expression": re.compile(
        r"(\w+(?:\.\w+)*)\s*\(",
        re.MULTILINE,
    ),
    "require_call": re.compile(
        r"(?:const|let|var)\s+(?:\w+(?:\s*,\s*\w+)*)\s*=\s*require\s*\(\s*[\"']([^\"']+)[\"']\s*\)",
        re.MULTILINE,
    ),
}


def get_line_col(content: str, index: int) -> tuple[int, int]:
    """Get line and column from string index."""
    lines = content[:index].split("\n")
    return len(lines), len(lines[-1]) + 1


def parse_javascript_file(file_path: str) -> ParseResult:
    """Parse a single JavaScript/TypeScript file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return ParseResult(
            file_path=file_path,
            module_name=Path(file_path).stem,
            errors=[f"Failed to read file: {e}"],
        )

    result = ParseResult(file_path=file_path, module_name=Path(file_path).stem)

    # Find functions
    for match in PATTERNS["function_declaration"].finditer(content):
        name = match.group(1)
        line, col = get_line_col(content, match.start())
        result.nodes.append(
            JSNode(
                type="function",
                name=name,
                qualified_name=f"{result.module_name}.{name}",
                start_line=line,
                start_column=col,
                properties={"kind": "declaration", "async": "async" in match.group(0)},
            )
        )

    # Find arrow functions / function expressions
    for match in PATTERNS["function_expression"].finditer(content):
        name = match.group(1)
        line, col = get_line_col(content, match.start())
        result.nodes.append(
            JSNode(
                type="function",
                name=name,
                qualified_name=f"{result.module_name}.{name}",
                start_line=line,
                start_column=col,
                properties={"kind": "expression", "async": "async" in match.group(0)},
            )
        )

    # Find classes
    for match in PATTERNS["class_declaration"].finditer(content):
        name = match.group(1)
        line, col = get_line_col(content, match.start())
        result.nodes.append(
            JSNode(
                type="class",
                name=name,
                qualified_name=f"{result.module_name}.{name}",
                start_line=line,
                start_column=col,
                properties={"kind": "declaration"},
            )
        )

    # Find imports
    for match in PATTERNS["import_statement"].finditer(content):
        module = match.group(1)
        line, col = get_line_col(content, match.start())
        result.imports.append(
            {
                "module": module,
                "line": line,
                "column": col,
                "kind": "named",
            }
        )

    for match in PATTERNS["import_default"].finditer(content):
        name = match.group(1)
        module = match.group(2)
        line, col = get_line_col(content, match.start())
        result.imports.append(
            {
                "name": name,
                "module": module,
                "line": line,
                "column": col,
                "kind": "default",
            }
        )

    for match in PATTERNS["import_namespace"].finditer(content):
        name = match.group(1)
        module = match.group(2)
        line, col = get_line_col(content, match.start())
        result.imports.append(
            {
                "name": name,
                "module": module,
                "line": line,
                "column": col,
                "kind": "namespace",
            }
        )

    # Find exports
    for match in PATTERNS["export_statement"].finditer(content):
        name = match.group(1)
        line, col = get_line_col(content, match.start())
        result.exports.append(
            {
                "name": name,
                "line": line,
                "column": col,
                "kind": "declaration",
            }
        )

    for match in PATTERNS["export_named"].finditer(content):
        names = [n.strip() for n in match.group(1).split(",")]
        line, col = get_line_col(content, match.start())
        for name in names:
            result.exports.append(
                {
                    "name": name,
                    "line": line,
                    "column": col,
                    "kind": "named",
                }
            )

    # Find require calls (CommonJS)
    for match in PATTERNS["require_call"].finditer(content):
        module = match.group(1)
        line, col = get_line_col(content, match.start())
        result.imports.append(
            {
                "module": module,
                "line": line,
                "column": col,
                "kind": "require",
            }
        )

    return result


def parse_directory(
    root_path: str,
    include_node_modules: bool = False,
    max_files: int = 1000,
) -> list[ParseResult]:
    """Parse all JavaScript/TypeScript files in a directory."""
    results = []
    js_extensions = {".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"}
    file_count = 0

    for root, dirs, files in os.walk(root_path):
        # Skip node_modules unless explicitly included
        if not include_node_modules:
            dirs[:] = [d for d in dirs if d != "node_modules"]
            # Also skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]

        for file in sorted(files):
            if file_count >= max_files:
                break

            ext = Path(file).suffix
            if ext in js_extensions:
                file_path = os.path.join(root, file)
                result = parse_javascript_file(file_path)
                results.append(result)
                file_count += 1

    return results