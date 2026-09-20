"""
Unit tests for configuration and S3 key layout.
"""

import pytest

from src.config import Config


class TestS3Folder:
    """Tests for the raw/processed object key prefix."""

    def test_includes_prefix_and_folder(self, monkeypatch):
        """The folder prefix joins S3_PREFIX with raw/processed."""
        monkeypatch.setattr(Config, "S3_PREFIX", "market-data")

        assert Config.s3_folder(processed=False) == "market-data/raw"
        assert Config.s3_folder(processed=True) == "market-data/processed"

    def test_omits_empty_prefix(self, monkeypatch):
        """An unset S3_PREFIX must not produce a leading slash."""
        monkeypatch.setattr(Config, "S3_PREFIX", "")

        assert Config.s3_folder(processed=True) == "processed"

    def test_strips_surrounding_slashes(self, monkeypatch):
        """A prefix written with slashes must not double them up."""
        monkeypatch.setattr(Config, "S3_PREFIX", "/market-data/")

        assert Config.s3_folder() == "market-data/raw"

    def test_is_not_a_csv_key(self, monkeypatch):
        """Regression: listing with a ".csv" prefix matches no object at all."""
        monkeypatch.setattr(Config, "S3_PREFIX", "market-data")

        assert not Config.s3_folder(processed=True).endswith(".csv")


class TestS3Key:
    """Tests for per-symbol object keys."""

    def test_mirrors_the_local_layout(self, monkeypatch):
        """Keys must match the local raw/processed directory layout."""
        monkeypatch.setattr(Config, "S3_PREFIX", "market-data")

        assert Config.s3_key("AAPL") == "market-data/raw/AAPL.csv"
        assert Config.s3_key("AAPL", processed=True) == "market-data/processed/AAPL.csv"

    def test_preserves_symbol_punctuation(self, monkeypatch):
        """Index and Brazilian ticker symbols are used verbatim."""
        monkeypatch.setattr(Config, "S3_PREFIX", "market-data")

        assert Config.s3_key("^BVSP") == "market-data/raw/^BVSP.csv"
        assert Config.s3_key("PETR4.SA") == "market-data/raw/PETR4.SA.csv"

    def test_is_inside_its_folder(self, monkeypatch):
        """A symbol's key must live under the prefix used to list it."""
        monkeypatch.setattr(Config, "S3_PREFIX", "market-data")

        assert Config.s3_key("AAPL", processed=True).startswith(
            f"{Config.s3_folder(processed=True)}/"
        )


class TestValidate:
    """Tests for backend validation."""

    def test_accepts_local(self, monkeypatch):
        """The local backend needs no bucket."""
        monkeypatch.setattr(Config, "DATA_BACKEND", "local")
        monkeypatch.setattr(Config, "S3_BUCKET", "")

        Config.validate()

    def test_rejects_unknown_backend(self, monkeypatch):
        """Only local and s3 are supported."""
        monkeypatch.setattr(Config, "DATA_BACKEND", "gcs")

        with pytest.raises(ValueError, match="DATA_BACKEND"):
            Config.validate()

    def test_requires_bucket_for_s3(self, monkeypatch):
        """The s3 backend is unusable without a bucket."""
        monkeypatch.setattr(Config, "DATA_BACKEND", "s3")
        monkeypatch.setattr(Config, "S3_BUCKET", "")

        with pytest.raises(ValueError, match="S3_BUCKET"):
            Config.validate()
