"""Unit tests for document_extractors: extract_content for all supported file types."""

import pytest

from backend.document_extractors import extract_content, PROSE_EXTENSIONS, EXTRACTOR_EXTENSIONS


class TestExtractPlainText:
    """Plain text extensions: .txt, .md, etc."""

    def test_txt_returns_prose_chunks(self, sample_txt_path):
        result = extract_content(str(sample_txt_path), ".txt")
        assert result is not None
        chunks, content_type = result
        assert content_type == "prose"
        assert len(chunks) >= 1
        assert "Plain text content" in chunks[0]
        assert "Second line" in chunks[0]

    def test_md_returns_prose(self, tmp_path):
        path = tmp_path / "readme.md"
        path.write_text("# Title\n\nSome **markdown** content.", encoding="utf-8")
        result = extract_content(str(path), ".md")
        assert result is not None
        chunks, content_type = result
        assert content_type == "prose"
        assert any("markdown" in c for c in chunks)

    def test_extension_without_dot(self, sample_txt_path):
        result = extract_content(str(sample_txt_path), "txt")
        assert result is not None
        _, content_type = result
        assert content_type == "prose"


class TestExtractCSV:
    """CSV: table chunking with header."""

    def test_csv_returns_table_chunks(self, sample_csv_path):
        result = extract_content(str(sample_csv_path), ".csv")
        assert result is not None
        chunks, content_type = result
        assert content_type == "table"
        assert len(chunks) >= 1
        assert "Project" in chunks[0] and "Owner" in chunks[0]
        assert "Alpha" in chunks[0] and "Alice" in chunks[0]


class TestExtractPDF:
    """PDF: blank PDF returns None; valid PDF runs without error."""

    def test_blank_pdf_returns_none_or_empty(self, sample_pdf_path):
        result = extract_content(str(sample_pdf_path), ".pdf")
        # Blank page has no extractable text -> None
        assert result is None or (result[0] == [] and result[1] == "prose")


class TestExtractDOCX:
    """DOCX: minimal document with paragraph."""

    def test_docx_returns_prose_chunks(self, sample_docx_path):
        result = extract_content(str(sample_docx_path), ".docx")
        assert result is not None
        chunks, content_type = result
        assert content_type == "prose"
        assert len(chunks) >= 1
        assert "DOCX unit test" in chunks[0]


class TestExtractXLSX:
    """XLSX: table with header and rows."""

    def test_xlsx_returns_table_chunks(self, sample_xlsx_path):
        result = extract_content(str(sample_xlsx_path), ".xlsx")
        assert result is not None
        chunks, content_type = result
        assert content_type == "table"
        assert len(chunks) >= 1
        assert "Name" in chunks[0] and "Value" in chunks[0]
        assert "Alpha" in chunks[0] and "42" in chunks[0]


class TestExtractPPTX:
    """PPTX: slide with text."""

    def test_pptx_returns_slide_chunks(self, sample_pptx_path):
        result = extract_content(str(sample_pptx_path), ".pptx")
        assert result is not None
        chunks, content_type = result
        assert content_type == "slide"
        assert len(chunks) >= 1
        assert "PPTX unit test" in chunks[0]


class TestExtractEdgeCases:
    """Unsupported extension, missing file, empty file."""

    def test_unsupported_extension_returns_none(self, sample_txt_path):
        result = extract_content(str(sample_txt_path), ".xyz")
        assert result is None

    def test_missing_file_returns_none(self, tmp_path):
        result = extract_content(str(tmp_path / "nonexistent.txt"), ".txt")
        assert result is None

    def test_empty_txt_returns_none(self, tmp_path):
        path = tmp_path / "empty.txt"
        path.write_text("", encoding="utf-8")
        result = extract_content(str(path), ".txt")
        assert result is None

    def test_whitespace_only_returns_none(self, tmp_path):
        path = tmp_path / "blank.txt"
        path.write_text("   \n\n  ", encoding="utf-8")
        result = extract_content(str(path), ".txt")
        assert result is None


class TestConstants:
    """Sanity check on extension sets."""

    def test_prose_and_extractor_sets_include_document_types(self):
        assert ".pdf" in EXTRACTOR_EXTENSIONS or ".pdf" in PROSE_EXTENSIONS
        assert ".txt" in PROSE_EXTENSIONS
        assert ".csv" in EXTRACTOR_EXTENSIONS
        assert ".docx" in EXTRACTOR_EXTENSIONS
        assert ".xlsx" in EXTRACTOR_EXTENSIONS
        assert ".pptx" in EXTRACTOR_EXTENSIONS
