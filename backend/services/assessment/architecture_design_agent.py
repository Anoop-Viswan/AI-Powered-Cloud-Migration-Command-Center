"""
Phase 1: Architecture design (LLM) for target-state diagram.

Produces detailed design instructions from profile + approach + optional KB/research context.
Follows TARGET_ARCHITECTURE_DIAGRAM_DESIGN.md: target state = post-migration; include
platform, components, layers, data producers/consumers, interfaces, observability; optional
clarification questions (human-in-the-loop).
"""

import re
from typing import NamedTuple

from langchain_core.messages import HumanMessage, SystemMessage

from backend.services.assessment.models import ApplicationProfile
from backend.services.diagnostics.recorder import invoke_llm
from backend.services.llm_provider import get_llm


class DesignResult(NamedTuple):
    """Result of Phase 1: design instructions and optional clarification questions."""
    design_instructions: str
    clarifications_needed: list[str]


def _research_context_summary(research_details: dict | None) -> str:
    """Build a short summary from research_details (KB hits + official docs) for design context."""
    if not research_details:
        return ""
    parts = []
    kb_hits = research_details.get("kb_hits") or []
    if kb_hits:
        sources = [h.get("file_path") or "KB" for h in kb_hits[:5]]
        parts.append(f"KB sources used in research: {', '.join(sources)}.")
    official_docs = research_details.get("official_docs") or []
    if official_docs:
        titles = [d.get("title") or d.get("url", "")[:50] for d in official_docs[:3]]
        parts.append(f"Official docs referenced: {', '.join(titles)}.")
    if not parts:
        return ""
    return " " + " ".join(parts)


def run_architecture_design(
    profile: ApplicationProfile,
    approach_document: str,
    research_details: dict | None = None,
    clarification_answers: list[str] | None = None,
    skip_clarification: bool = False,
) -> DesignResult:
    """
    Phase 1: Produce architecture design instructions for the target state (post-migration).

    Uses profile, approach document, and optional research context. If clarification_answers
    is provided, appends them so the LLM can refine the design. Returns design_instructions
    and any clarifications_needed (questions for human-in-the-loop).
    """
    llm = get_llm(temperature=0.2)
    profile_text = profile.to_context_text()
    target = (profile.target_environment or "azure").lower()
    kb_context = _research_context_summary(research_details)

    system_prompt = """You are an enterprise architect designing the TARGET STATE architecture for a cloud migration. The target state is how the system will look AFTER migration.

Guidelines you must follow:
1. **Target platform and components**: Use the target cloud (Azure/AWS/GCP) from the profile and choose appropriate services (e.g. for Azure: Front Door, App Service, Azure SQL, Storage, Key Vault, App Insights).
2. **Use all data and requirements**: Base the design on the full application profile (overview, architecture, data, BC/DR, security, project) and the approach document from research. If the profile mentions ingestion, ingress, egress, ETLs, RTO/RPO, or integrations, include them.
3. **Cover the full picture**. Your design instructions must explicitly include:
   - **Data producers and consumers** (who produces data, who consumes it; ingress/egress sources and destinations).
   - **All interfaces and connections** (APIs, queues, events, private endpoints).
   - **Inbound and outbound** flows (how traffic and data enter and leave the system).
   - **Layers and their interactions**:
     - Front-end layer (users, web, gateways).
     - Back-end / middleware (APIs, app tier, message/event layer).
     - Database / storage layer.
     - How these layers connect (e.g. front-end → API → DB; async flows).
   - **Observability stack** (logging, metrics, tracing – e.g. Application Insights, CloudWatch, etc.).
4. **Human-in-the-loop**: Unless instructed otherwise, if critical information is missing or ambiguous (e.g. unclear data flows, unknown consumers, missing interfaces), output a "Clarifications needed" section with specific, numbered questions. Do not invent; ask. If you have enough information, leave that section empty.

Output format (use these exact section headers):
---
## Design instructions
[Your detailed design: target platform, components, layers, data flows, producers/consumers, interfaces, observability. Be specific so a diagram can be generated from this.]

## Clarifications needed
[Either: "None." OR a numbered list of questions for the architect, one per line.]
---
Output only the content between the --- markers. No other text before or after."""

    if skip_clarification:
        system_prompt += "\n\nImportant: Do not output any Clarifications needed; leave that section as 'None.' Produce the best design with the information available."
    user_parts = [
        "## Application profile (all pillars)",
        profile_text,
        "",
        "## Approach document (from research)",
        (approach_document or "")[:8000],
    ]
    if kb_context:
        user_parts.extend(["", "## Research context", kb_context])
    if clarification_answers:
        user_parts.extend([
            "",
            "## Architect's answers to previous clarification questions",
            "\n".join(f"Q{i+1} answer: {a}" for i, a in enumerate(clarification_answers)),
            "",
            "Please refine the design using these answers and output updated design instructions. If anything is still unclear, add new questions to Clarifications needed.",
        ])
    user_content = "\n".join(user_parts)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
    response = invoke_llm(llm, messages, "architecture_design", assessment_id=None)
    text = (response.content if hasattr(response, "content") else str(response)) or ""

    design_instructions = ""
    clarifications_needed: list[str] = []

    if "## Design instructions" in text:
        try:
            design_section = text.split("## Design instructions")[1].split("## Clarifications needed")[0].strip()
            design_instructions = design_section.strip()
        except IndexError:
            design_instructions = text.strip()
    else:
        design_instructions = text.strip()

    if "## Clarifications needed" in text:
        try:
            clar_section = text.split("## Clarifications needed")[1].strip()
            if clar_section and clar_section.lower() not in ("none.", "none", "n/a"):
                lines = [ln.strip() for ln in clar_section.split("\n") if ln.strip()]
                for ln in lines:
                    if re.match(r"^\d+[.)]\s*", ln):
                        q = re.sub(r"^\d+[.)]\s*", "", ln).strip()
                        if q:
                            clarifications_needed.append(q)
                    elif ln:
                        clarifications_needed.append(ln)
        except IndexError:
            pass

    return DesignResult(design_instructions=design_instructions or "Target state: see profile and approach.", clarifications_needed=clarifications_needed)


