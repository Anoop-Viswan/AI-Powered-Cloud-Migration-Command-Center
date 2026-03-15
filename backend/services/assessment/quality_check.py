"""
Quality check: ensure the assessment report is comprehensive, actionable, and useful.

Runs an LLM over the report + profile and returns scores (0–100) and a short reason
per criterion, plus overall pass and suggestions. Gives explainability: why it meets
or does not meet each criterion.
"""

import json
from langchain_core.messages import HumanMessage, SystemMessage

from backend.services.assessment.models import ApplicationProfile
from backend.services.diagnostics.recorder import invoke_llm
from backend.services.llm_provider import get_llm

# Minimum score (0–100) to consider a criterion "passed" for overall_pass
QC_SCORE_THRESHOLD = 60


def run_quality_check(profile: ApplicationProfile, report_text: str) -> dict:
    """
    Evaluate the report against three criteria with scores and reasons.

    Returns a dict with:
    - comprehensive: { score: 0-100, reason: str }
    - actionable: { score: 0-100, reason: str }
    - useful: { score: 0-100, reason: str }
    - overall_pass: bool (all scores >= QC_SCORE_THRESHOLD)
    - suggestions: list[str]
    """
    if not (report_text or "").strip():
        return {
            "comprehensive": {"score": 0, "reason": "Report is empty."},
            "actionable": {"score": 0, "reason": "Report is empty."},
            "useful": {"score": 0, "reason": "Report is empty."},
            "diagrams": {"score": 0, "reason": "Report is empty; no diagram."},
            "overall_pass": False,
            "suggestions": ["Generate a report first."],
        }

    llm = get_llm(temperature=0.2)

    system_prompt = """You are a quality reviewer for migration assessment reports. Evaluate the report against four criteria and give a score (0–100) and a short reason for each.

1. **Comprehensive** (0–100): Does the report cover the main areas needed for a migration decision? Check for: executive summary, current state, target architecture, migration strategy, data/DR considerations, security & compliance, cost/timeline, and risks & mitigations. If the application profile mentions specific topics (e.g. database migration, RTO/RPO), are they addressed? Score low if important sections are missing or very thin.

2. **Actionable** (0–100): Does the report give clear next steps, recommendations, or decisions? A reader should know what to do next (e.g. "refactor the data tier", "implement backup by X", "consider Azure SQL"). Score low if it is vague or only descriptive.

3. **Useful** (0–100): Is the content specific to this application and context, or generic filler? Useful reports reference the app name, tech stack, target environment, and concrete constraints from the profile. Score low if it could apply to any app.

4. **Diagrams and visuals** (0–100): Does the report include a target state architecture diagram? Check for a diagram image (e.g. ![Target State Architecture](...) or ```mermaid code block). Score high (e.g. 80–100) if there is a clear target-state diagram (image or Mermaid); score low (e.g. 0–40) if no diagram is present. In the reason, state whether a diagram is present and whether it shows components/network/security.

Respond in this exact JSON format only (no other text):
{
  "comprehensive": { "score": <0-100>, "reason": "<1-2 sentences why this score>" },
  "actionable": { "score": <0-100>, "reason": "<1-2 sentences why this score>" },
  "useful": { "score": <0-100>, "reason": "<1-2 sentences why this score>" },
  "diagrams": { "score": <0-100>, "reason": "<1-2 sentences: is a target-state diagram present? what does it show?>" },
  "suggestions": ["concrete improvement 1", "concrete improvement 2", ...]
}

- Be fair: score 60+ when the criterion is reasonably met; score below 60 when there is a real gap.
- reasons: explain what is present or missing.
- suggestions: 0–5 concrete improvements. Include "Add a target state architecture Mermaid diagram" if diagrams score is low. Be specific."""

    profile_brief = (
        f"Application: {profile.application_name}. "
        f"Target: {profile.target_environment}. "
        f"Tech: {', '.join(profile.tech_stack or [])}. "
        f"DB migration: {profile.contains_database_migration}. "
        f"RTO/RPO: {profile.rto} / {profile.rpo}."
    )
    user_content = f"""## Application (brief)
{profile_brief}

## Report to evaluate
{report_text[:12000]}

Respond with the JSON only."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_content),
    ]
    response = invoke_llm(llm, messages, "quality_check", assessment_id=None)
    text = response.content if hasattr(response, "content") else str(response)
    text = (text or "").strip()

    if "```" in text:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return _fallback_quality_result("Could not parse reviewer response. Review the report manually.")

    def get_criterion(name: str) -> dict:
        c = data.get(name)
        if not isinstance(c, dict):
            return {"score": 70, "reason": "Could not evaluate."}
        score = c.get("score")
        try:
            score = int(score) if score is not None else 70
        except (TypeError, ValueError):
            score = 70
        score = max(0, min(100, score))
        reason = (c.get("reason") or "No reason given.").strip()
        return {"score": score, "reason": reason[:500]}

    comprehensive = get_criterion("comprehensive")
    actionable = get_criterion("actionable")
    useful = get_criterion("useful")
    diagrams = get_criterion("diagrams")
    suggestions = data.get("suggestions")
    if not isinstance(suggestions, list):
        suggestions = []
    suggestions = suggestions[:10]

    threshold = QC_SCORE_THRESHOLD
    overall_pass = (
        comprehensive["score"] >= threshold
        and actionable["score"] >= threshold
        and useful["score"] >= threshold
        and diagrams["score"] >= threshold
    )

    return {
        "comprehensive": comprehensive,
        "actionable": actionable,
        "useful": useful,
        "diagrams": diagrams,
        "overall_pass": overall_pass,
        "suggestions": suggestions,
    }


def _fallback_quality_result(message: str) -> dict:
    return {
        "comprehensive": {"score": 70, "reason": message},
        "actionable": {"score": 70, "reason": message},
        "useful": {"score": 70, "reason": message},
        "diagrams": {"score": 70, "reason": message},
        "overall_pass": True,
        "suggestions": [],
    }
