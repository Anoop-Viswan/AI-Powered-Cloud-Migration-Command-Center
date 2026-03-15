# Target State Architecture Diagram – Design (LLM-First + Guidelines)

**Status:** Implemented  
**Purpose:** Define how the target-state architecture diagram should be produced: **design instructions from an LLM first** (using profile, KB, reference-arch guidance), then **diagram generation** from that design. Includes your guidelines (target platform, data/connections, layers, observability, human-in-the-loop). **No code changes until you approve.**

---

## 1. Current State (As-Is)

| Aspect | What we do today | Gap |
|--------|-------------------|-----|
| **Input** | Profile only (target env, app name, DB types, etc.) | No structured “design brief”; no KB or reference-arch context passed for the diagram. |
| **Diagram** | **Template-based** Mermaid: fixed structure (edge → VNet → app tier → data tier) with labels filled from profile. | Same shape for every assessment; does not reflect actual data flows, interfaces, producers/consumers, or observability. |
| **LLM** | LLM is used only for the **report narrative**; it is **not** asked to produce architecture design instructions before the diagram. | Diagram is not driven by “what the migration actually looks like” from data and requirements. |

So the diagram can be **incorrect or generic** because we never ask the LLM to reason about target platform, components, interfaces, and connections before drawing.

---

## 2. Intended Behavior (To-Be)

**Main goal:** Provide a **useful and accurate** target-state architecture diagram that reflects **how the system looks after migration**.

**Principle:** **Target state = post-migration view.** The diagram should be based on:

1. **Target platform and components** (e.g. Azure / AWS / GCP and the right services).
2. **All data and requirements we have** (profile + approach document + optional KB/reference-arch).
3. **Explicit design step:** An LLM produces **detailed design instructions** (or a “design brief”) **before** we generate the diagram. The diagram generator (Mermaid) then follows those instructions so the diagram matches the intended architecture.

---

## 3. Guidelines for Target State (Your Requirements)

These will be encoded in prompts and design rules:

1. **Look at target platform and components**  
   Use profile `target_environment` (azure/aws/gcp) and choose appropriate services (e.g. App Service, Azure SQL, Front Door for Azure).

2. **Pass all data and requirements we have**  
   - Application profile (overview, architecture, data, BC/DR, cost, security, project).  
   - Approach document (from research: strategy, steps, references).  
   - If the design step needs more context: **look at KB** (e.g. reuse research hits or run a targeted query for “target architecture” / “reference”), or **look for reference architectures** (e.g. Microsoft Learn, cloud provider docs) when needed.

3. **Cover the full picture**  
   Ensure the design (and thus the diagram) includes:
   - **Data producers and consumers** (who produces data, who consumes it).
   - **All interfaces and connections** (APIs, queues, events).
   - **Inbound and outbound** flows (ingress, egress, ETLs if any).
   - **Layers and their interactions:**
     - Front-end layer (web, mobile, gateways).
     - Back-end / middleware (APIs, app tier, message/event layer).
     - Database / storage layer.
     - Interactions between these (e.g. front-end → API → DB; async flows).
   - **Observability stack** (logging, metrics, tracing – e.g. App Insights, CloudWatch, etc.).

4. **Human-in-the-loop (HITL)**  
   - If the LLM or the design step determines that **further data or clarification** is needed (e.g. “unclear who consumes this data”, “missing interface details”), **ask**.  
   - Add an **option to ask a human** for:
     - Missing or ambiguous requirements.  
     - Clarification on interfaces, producers/consumers, or observability.  
   - Goal: **useful and accurate** – “ask as much as you need” rather than guess.

---

## 4. Proposed Approach (High Level)

Two-phase flow:

```
[Profile + Approach + optional KB/reference context]
                    ↓
    ┌───────────────────────────────────────────────┐
    │  Phase 1: Architecture design (LLM)           │
    │  - Input: profile, approach, guidelines        │
    │  - Optional: KB hits or reference-arch hints  │
    │  - Output: "Design instructions" (structured   │
    │    text or JSON) + optional "clarifications"  │
    │    (questions for human-in-the-loop)          │
    └───────────────────────────────────────────────┘
                    ↓
    ┌───────────────────────────────────────────────┐
    │  If clarifications requested → show to user   │
    │  (Admin). User can answer or skip; re-run     │
    │  design when answers are provided.            │
    └───────────────────────────────────────────────┘
                    ↓
    ┌───────────────────────────────────────────────┐
    │  Phase 2: Diagram generation                  │
    │  - Input: design instructions from Phase 1    │
    │  - Output: Mermaid diagram (then export .mmd  │
    │    + PNG as today)                            │
    └───────────────────────────────────────────────┘
```

- **Phase 1** ensures we have a clear, requirement-driven **design** (target platform, components, layers, interfaces, data flows, observability, and optionally HITL questions).  
- **Phase 2** turns that design into a **concrete diagram** (so the diagram is “correct” by construction relative to the design).

---

## 5. Phase 1: Architecture Design (LLM) – Detail

### 5.1 Inputs to the LLM

- **Application profile** (full: overview, architecture, data, BC/DR, cost, security, project).  
- **Approach document** (research output: strategy, steps, references).  
- **Guidelines** (in system prompt) that restate the rules above:
  - Target state = post-migration.
  - Consider target platform and components; use all data and requirements; use KB or reference architectures if more info is needed.
  - Include: data producers/consumers, interfaces, connections, inbound/outbound, front-end, back-end/middleware, DB layer, interactions, observability.
  - If something is missing or ambiguous, **output clarification questions** for a human instead of guessing.

### 5.2 Optional context (when available)

