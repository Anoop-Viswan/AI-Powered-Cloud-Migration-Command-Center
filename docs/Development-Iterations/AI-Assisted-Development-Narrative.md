# AI-Assisted Development Narrative: Cloud Migration Command Center

**Purpose:** This document keeps a narrative of how we iteratively developed this application with AI assistance. It records the **updates, changes, and iterations** you suggested, the **type of guidance and instructions** you gave, and how that shaped the product. The goal is to help others understand **how to use AI effectively** for building real applications: what to ask for, how to refine, and how to steer toward a strong outcome.

---

## 1. Why This Narrative Matters

Building with AI is iterative. You don’t get a perfect system in one prompt. You get something good by:

- **Being specific** about what “good” means (e.g. “100% transparency on what the LLM is doing”).
- **Asking for design first** when the approach is unclear (e.g. “show me the blueprint before you implement”).
- **Rejecting generic output** and asking for professional standards (e.g. “refer Microsoft reference architectures”).
- **Fixing behavior, not just bugs** (e.g. “clean up everything when I run research again”).
- **Demanding explainability** (e.g. “I need to see why it met or didn’t meet each criterion”).

This narrative captures those patterns so your team (and others) can reuse them.

---

## 2. Types of Guidance That Shaped the Project

Below are **recurring kinds of instructions** you gave and how they were applied. Use these as a checklist when directing AI on similar projects.

| Type of guidance | Example from this project | Outcome |
|------------------|---------------------------|---------|
| **Design before code** | “Show me the exact blueprint before you implement so I can sign off.” | Research flow, diagram flow, and tool gateway were designed in docs first; implementation followed. |
| **Transparency over silence** | “All steps need to be informed; no silent failures.” “I need 100% transparency on what is going on with LLMs and external tools.” | Feature-status API, live SSE steps with timings, exact Tavily errors surfaced, quality check with scores and reasons. |
| **Explainability** | “The quality check doesn’t give me explainability; I need a score and why or why not it meets criteria.” “Explain why the match—origin/destination, features.” | Quality check returns score + reason per criterion; KB hits include “why_match”; research shows key results before synthesis. |
| **Professional standards** | “Target state architecture is nonsense; I need a very professional diagram—refer Microsoft reference architectures.” | Template replaced by LLM-first design phase; diagram follows reference-arch guidelines; DOCX embeds PNG. |
| **Clean state on re-run** | “When I run research or regenerate report, you must clean up everything and regenerate.” “Give a provision to research again and regenerate report even if created once.” | Clear artifacts (approach, report, QC, research details, diagram folder) on research; report/QC clear on summarize; UI always allows “Run research” and “Regenerate report.” |
| **Human-in-the-loop** | “Add an option to ask a human if you need further data or clarification; goal is useful and accurate—ask as much as you need.” | Diagram design phase can return clarification questions; UI shows them and “Submit answers” or “Generate anyway.” |
| **Validation and sanity** | “Run sanity checks so data entered is not junk; flag unreasonable values.” | Profile validation (mandatory fields, LLM-based content checks, RTO/RPO hints); validation gates submission. |
| **Config and ops clarity** | “I want an informed message if LangChain/Tavily is not running because of API keys; all steps need to be informed.” “What’s the best architecture to load .env?” | Feature-status API; “Reload .env” without restart; docs for .env and config loading. |
| **Extensibility** | “Create a standard framework for tool calling so in future it’s easier to add Teams, WhatsApp, email.” | Tool Gateway (direct/MCP/UTC); extension guide; Tavily and LLM behind the same patterns. |

---

## 3. Chronological Narrative of Major Iterations

### 3.1 Foundation and flexibility

- **You asked for:** Flexible architecture so a different LLM could be used; one umbrella design doc with links to wireframes, decision matrix, etc.
- **Guidance style:** “Make it seamless,” “single umbrella document.”
- **Outcome:** LLM provider abstraction (`get_llm`), design docs consolidated and cross-linked; architecture doc and index updated.

### 3.2 Assessment module and validation

