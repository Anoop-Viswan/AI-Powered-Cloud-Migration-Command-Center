# Recommendations: Mixed Document Types (PDF, DOC/DOCX, XLS/XLSX, CSV, PPTX)

## 1. Single KB vs Separate KBs

**Recommendation: Use a single knowledge base (one index, one namespace per project) and add the new file types.**

- **Pinecone best practice:** Use **one index with namespaces** and **metadata** to separate or filter content. Multiple indexes are for different embedding models, hybrid (dense + sparse) needs, or full isolation—not for “PDF vs Excel.”
- **Embeddings:** The same embedding model (e.g. `llama-text-embed-v2`) works on text from any source. What matters is that you feed **meaningful text** (prose, table rows with headers, slide text) into the pipeline. No need for separate indexes per file type.
- **Production:** Single index is simpler to operate, cheaper, and easier to query (one endpoint, optional filter by `category`). Your code already supports `--category pdf` or `--category xlsx` for filtering; that continues to work.

**Conclusion:** Add the new file types to the **existing** pipeline. Keep one project directory → one namespace. Use metadata (`category` = extension, and optionally `content_type` = prose | table | slide) for filtering and traceability.

---

## 2. File Types to Support and How to Handle Them

| Type    | Extension(s) | Extraction approach | Chunking strategy |
|---------|--------------|----------------------|--------------------|
| PDF     | `.pdf`       | **pypdf** – extract text per page. For scanned PDFs you’d need OCR (e.g. pytesseract) later; start with text-based PDFs. | Prose: by character (current) or by page. Page-level often better for PDFs with tables. |
| Word    | `.docx`      | **python-docx** – paragraphs and tables as text. | Prose + tables: current overlap chunking; for tables, prefer keeping table rows together (see Tables below). |
| Word    | `.doc`       | Legacy binary. Options: **textract** (OS-dependent), **LibreOffice headless** (convert to text), or **antiword**. Simpler: support `.docx` first and treat `.doc` as “convert to docx or txt manually” or add a single optional dependency. | Same as docx once text is extracted. |
| Excel   | `.xlsx`      | **openpyxl** – read sheet names, then per sheet: header row + data rows. | **Table-aware:** emit “Header: A, B, C → Row: 1, 2, 3” per row or small row groups; never split mid-row. |
| Excel   | `.xls`       | **xlrd** – read-only for legacy .xls. Same idea: sheet → header + rows. | Same as xlsx. |
| CSV     | `.csv`       | **csv** (stdlib) or **pandas** – header + rows. | Same as Excel: schema-aware rows (include column names in each chunk). |
| PowerPoint | `.pptx`    | **python-pptx** – slide title + body text per slide. | **Slide-aware:** one chunk per slide (or merge 2–3 short slides) so “slide 5” stays coherent. |

**Suggested Python dependencies (add to `requirements.txt`):**

- `pypdf` – PDF
- `python-docx` – DOCX
- `openpyxl` – XLSX
- `xlrd` – XLS (legacy)
- `python-pptx` – PPTX  
- CSV: no extra lib (stdlib `csv` or plain text read).

Optional for `.doc`: `textract` or “convert to docx/txt” path; can be Phase 2.

---

## 3. Chunking: Prose vs Tables vs Slides

- **Prose (PDF, DOC/DOCX, plain text):**  
  Current character-based chunking with overlap is fine. For PDFs, **page-based** chunking is often better (each chunk = one page or a few pages) so tables and sections stay intact.

- **Tables (XLS, XLSX, CSV):**  
  **Do not** use plain character chunking; it splits rows and loses column meaning. Best practice:
  - Include **column headers** in every chunk (e.g. “Project | Owner | Due Date → Alpha | Alice | 2025-03-01”).
  - Chunk by **rows** (e.g. N rows per chunk) or by row groups that fit within your max chunk size.
  - This keeps semantics so embeddings and queries like “project plan due dates” work.

- **Slides (PPTX):**  
  Chunk by **slide** (or 2–3 short slides). Each chunk = slide title + bullet/text. Avoid splitting in the middle of a slide.

**Implementation outline:**

- Add a small **content-type** notion: `prose` | `table` | `slide`.
- `chunk_text()` stays for prose (and for “flattened” doc/pptx text if you don’t want page/slide logic in v1).
- New helpers: `chunk_table_rows(rows, header, max_chars)` and `chunk_pptx_by_slide(slides)`.
- Metadata: keep `category` (file extension); optionally add `content_type` for future “only search slides” or “only spreadsheets.”

---

## 4. Metadata and Filtering

- **Keep:** `file_path`, `category` (extension: `pdf`, `docx`, `xlsx`, `csv`, `pptx`, etc.).
- **Optional:** `content_type`: `"prose"` | `"table"` | `"slide"` so the UI or API can filter by “presentations only” or “spreadsheets only” without separate KBs.
- **Structured IDs:** Keep current pattern (e.g. `file_path__chunk_index`); it’s already good for traceability.

No schema change required in Pinecone beyond adding the new extensions and optional metadata; the index already has a `content` field and supports metadata filters.

---

## 5. Production-Oriented Notes

- **Single index, one namespace per project directory:** Matches Pinecone’s guidance: use namespaces and metadata instead of multiple indexes.
- **Batch upserts:** Already in place; keep batch size (e.g. 96) when adding new record types.
- **Errors:** Per-file extraction can fail (corrupted PDF, password-protected file). Handle per file: log and skip, don’t fail the whole run.
- **Idempotence:** Re-running `--seed` on the same directory can re-upsert same IDs; Pinecone overwrites. For “add new files only” you’d add incremental logic later; for now, full re-seed is acceptable.
- **Scanned PDFs:** If you need OCR later, add a path that uses something like `pytesseract` + `pdf2image` for PDFs that return no/minimal text from pypdf.

---

## 6. Summary Table

| Question | Recommendation |
|----------|----------------|
| Separate KB per file type? | **No.** One KB (one index, one namespace per project) with metadata. |
| Add PDF, DOCX, XLS, XLSX, CSV, PPTX? | **Yes.** Add extractors and include these extensions in the pipeline. |
| .doc (legacy)? | Support in Phase 2 or via conversion; prioritize .docx. |
| Chunking | Prose: current or page-based. Tables: row-based with headers. Slides: per-slide. |
| Metadata | Keep `category` (extension); optionally add `content_type` (prose/table/slide). |
| Dependencies | pypdf, python-docx, openpyxl, xlrd, python-pptx; CSV via stdlib. |

---

## Next Steps (when you’re ready)

1. Add the new extensions to `INCLUDE_EXTENSIONS` and implement extractors (PDF, DOCX, XLS/XLSX, CSV, PPTX) that return plain text (or structured rows for tables / slides).
2. Route each file type to the right chunking (prose vs table vs slide).
3. Add optional `content_type` to records and wire it to metadata.
4. Harden: per-file try/except, skip bad files, log warnings.
5. (Optional) Add a `--category` filter in the UI so users can restrict to e.g. “pptx” or “xlsx” when needed.

Once you’re happy with this direction, we can implement the extractors and chunking in `semantic_search.py` step by step.
