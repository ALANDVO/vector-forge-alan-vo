import pytest
import tempfile
import os
from pathlib import Path

from app.analysis.javascript.parser import (
    parse_javascript_file,
    parse_directory,
    get_line_col,
)


def test_get_line_col():
    content = "line 1\nline 2\nline 3"
    assert get_line_col(content, 0) == (1, 1)
    assert get_line_col(content, 6) == (1, 7)
    assert get_line_col(content, 7) == (2, 1)
    assert get_line_col(content, 13) == (2, 7)
    assert get_line_col(content, 14) == (3, 1)


def test_parse_simple_function():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write("function hello() { return 'world'; }")
        f.flush()
        try:
            result = parse_javascript_file(f.name)
            assert len(result.errors) == 0
            assert len(result.nodes) == 1
            assert result.nodes[0].name == "hello"
            assert result.nodes[0].type == "function"
            assert result.nodes[0].qualified_name.endswith(".hello")
        finally:
            os.unlink(f.name)


def test_parse_async_function():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write("async function fetchData() { return await fetch('/api'); }")
        f.flush()
        try:
            result = parse_javascript_file(f.name)
            assert len(result.nodes) == 1
            assert result.nodes[0].name == "fetchData"
            assert result.nodes[0].properties.get("async") is True
        finally:
            os.unlink(f.name)


def test_parse_arrow_function():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write("const add = (a, b) => a + b;")
        f.flush()
        try:
            result = parse_javascript_file(f.name)
            assert len(result.nodes) == 1
            assert result.nodes[0].name == "add"
            assert result.nodes[0].type == "function"
        finally:
            os.unlink(f.name)


def test_parse_class():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write("class User { constructor(name) { this.name = name; } }")
        f.flush()
        try:
            result = parse_javascript_file(f.name)
            assert len(result.nodes) == 1
            assert result.nodes[0].name == "User"
            assert result.nodes[0].type == "class"
        finally:
            os.unlink(f.name)


def test_parse_imports():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write("""
import React from 'react';
import { useState, useEffect } from 'react';
import * as Utils from './utils';
const fs = require('fs');
""")
        f.flush()
        try:
            result = parse_javascript_file(f.name)
            assert len(result.imports) >= 3
            # Check default import
            default_imports = [i for i in result.imports if i["kind"] == "default"]
            assert len(default_imports) == 1
            assert default_imports[0]["name"] == "React"
            assert default_imports[0]["module"] == "react"

            # Check named imports
            named_imports = [i for i in result.imports if i["kind"] == "named"]
            assert len(named_imports) >= 1

            # Check namespace import
            ns_imports = [i for i in result.imports if i["kind"] == "namespace"]
            assert len(ns_imports) == 1
            assert ns_imports[0]["name"] == "Utils"

            # Check require
            req_imports = [i for i in result.imports if i["kind"] == "require"]
            assert len(req_imports) == 1
            assert req_imports[0]["module"] == "fs"
        finally:
            os.unlink(f.name)


def test_parse_exports():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write("""
export function foo() {}
export const bar = 1;
export { baz, qux };
""")
        f.flush()
        try:
            result = parse_javascript_file(f.name)
            assert len(result.exports) >= 3
            decl_exports = [e for e in result.exports if e["kind"] == "declaration"]
            named_exports = [e for e in result.exports if e["kind"] == "named"]
            assert len(decl_exports) >= 2
            assert len(named_exports) >= 1
        finally:
            os.unlink(f.name)


def test_parse_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        (Path(tmpdir) / "main.js").write_text("function main() {}")
        (Path(tmpdir) / "utils.js").write_text("export function helper() {}")
        (Path(tmpdir) / "ignored.txt").write_text("not js")

        # Create node_modules (should be skipped by default)
        os.makedirs(os.path.join(tmpdir, "node_modules", "pkg"))
        (Path(tmpdir) / "node_modules" / "pkg" / "index.js").write_text("export function lib() {}")

        results = parse_directory(tmpdir, include_node_modules=False, max_files=10)
        assert len(results) == 2
        file_names = {r.module_name for r in results}
        assert file_names == {"main", "utils"}

        # With node_modules
        results_with_nm = parse_directory(tmpdir, include_node_modules=True, max_files=10)
        assert len(results_with_nm) == 3


def test_parse_typescript():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ts", delete=False) as f:
        f.write("""
interface User { name: string; }
function greet(user: User): string { return `Hello, ${user.name}`; }
export { greet };
""")
        f.flush()
        try:
            result = parse_javascript_file(f.name)
            assert len(result.nodes) == 1
            assert result.nodes[0].name == "greet"
        finally:
            os.unlink(f.name)


def test_parse_error_handling():
    # Non-existent file
    result = parse_javascript_file("/nonexistent/file.js")
    assert len(result.errors) == 1
    assert "Failed to read file" in result.errors[0]