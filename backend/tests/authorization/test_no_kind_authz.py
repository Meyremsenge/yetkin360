"""
Static protection test: principal.kind is never read in authorization decisions (AC-6).

Scans backend/app/services/ and backend/app/api/ for direct reads of principal.kind,
engagement.kind, evidence.kind in authorization decision paths. Kind is display-only;
authorization must use ID lists (org_ids, org_admin_ids, etc.).

Implements AC-6 (threat model, intent E — escalation prevention).
"""

import ast
import os
from pathlib import Path


def _find_principal_kind_reads(source: str, filename: str) -> list[int]:
    """
    Scan source code for reads of principal.kind in authorization context.

    Returns: list of line numbers where principal.kind (or similar) is read.
    Does NOT flag:
      - Principal(kind="X") constructor calls (keyword argument definition)
      - engagement.kind, evidence.kind, request_body.kind reads (different objects)
      - Non-authorization uses (e.g., logging "kind for display")

    Args:
        source: Python source code as string
        filename: filename for context

    Returns:
        List of line numbers (1-indexed) where principal.kind is read
    """
    tree = ast.parse(source, filename=filename)

    violations = []

    class KindReadVisitor(ast.NodeVisitor):
        def visit_Attribute(self, node):
            """Check for obj.kind reads, including nested principal access via getattr()."""
            # Pattern 1: direct attribute access: principal.kind, p.kind, current_principal.kind, caller.kind
            if (isinstance(node.value, ast.Name) and
                node.attr == "kind" and
                node.value.id in {"principal", "p", "current_principal", "caller"}):
                violations.append(node.lineno)
            self.generic_visit(node)

        def visit_Call(self, node):
            """Check for getattr(principal, 'kind') patterns."""
            # Pattern 2: getattr(principal, "kind") or getattr(principal, 'kind')
            if (isinstance(node.func, ast.Name) and
                node.func.id == "getattr" and
                len(node.args) >= 2):
                # First arg is the object, second is the attribute name
                obj_arg = node.args[0]
                attr_arg = node.args[1]

                # Check if object is a principal-like variable
                if isinstance(obj_arg, ast.Name) and obj_arg.id in {"principal", "p", "current_principal", "caller"}:
                    # Check if attribute name is "kind" (as string constant)
                    if isinstance(attr_arg, ast.Constant) and attr_arg.value == "kind":
                        violations.append(node.lineno)

            self.generic_visit(node)

    visitor = KindReadVisitor()
    visitor.visit(tree)
    return violations


def _scan_directory_for_kind_reads(root_dir: str, exclude_patterns=None) -> dict[str, list[int]]:
    """
    Scan all .py files in root_dir for principal.kind reads.

    Args:
        root_dir: directory to scan (e.g., backend/app/services)
        exclude_patterns: list of patterns to skip (e.g., ["__pycache__", "*.pyc"])

    Returns:
        dict mapping filepath -> list of violation line numbers

    Raises:
        FileNotFoundError: if root_dir doesn't exist
        SyntaxError: if a Python file has parse errors (not silently skipped)
        RuntimeError: if a file cannot be read
    """
    if exclude_patterns is None:
        exclude_patterns = ["__pycache__", "*.pyc", ".pytest_cache"]

    violations = {}
    root = Path(root_dir)

    if not root.exists():
        raise FileNotFoundError(f"Directory not found: {root_dir}")

    for py_file in root.rglob("*.py"):
        # Skip excluded patterns
        if any(pattern in str(py_file) for pattern in exclude_patterns):
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                source = f.read()
            lines = _find_principal_kind_reads(source, str(py_file))
            if lines:
                violations[str(py_file)] = lines
        except (IOError, OSError) as e:
            # File read errors should fail the test, not be silently skipped
            raise RuntimeError(f"Failed to read file {py_file}: {e}") from e
        # SyntaxError from _find_principal_kind_reads propagates (not caught)

    return violations


# ============================================================================
# AC-6: Real code scanning (services + api)
# ============================================================================


class TestNoKindAuthzRealCode:
    """AC-6: backend/app/services/ and backend/app/api/ do not read principal.kind."""

    def test_services_no_principal_kind_read(self):
        """AC-6: app/services/*.py does not read principal.kind."""
        backend_root = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "app", "services"
        )
        violations = _scan_directory_for_kind_reads(backend_root)

        # Extract violations specific to principal.kind (not engagement.kind, etc.)
        # This test uses the visitor's output directly
        assert violations == {}, (
            "AC-6 violation: principal.kind read in authorization context:\n"
            + "\n".join(f"  {file}:{lines}" for file, lines in violations.items())
        )

    def test_api_no_principal_kind_read(self):
        """AC-6: app/api/*.py does not read principal.kind."""
        backend_root = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "app", "api"
        )
        violations = _scan_directory_for_kind_reads(backend_root)

        # Note: deps.py calculates kind, so it's OK there
        # Violations would be in other api files (organizations.py, etc.)
        assert violations == {}, (
            "AC-6 violation: principal.kind read in authorization context:\n"
            + "\n".join(f"  {file}:{lines}" for file, lines in violations.items())
        )


# ============================================================================
# AC-6: Synthetic code snippets (unit tests)
# ============================================================================


