"""Summarizer Agent: Profile + Approach → Assessment Report. Standalone, traceable via LangSmith."""

from langchain_core.messages import HumanMessage, SystemMessage

from backend.services.assessment.models import ApplicationProfile
from backend.services.llm_provider import get_llm


def run_summarize(profile: ApplicationProfile, approach_document: str) -> str:
    """
    Produce assessment report from profile + approach document.
    Uses get_llm for provider-agnostic switching; LangSmith traces when LANGCHAIN_TRACING_V2=true.
    """
    llm = get_llm(temperature=0.3)

    system_prompt = """You are a migration architect writing a formal assessment report. Given an application profile (with architecture pillars: overview, data, DR, cost, security, timeline) and an approach document, produce a detailed ASSESSMENT REPORT in markdown with these sections:

1. **Executive Summary** – 2–3 sentences
2. **Current State** – Application, tech stack, environment, dependencies, data
3. **Target Architecture** – Recommended target (e.g. Azure/AWS/GCP services)
4. **Migration Strategy** – Lift-and-shift, refactor, or re-platform with rationale
5. **Data & DR Considerations** – Data migration, backup, failover
6. **Security & Compliance** – Auth, encryption, compliance frameworks
7. **Cost & Timeline** – Budget, phases, go-live
8. **Risks & Mitigations** – Known risks and how to address them

Be professional, concise, and actionable. Use markdown formatting."""

    profile_text = profile.to_context_text()
    user_content = f"""## Application Profile (Architecture Pillars)
{profile_text}

## Approach Document
{approach_document}

Produce the full assessment report in markdown."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
    response = llm.invoke(messages)
    return response.content if hasattr(response, "content") else str(response)
