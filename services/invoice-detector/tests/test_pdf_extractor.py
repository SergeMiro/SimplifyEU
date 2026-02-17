"""
Tests for PDF extraction and file validation.
"""
import os
import pytest
import tempfile
from src.core.pdf_extractor import validate_file_magic, compute_file_hash


class TestValidateFileMagic:
    """Test magic byte validation."""

    def test_valid_pdf(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake content")
            f.flush()
            assert validate_file_magic(f.name) is True
            os.unlink(f.name)

    def test_valid_jpeg(self):
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"\xff\xd8\xff\xe0 fake jpeg")
            f.flush()
            assert validate_file_magic(f.name) is True
            os.unlink(f.name)

    def test_valid_png(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n fake png")
            f.flush()
            assert validate_file_magic(f.name) is True
            os.unlink(f.name)

    def test_invalid_file(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"Hello, this is not a PDF")
            f.flush()
            assert validate_file_magic(f.name) is False
            os.unlink(f.name)

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.flush()
            assert validate_file_magic(f.name) is False
            os.unlink(f.name)


class TestComputeFileHash:
    """Test file hashing."""

    def test_same_content_same_hash(self):
        with tempfile.NamedTemporaryFile(delete=False) as f1:
            f1.write(b"test content")
            f1.flush()
            hash1 = compute_file_hash(f1.name)

        with tempfile.NamedTemporaryFile(delete=False) as f2:
            f2.write(b"test content")
            f2.flush()
            hash2 = compute_file_hash(f2.name)

        assert hash1 == hash2
        os.unlink(f1.name)
        os.unlink(f2.name)

    def test_different_content_different_hash(self):
        with tempfile.NamedTemporaryFile(delete=False) as f1:
            f1.write(b"content A")
            f1.flush()
            hash1 = compute_file_hash(f1.name)

        with tempfile.NamedTemporaryFile(delete=False) as f2:
            f2.write(b"content B")
            f2.flush()
            hash2 = compute_file_hash(f2.name)

        assert hash1 != hash2
        os.unlink(f1.name)
        os.unlink(f2.name)

    def test_hash_is_sha256(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            f.flush()
            h = compute_file_hash(f.name)

        assert len(h) == 64  # SHA-256 hex length
        assert all(c in "0123456789abcdef" for c in h)
        os.unlink(f.name)