class TestNoKindAuthzSynthetic:
    """AC-6: static scanning of synthetic code snippets."""

    def test_detects_principal_kind_read(self):
        """AC-6: detects principal.kind == "X" in synthetic snippet."""
        source = """
def some_authorization_check(principal):
    if principal.kind == "ORG_ADMIN":
        return True
    return False
"""
        violations = _find_principal_kind_reads(source, "test.py")
        assert len(violations) > 0, "Should detect principal.kind read"
        assert 3 in violations

    def test_detects_p_kind_abbreviation(self):
        """AC-6: detects abbreviated p.kind."""
        source = """
def check_perms(p):
    return p.kind in ["ORG_ADMIN", "INST_ADMIN"]
"""
        violations = _find_principal_kind_reads(source, "test.py")
        assert len(violations) > 0, "Should detect p.kind read"

    def test_detects_current_principal_kind(self):
        """AC-6: detects current_principal.kind."""
        source = """
def check_role(current_principal):
    if current_principal.kind != "TALENT":
        raise PermissionError()
"""
        violations = _find_principal_kind_reads(source, "test.py")
        assert len(violations) > 0, "Should detect current_principal.kind"

    def test_ignores_engagement_kind(self):
        """AC-6: does NOT flag engagement.kind (different object)."""
        source = """
def check_engagement(engagement):
    if engagement.kind == "INTERNSHIP":
        return True
    return False
"""
        violations = _find_principal_kind_reads(source, "test.py")
        assert len(violations) == 0, "Should NOT flag engagement.kind"

    def test_ignores_evidence_kind(self):
        """AC-6: does NOT flag evidence.kind (different object)."""
        source = """
def check_evidence(evidence):
    if evidence.kind == "DOCUMENT":
        return True
    return False
"""
        violations = _find_principal_kind_reads(source, "test.py")
        assert len(violations) == 0, "Should NOT flag evidence.kind"

    def test_ignores_principal_constructor_kwarg(self):
        """AC-6: does NOT flag Principal(kind="X") constructor call."""
        source = """
def create_principal():
    return Principal(kind="TALENT", org_ids=[], talent_id=None)
"""
        violations = _find_principal_kind_reads(source, "test.py")
        # Constructor keyword arguments are not attribute reads (they're Keyword AST nodes)
        assert violations == [], "Should NOT flag Principal(kind=...) constructor calls"

    def test_ignores_request_body_kind(self):
        """AC-6: does NOT flag request_body.kind (different object)."""
        source = """
def handle_request(request_body):
    if request_body.kind == "UPDATE":
        return True
    return False
"""
        violations = _find_principal_kind_reads(source, "test.py")
        assert len(violations) == 0, "Should NOT flag request_body.kind"

    def test_detects_nested_function(self):
        """AC-6: detects principal.kind in nested function scope."""
        source = """
def outer(principal):
    def inner():
        if principal.kind == "ORG_ADMIN":
            return True
        return False
    return inner()
"""
        violations = _find_principal_kind_reads(source, "test.py")
        assert len(violations) > 0, "Should detect in nested function"

    def test_detects_multiple_violations(self):
        """AC-6: detects multiple principal.kind reads in same file."""
        source = """
def check_one(principal):
    if principal.kind == "ADMIN":
        return True

def check_two(principal):
    if principal.kind != "MEMBER":
        return False
"""
        violations = _find_principal_kind_reads(source, "test.py")
        assert len(violations) >= 2, "Should detect both reads"

    def test_caller_principal_variant(self):
        """AC-6: detects caller.kind (parameter named 'caller')."""
        source = """
def authorize(caller):
    return caller.kind == "COORDINATOR"
"""
        violations = _find_principal_kind_reads(source, "test.py")
        assert len(violations) > 0, "Should detect caller.kind"

    def test_parse_error_raises(self):
        """AC-6: parse error in source code raises SyntaxError (not silently ignored)."""
        import pytest
        source = """
def broken(principal):
    if principal.kind == "X:  # unterminated string
"""
        with pytest.raises(SyntaxError):
            _find_principal_kind_reads(source, "test.py")

    def test_detects_getattr_principal_kind(self):
        """AC-6: detects getattr(principal, 'kind') calls."""
        source = """
def check_via_getattr(principal):
    kind = getattr(principal, "kind")
    return kind == "ADMIN"
"""
        violations = _find_principal_kind_reads(source, "test.py")
        assert len(violations) > 0, "Should detect getattr(principal, 'kind')"

    def test_detects_getattr_with_single_quotes(self):
        """AC-6: detects getattr(principal, 'kind') with single quotes."""
        source = """
def check_via_getattr(principal):
    kind = getattr(principal, 'kind')
    return kind == "ADMIN"
"""
        violations = _find_principal_kind_reads(source, "test.py")
        assert len(violations) > 0, "Should detect getattr(principal, 'kind') with single quotes"

    def test_ignores_getattr_other_attributes(self):
        """AC-6: does NOT flag getattr(principal, 'other_attr')."""
        source = """
def check_via_getattr(principal):
    org_ids = getattr(principal, "org_ids")
    return len(org_ids) > 0
"""
        violations = _find_principal_kind_reads(source, "test.py")
        assert len(violations) == 0, "Should NOT flag getattr for non-kind attributes"