- **You asked for:** First module step-by-step; mandatory fields, required indicators, validation before proceeding; sanity and LLM-based checks to prevent junk input; hints (e.g. RTO/RPO for critical apps).
- **Guidance style:** “Don’t show warnings at the start; only when they proceed,” “standardize,” “run sanity so data is not junk.”
- **Outcome:** Profile pillars with required/optional; validation per section; LLM content validation; RTO/RPO hints; validation gates submission.

### 3.3 Two-role workflow pivot

- **You asked for:** Application User (submit only, no research/report) and Admin (view requests, run research, use KB, add guidance, generate/edit/download reports). “Update all design documents, wireframes, etc. based on this pivot.”
- **Guidance style:** Clear role split; design and docs updated before implementation.
- **Outcome:** [MIGRATION_REQUEST_FLOW.md](./MIGRATION_REQUEST_FLOW.md), updated architecture, wireframes, Admin Command Center design; Phase 1 (user flow) then Phase 2 (admin flow).

### 3.4 Research: explainability and official docs

- **You asked for:** (1) Query KB first, (2) clear confidence score and explainability (why match: origin/destination, features), (3) if below threshold, research official docs (e.g. Microsoft Learn) via web search (Tavily), (4) summarize with references and rationale, (5) show as live updates (SSE).
- **Guidance style:** “Show me the exact blueprint before you implement.”
- **Outcome:** [RESEARCH_FLOW_BLUEPRINT.md](./RESEARCH_FLOW_BLUEPRINT.md); KB confidence, per-hit “why_match,” official-doc search via Tool Gateway (Tavily), streaming SSE; research_details stored and shown in UI.

### 3.5 Transparency and live steps

- **You asked for:** “Live detailed steps like in Cursor: thinking… then retrieving… took X seconds, summarizing, got these key results—100% transparency on what is going on with LLMs and external tools.”
- **Guidance style:** “I have no clue what is returned from Tavily or how the LLM extracted information—give transparency.”
- **Outcome:** SSE events with timings (phase, kb_results, confidence, official_search_results, key_results, done); “Document retrieval” section with KB hits and Tavily results; synthesis step and total duration in UI.

### 3.6 Quality check with explainability

- **You asked for:** “A quality check so the report is comprehensive, actionable, useful.” Then: “The quality check doesn’t give explainability; I need a score and why or why not it meets each criterion.”
- **Guidance style:** Move from binary pass/fail to scored, explained criteria.
- **Outcome:** Quality check returns score (0–100) and reason per criterion (comprehensive, actionable, useful, diagrams); overall_pass from thresholds; suggestions; UI shows score + reason per criterion.

### 3.7 Config, .env, and feature status

- **You asked for:** “Informed message if LangChain/LangSmith/Tavily is not running (API keys, limits); all steps informed; how to add keys.” “Best architecture to load .env; not reload on every request.”
- **Guidance style:** No silent failures; one-time reload without restart.
- **Outcome:** Feature-status API; “Reload .env” button and endpoint; [CONFIG_AND_ENV.md](./CONFIG_AND_ENV.md); load-once, reload-on-demand.

### 3.8 Tavily and errors

- **You asked for:** “Give exact error and reason; run debug as needed”—surface the real Tavily API error, not a generic message.
- **Guidance style:** Transparency even in failure.
- **Outcome:** TavilySearchError with HTTP status/body; router preserves Tavily messages in user-facing errors.

### 3.9 Diagram: from template to design-led

- **You asked for:** “Target state architecture is nonsense; I need a very professional diagram—refer Microsoft reference architectures.” Then: “Properly prompt the LLM, give design instructions before generating the diagram; include data producers/consumers, interfaces, inbound/outbound, layers, observability; add human-in-the-loop if you need more data.”
- **Guidance style:** Design first; professional standards; ask when unclear.
- **Outcome:** [TARGET_ARCHITECTURE_DIAGRAM_DESIGN.md](./TARGET_ARCHITECTURE_DIAGRAM_DESIGN.md); Phase 1 (LLM architecture design with guidelines) → optional HITL (clarification questions) → Phase 2 (Mermaid from design) → export .mmd + PNG; diagram embedded in report and DOCX.

