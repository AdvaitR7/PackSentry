"""
Architectural Invariant Linter (ADR-0002 & ADR-0012).
Uses Python AST inspection to strictly assert that:
1. No module in Backend/app/rules/ references or accesses 'normalized_text'.
   Rules adjudicate strictly on raw_text and parsed structures derived from it (ADR-0002).
2. No module in Backend/app/rules/ imports or references geometry/polygon coordinates
   or transforms. Rules must not depend on pixel geometry (ADR-0012).
"""

import ast
from pathlib import Path
import pytest

RULES_DIR = Path(__file__).resolve().parent.parent / "app" / "rules"

FORBIDDEN_ATTRIBUTES = {
    "normalized_text": "ADR-0002: Rules must adjudicate on raw_text, never on normalized_text",
    "polygon_analysis": "ADR-0012: Rules must not touch image geometry",
    "polygon_original": "ADR-0012: Rules must not touch image geometry",
    "polygon_normalized": "ADR-0012: Rules must not touch image geometry",
    "transform": "ADR-0012: Rules must not touch image transform coordinates",
}

FORBIDDEN_IMPORTS = {
    "normalized_text",
    "polygon_analysis",
    "polygon_original",
    "polygon_normalized",
    "Transform",
    "NormalisedDocument",
    "NormalisedLine",
}


def test_rules_directory_exists():
    assert RULES_DIR.exists() and RULES_DIR.is_dir(), f"Rules directory missing: {RULES_DIR}"


def test_ast_invariant_no_forbidden_access_in_rules():
    py_files = list(RULES_DIR.glob("*.py"))
    assert len(py_files) >= 5, f"Expected multiple rule files in {RULES_DIR}"

    violations = []
    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))

        for node in ast.walk(tree):
            # Check attribute access: obj.normalized_text, obj.polygon_analysis, etc.
            if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_ATTRIBUTES:
                violations.append(
                    f"{py_file.name}:{node.lineno}: Accessed forbidden attribute '.{node.attr}'. "
                    f"Violation: {FORBIDDEN_ATTRIBUTES[node.attr]}"
                )

            # Check imports: from ... import normalized_text, Transform, etc.
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in FORBIDDEN_IMPORTS:
                        violations.append(
                            f"{py_file.name}:{node.lineno}: Imported forbidden symbol '{alias.name}'"
                        )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in FORBIDDEN_IMPORTS:
                        violations.append(
                            f"{py_file.name}:{node.lineno}: Imported forbidden module '{alias.name}'"
                        )

            # Check variable names
            elif isinstance(node, ast.Name) and node.id in FORBIDDEN_IMPORTS:
                violations.append(
                    f"{py_file.name}:{node.lineno}: Referenced forbidden identifier '{node.id}'"
                )

    assert not violations, "\n".join(violations)
