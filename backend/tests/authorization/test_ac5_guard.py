"""
Test for AC-5 guard: pytest_collection_modifyitems hook.

Verifies that the "boş matris = FAIL" guard in conftest.py
actually calls pytest.exit when items collection is empty.
"""

import pytest
from _pytest.outcomes import Exit

from tests.authorization.conftest import pytest_collection_modifyitems


class TestAC5Guard:
    """AC-5: Verify the empty matrix guard prevents silent test collection failures."""

    def test_pytest_collection_modifyitems_empty_items_raises_exit(self):
        """
        AC-5: pytest_collection_modifyitems calls pytest.exit when items is empty.

        Ensures that forgetting to add test cases to this package
        will fail CI, not silently pass.
        """
        # Call the hook with empty items collection
        with pytest.raises(Exit):
            pytest_collection_modifyitems(config=None, items=[])

    def test_pytest_collection_modifyitems_nonempty_items_does_not_raise(self):
        """
        AC-5: pytest_collection_modifyitems does NOT raise when items is non-empty.

        Ensures that the guard only triggers when collection is truly empty.
        """
        # Create a mock test item (a simple object with minimal attributes)
        mock_item = type('MockItem', (), {})()

        # Should not raise; should pass through silently
        try:
            pytest_collection_modifyitems(config=None, items=[mock_item])
        except Exit:
            pytest.fail("pytest_collection_modifyitems should not raise when items is non-empty")