def run_mermaid_from_design(design_instructions: str) -> str:
    """
    Phase 2: Generate Mermaid flowchart code from architecture design instructions.

    Uses LLM to produce valid Mermaid so the diagram reflects the design (layers, flows,
    producers/consumers, observability). Returns raw Mermaid code (no markdown fence).
    """
    llm = get_llm(temperature=0.2)
    system_prompt = """You are an architect. Given detailed design instructions for a target-state (post-migration) architecture, output ONLY valid Mermaid flowchart code. No explanation, no markdown fence.

Requirements for the Mermaid:
- Use "flowchart TB" or "flowchart LR" with subgraphs for layers (e.g. Internet/Edge, App Tier, Data Tier, Observability).
- Include: users/clients, edge (e.g. Front Door/WAF), application tier, data tier (DB, storage), identity/security, and observability (e.g. App Insights, logging).
- Show data flows and connections (--> or ---); label key flows (e.g. "HTTPS", "Private").
- Use proper service names from the design (e.g. Azure App Service, Azure SQL Database, Azure Storage).
- Keep it readable: 8–20 nodes. Use subgraph for grouping.
Output only the Mermaid code. No ```mermaid wrapper."""

    user_content = f"""## Design instructions to convert to diagram\n\n{design_instructions[:6000]}\n\nGenerate Mermaid flowchart code for this target state architecture."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
    response = invoke_llm(llm, messages, "mermaid_from_design", assessment_id=None)
    raw = (response.content if hasattr(response, "content") else str(response)) or ""
    if raw.strip().startswith("```"):
        lines = raw.strip().split("\n")
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)
    return raw.strip() or "flowchart TB\n  A[Application]\n  B[Data]\n  A --> B"
