"""Summarizer Agent: Profile + Approach → Assessment Report. Standalone, traceable via LangSmith.

Flow: generate target-state Mermaid diagram from profile (template-based, Microsoft/reference
architecture style), then produce full report that includes the diagram. Diagrams are created
before quality checks run.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from backend.services.assessment.models import ApplicationProfile
from backend.services.diagnostics.recorder import invoke_llm
from backend.services.llm_provider import get_llm


def run_summarize(
    profile: ApplicationProfile,
    approach_document: str,
    diagram_image_url: str | None = None,
    clarification_context: str | None = None,
) -> str:
    """
    Produce assessment report from profile + approach document.
    If diagram_image_url is provided, the report will include the target-state diagram as an image
    (proper PNG) in section 4 instead of raw Mermaid in markdown.
    If clarification_context is provided (e.g. architect Q&A from human-in-the-loop), the report
    must reflect those prompts and answers so the reader sees what was asked and how it was resolved.
    """
    llm = get_llm(temperature=0.3)
    system_prompt = (
        """You are a migration architect writing a formal assessment report. Given an application profile (with architecture pillars: overview, data, DR, cost, security, timeline) and an approach document, produce a detailed ASSESSMENT REPORT in markdown with these sections:

1. **Executive Summary** – 2–3 sentences
2. **Current State** – Application, tech stack, environment, dependencies, data
3. **Target Architecture** – Recommended target (e.g. Azure/AWS/GCP services); short narrative only here
4. **Target State Architecture (diagram)** – You MUST include the diagram image in this section. The user message will provide the exact markdown for the image: a line like ![Target State Architecture](IMAGE_URL). Paste that line verbatim (so the diagram displays as a proper image). Add one short sentence that the diagram is aligned to Microsoft/cloud reference architecture (e.g. Azure N-tier). Do not use a mermaid code block here; use only the image markdown provided.

5. **Migration Strategy** – Lift-and-shift, refactor, or re-platform with rationale
6. **Data & DR Considerations** – Data migration, backup, failover
7. **Security & Compliance** – Auth, encryption, compliance frameworks
8. **Cost & Timeline** – Budget, phases, go-live
9. **Risks & Mitigations** – Known risks and how to address them

If the user provides "Architect clarifications" (questions asked during design and the answers given), you MUST reflect them in the report: include a short subsection (e.g. under Target Architecture or as "Design assumptions / clarifications") that states what was clarified and how it was resolved, so the report is complete and the prompts asked during research are reflected in the final output.

Be professional, concise, and actionable. Use markdown formatting. Section 4 must contain the image markdown line exactly as given."""
    )

    if diagram_image_url:
        diagram_instruction = "In section 4 (Target State Architecture) write: a heading, then the line ![Target State Architecture](DIAGRAM_URL) with DIAGRAM_URL replaced by: " + diagram_image_url + " then one sentence that the diagram follows reference architecture. Use that exact image markdown so the diagram displays."
    else:
        diagram_instruction = "In section 4 (Target State Architecture) write a short note that the diagram can be generated and downloaded from the assessment page."

    profile_text = profile.to_context_text()
    user_parts = [
        "## Application Profile (Architecture Pillars)",
        profile_text,
        "",
        "## Approach Document",
        approach_document,
    ]
    if clarification_context and clarification_context.strip():
        user_parts.extend(["", "## Architect clarifications (reflect these in the report)", clarification_context.strip()])
    user_parts.extend(["", "## Instruction for section 4", diagram_instruction, "", "Produce the full assessment report in markdown."])
    user_content = "\n".join(user_parts)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
    response = invoke_llm(llm, messages, "summarize", assessment_id=None)
    return response.content if hasattr(response, "content") else str(response)
