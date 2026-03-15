# Pydantic Models in This Project

**What is Pydantic?**  
Pydantic is a Python library for **data validation and settings** using type hints. You define classes (models) with typed fields; Pydantic validates that data matches those types and constraints (e.g. non-empty string, number in 0–1). It is widely used with **FastAPI** for request/response bodies and for structured data in application code.

**Why we use it here:**  
We use Pydantic so that API request/response shapes and internal data structures are consistent and validated. Invalid or missing required fields are caught early instead of causing errors in the database or LLM calls. Types and constraints are defined in one place, which helps maintenance and tooling (e.g. IDE hints).

---

## Where We Use Pydantic

- **FastAPI** – Request and response bodies are validated and serialized via Pydantic models (e.g. `ApplicationProfile` for PUT profile, research result for POST research).
- **Assessment and research** – Profile, validation results, and research results (KB hits, confidence, official docs) are all Pydantic models.
- **Persistence** – We serialize models to JSON (e.g. `model.model_dump()` or `model_dump_json()`) for the SQLite store and rehydrate with `Model.model_validate(json)`.

---

## Main Models in This Project

| Model | File | Purpose |
|-------|------|--------|
| **ApplicationProfile** | `backend/services/assessment/models.py` | Full application profile (seven pillars). Used in PUT profile, validation, research, and summarizer. |
| **AssessmentState** | Same file | Assessment record: id, profile, approach_document, report, status, error_message. Used when loading/saving assessment state. |
| **KBHit** | `backend/services/assessment/research_models.py` | One KB search hit: score, file_path, application, content_preview, why_match. Used in research API response. |
| **KBConfidence** | Same file | KB confidence: value (0–1), label (high/medium/low), below_threshold. |
| **OfficialDocResult** | Same file | One official-doc result: title, url, snippet, rationale. |
| **ResearchResult** | Same file | Full research output: approach_document, kb_confidence, kb_hits, official_docs. Returned by the research agent and research API. |
| **ReportUpdate** | `backend/routers/assessment.py` | Body for editing report: `{ "report": "..." }`. |

---

## Common Patterns

- **Required field:** `Field(..., min_length=1)` (e.g. `application_name`).
- **Optional with default:** `Field(default="")` or `default_factory=list`.
- **Allowed values:** `Literal["high", "medium", "low"]` for a fixed set of strings.
- **Validation:** `ge=0, le=1` for numeric bounds; `min_length=1` for strings.
- **Serialization:** `.model_dump()` for a dict, `.model_dump_json()` for a JSON string; `Model.model_validate(dict)` to build a model from a dict or parsed JSON.

---

## References

- [Pydantic docs](https://docs.pydantic.dev/)
- [FastAPI – Request body](https://fastapi.tiangolo.com/tutorial/body/)
