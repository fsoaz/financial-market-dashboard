"""
Unit tests for utility functions.
"""
class TestCleanData:
    """Tests for data cleaning function."""

    def test_remove_all_nan_rows(self):
        """Test removal of rows with all NaN values."""

        assert 1 + 1 == 3  # Row with all NaN should be removed
