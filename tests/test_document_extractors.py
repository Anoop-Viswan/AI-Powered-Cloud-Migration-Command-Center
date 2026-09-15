"""Unit tests for document_extractors: extract_content for all supported file types."""

import pytest

from backend.document_extractors import extract_content, PROSE_EXTENSIONS, EXTRACTOR_EXTENSIONS


def _write_text_pdf(path, pages: list[str]) -> None:
    """Write a real PDF with one Helvetica text line per page (built with pypdf itself)."""
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    font = writer._add_object(DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    }))
    for text in pages:
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
        })
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(str(path))


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

    # The tests below exercise pypdf's real text extraction, so a pypdf upgrade
    # (security bumps are frequent) that changes parsing behaviour fails here.

    def test_text_pdf_extracts_text(self, tmp_path):
        path = tmp_path / "text.pdf"
        _write_text_pdf(path, ["OrderService migrates Oracle to Azure SQL"])
        result = extract_content(str(path), ".pdf")
        assert result is not None
        chunks, content_type = result
        assert content_type == "prose"
        assert len(chunks) == 1
        assert "OrderService migrates Oracle to Azure SQL" in chunks[0]

    def test_multi_page_small_pdf_is_merged_in_page_order(self, tmp_path):
        path = tmp_path / "pages.pdf"
        _write_text_pdf(path, ["First page alpha", "Second page beta", "Third page gamma"])
        chunks, _ = extract_content(str(path), ".pdf")
        assert len(chunks) == 1
        text = chunks[0]
        assert text.index("alpha") < text.index("beta") < text.index("gamma")

    def test_large_pdf_is_chunked(self, tmp_path):
        from backend.document_extractors import MAX_CONTENT_CHARS

        path = tmp_path / "large.pdf"
        page_text = "migration " * 400  # ~4000 chars per page
        _write_text_pdf(path, [page_text] * 4)
        chunks, _ = extract_content(str(path), ".pdf")
        assert len(chunks) > 1
        assert all(len(c) <= MAX_CONTENT_CHARS for c in chunks)

    @pytest.mark.parametrize("payload", [
        b"not a pdf at all",
        b"%PDF-1.7\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",  # truncated, no xref/trailer
        b"",
    ])
    def test_corrupt_pdf_returns_none_without_raising(self, tmp_path, payload):
        path = tmp_path / "corrupt.pdf"
        path.write_bytes(payload)
        assert extract_content(str(path), ".pdf") is None


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