- **KB:** If we have `research_details` (KB hits + official docs), we can pass a short summary or key snippets so the design can align with “what we found” (e.g. “KB suggests Azure SQL + App Service for this workload”).
- **Reference architectures:** Prompt can instruct the LLM to “align with standard reference architectures for [Azure|AWS|GCP] for this workload type” and, if we ever have a “reference-arch” retrieval step, pass those snippets here.

### 5.3 Output of Phase 1 (design instructions)

We need a **structured** output so Phase 2 can consume it reliably. Two options:

**Option A – Structured text (recommended for v1)**  
- One LLM call.  
- Output: a **design instructions** block (markdown or plain text) that explicitly lists:
  - Target platform (e.g. Azure).
  - **Components** (e.g. Front Door, App Service, Azure SQL, Storage, Key Vault, App Insights).
  - **Layers** (edge, app tier, data tier, identity/security, observability).
  - **Flows** (e.g. Users → Front Door → App Service → Azure SQL; App → Key Vault; App → Storage; App → App Insights).
  - **Data producers/consumers** (e.g. “App Service produces events to …”, “Storage consumed by …”).
  - **Interfaces** (e.g. REST API, private endpoints).
- Optional: a separate short block **“Clarifications needed”** (list of questions). If non-empty, we do **not** run Phase 2 yet; we show these to the user and allow them to provide answers (and optionally re-run Phase 1).

**Option B – JSON**  
- Same content as above but in a fixed JSON schema (e.g. `components`, `layers`, `flows`, `clarifications`).  
- Easier for code to parse; slightly more fragile if the LLM deviates from the schema.  
- Can be introduced in a later iteration.

**Recommendation:** Start with **Option A** (structured text). Phase 2 can be implemented by either (1) a second LLM call that takes “design instructions” and outputs Mermaid, or (2) a template that maps common patterns from the design text into Mermaid (with an LLM fallback for complex cases).

### 5.4 Human-in-the-loop

- In the **system prompt**, instruct the LLM: *“If critical information is missing or ambiguous (e.g. unclear data flows, unknown consumers), output a ‘Clarifications needed’ section with specific questions. Do not invent; ask.”*
- **Backend:** If the design response contains a “Clarifications needed” section (e.g. detected by a marker or a small parser), we:
  - Store the **design instructions** and the **clarification questions** (e.g. in assessment state or a small “diagram_design” blob).
  - Return to the client that **diagram is pending clarification** and include the questions.
- **Frontend (Admin):**  
  - Show a message: “Architect: please clarify the following so we can generate an accurate diagram.”  
  - List the questions; provide a free-text or form for answers (and/or “Skip / generate anyway”).  
  - On submit: optionally **re-run Phase 1** with the answers appended to the context, then run Phase 2.  
- **Skip path:** User can choose “Generate diagram anyway” so we still run Phase 2 from the current design (with possible gaps). So HITL is an **option**, not a blocker.

---

## 6. Phase 2: Diagram Generation – Detail

- **Input:** Design instructions (and optionally clarification answers) from Phase 1.  
- **Process:**
  - **Option 2a:** **LLM generates Mermaid** from the design instructions (one prompt: “Given these design instructions, output only valid Mermaid flowchart code for the target state architecture.”). We already have export to .mmd and PNG; we keep that.  
  - **Option 2b:** **Template + rules** that map “design instructions” (parsed or key phrases) to Mermaid (e.g. if “Azure”, “App Service”, “Azure SQL” appear, use an Azure template and fill in the rest from the design). More deterministic, but less flexible.  
- **Recommendation:** **Option 2a** (LLM generates Mermaid from design) so we can support arbitrary platforms and flows (producers/consumers, observability) without maintaining many templates. We can add basic validation (e.g. “contains flowchart/graph”) and a fallback to a minimal template if the output is invalid.

---

## 7. Where This Runs in the App Flow

- **Today:** Diagram is built during **“Generate report”** (summarize step): we build Mermaid from profile (template), export .mmd + PNG, inject image into report.  
- **Proposed:**  
  - **Option 1:** Keep diagram inside “Generate report”. When the user clicks “Generate report”, we run **Phase 1 (design)** → if no clarifications, run **Phase 2 (Mermaid)** → export .mmd + PNG → then run the rest of summarize (report narrative + diagram image). If clarifications are needed, we return “Report generation needs clarification” and show questions; after the user answers and clicks again, we re-run Phase 1 (with answers) then Phase 2 and summarize.  
  - **Option 2:** Add a separate **“Generate / refresh diagram”** step (e.g. before or after research). Phase 1 + Phase 2 run there; the diagram is stored and then used when the user runs “Generate report”. So diagram can be refined (and HITL done) independently.  

**Recommendation:** **Option 1** for simplicity (one “Generate report” flow that includes design → diagram → report). We can later split “diagram only” into a separate action if needed.

---

## 8. Summary for Sign-Off

| Item | Proposal |
|------|----------|
| **Design first** | LLM produces “architecture design instructions” (target platform, components, layers, flows, producers/consumers, interfaces, observability) **before** any diagram. |
| **Guidelines in prompt** | Target state = post-migration; use all data and requirements; use KB/reference if needed; include producers/consumers, interfaces, inbound/outbound, front-end, back-end, DB, observability; ask for clarification when missing. |
| **Diagram from design** | Phase 2 takes design instructions and generates Mermaid (LLM-generated Mermaid recommended); then export .mmd + PNG as today. |
| **Human-in-the-loop** | If design step outputs “Clarifications needed”, show questions in Admin UI; user can answer and re-run, or skip and generate anyway. |
| **Integration** | Design + diagram run inside “Generate report”; optional later: separate “Generate diagram” action. |

Once you approve this approach (and any tweaks you want, e.g. JSON vs text for Phase 1, or separate “Generate diagram” step), implementation can follow this design.