### 3.10 Diagram as artifact, not just markdown

- **You asked for:** “Perhaps build the diagram properly—e.g. use Mermaid to create a full diagram, then export that file and use an editable file or PNG so I see a proper diagram.”
- **Guidance style:** Deliver usable artifacts (file + image), not only markdown.
- **Outcome:** Mermaid rendered via mermaid.ink to PNG; .mmd and PNG saved under `data/assessment_diagrams/{id}/`; API serves PNG and .mmd; report and DOCX embed the image; “Download PNG” and “Download .mmd (editable)” in UI.

### 3.11 Cleanup on re-run and regenerate

- **You asked for:** “When I run research or regenerate report, clean up everything.” “Give a provision to research again and regenerate report even if created once; if admin/user opts for that, clean up and regenerate everything.”
- **Guidance style:** Re-run should leave no stale state.
- **Outcome:** On “Run research”: clear approach, report, QC, research_details, and diagram folder. On “Generate report”: clear report and QC, then regenerate. UI always offers “Run research” and “Generate report” / “Regenerate report.”

---

## 4. Document and Code Map (Where to Look)

| Topic | Document or location |
|-------|------------------------|
| Two-role flow | [MIGRATION_REQUEST_FLOW.md](./MIGRATION_REQUEST_FLOW.md) |
| Research flow (KB, confidence, official docs, SSE) | [RESEARCH_FLOW_BLUEPRINT.md](./RESEARCH_FLOW_BLUEPRINT.md) |
| Diagram design (LLM-first, HITL) | [TARGET_ARCHITECTURE_DIAGRAM_DESIGN.md](./TARGET_ARCHITECTURE_DIAGRAM_DESIGN.md) |
| Tool Gateway and extensions | [TOOL_GATEWAY_DESIGN.md](./TOOL_GATEWAY_DESIGN.md), [TOOL_EXTENSION_GUIDE.md](./TOOL_EXTENSION_GUIDE.md) |
| Config and .env | [CONFIG_AND_ENV.md](./CONFIG_AND_ENV.md), [ENV_REFERENCE.md](./ENV_REFERENCE.md) |
| Profile validation | [PROFILE_VALIDATION.md](./PROFILE_VALIDATION.md) |
| Architecture overview | [ARCHITECTURE_DESIGN.md](./ARCHITECTURE_DESIGN.md) |
| Code review path | [CODE_REVIEW_GUIDE.md](./CODE_REVIEW_GUIDE.md) |
| Pydantic usage | [PYDANTIC_MODELS.md](./PYDANTIC_MODELS.md) |

---

## 5. Takeaways for Using AI in Development

1. **Lock the design in writing first** when behavior or flow is non-trivial (research, diagram, tools). Ask for a blueprint or design doc and approve it before implementation.
2. **Insist on transparency and explainability** for any LLM or external service: live steps, timings, errors, scores, and reasons so users and operators can trust and debug.
3. **Reject generic or “nonsense” output** and ask for professional standards (reference architectures, proper artifacts like PNG + editable source).
4. **Define “clean state”** for re-runs (research, regenerate report) and implement full cleanup so re-running never leaves stale data or UI.
5. **Use human-in-the-loop** when accuracy matters and the model might need more data; expose questions in the UI and allow “answer” or “proceed anyway.”
6. **Keep a narrative like this** so the team (and future you) can see how guidance and iterations led to the current product and reuse the same patterns in the next project.
7. **Docs “duplicate” means same content in two paths** (e.g. root vs subdir after a reorg), not “HTML vs MD.” When consolidating docs, keep HTMLs where the project webpages (e.g. GitHub Pages) expect them so links don’t break; remove only redundant copies (e.g. root .md when subdir has the canonical copy).

---

*This narrative can be updated as you add more iterations. Add new sections under §3 and new rows in §2 and §4 as the product evolves.*
