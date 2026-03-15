"""
LLM-based content validation for application profile.
Builds a key-value map of all fields, defines expected value guidelines,
and flags placeholder/nonsense/deviant values (e.g. "I don't know", "good", "none").
"""

import json
import os
import re

from backend.services.assessment.models import ApplicationProfile


# ─── Internal map: profile attribute -> human-readable label (per screen) ─────
# Used to build the KV map and to display field names in findings.

FIELD_LABELS = {
    # 1. Overview
    "application_name": "Application name",
    "business_purpose": "Business purpose",
    "description": "Description",
    "user_count_estimate": "User count (estimate)",
    "priority": "Priority",
    "rto": "RTO (Recovery Time Objective)",
    "rpo": "RPO (Recovery Point Objective)",
    "compliance_requirements": "Compliance requirements",
    "known_risks": "Known risks",
    "constraints": "Constraints",
    "additional_notes": "Additional notes",
    # 2. Architecture
    "tech_stack": "Tech stack",
    "current_environment": "Current environment",
    "target_environment": "Target environment",
    "current_architecture_description": "Current architecture description",
    "current_architecture_diagram_path": "Current architecture diagram",
    "future_architecture_description": "Future architecture description",
    "future_architecture_diagram_path": "Future architecture diagram",
    # 3. Data
    "contains_database_migration": "Contains database migration",
    "total_data_volume": "Total data volume",
    "database_types": "Database types",
    "current_databases_description": "Current databases description",
    "target_databases_description": "Target databases description",
    "data_retention_requirements": "Data retention requirements",
    "data_ingestion": "Data ingestion",
    "data_ingress": "Ingress",
    "data_egress": "Egress",
    "etl_pipelines": "ETL pipelines",
    "data_migration_notes": "Data migration notes",
    # 4. BC & DR
    "current_dr_strategy": "Current DR strategy",
    "backup_frequency": "Backup frequency",
    "failover_approach": "Failover approach",
    "dr_testing_frequency": "DR testing frequency",
    "bc_dr_notes": "BC/DR notes",
    # 5. Cost
    "current_annual_cost": "Current annual cost",
    "migration_budget": "Migration budget",
    "cost_constraints": "Cost constraints",
    "licensing_considerations": "Licensing considerations",
    # 6. Security
    "authentication_type": "Authentication type",
    "encryption_at_rest": "Encryption at rest",
    "encryption_in_transit": "Encryption in transit",
    "pii_handling": "PII handling",
    "compliance_frameworks": "Compliance frameworks",
    # 7. Project
    "project_manager": "Project manager",
    "timeline_expectation": "Timeline expectation",
    "team_size": "Team size",
    "dependencies": "Dependencies",
    "integrations": "Integrations",
    "preferred_go_live": "Preferred go-live",
}


# ─── Expected value guidelines (what we expect per field / section) ───────────
# Shown to LLM so it can judge if values are placeholder, nonsense, or deviant.

EXPECTED_VALUE_GUIDELINES = """
## Expected value guidelines (by section)

**1. General Overview**
- application_name: A real application or system name (e.g. "OrderService"), not placeholder.
- business_purpose: Concrete description of what the app does (e.g. "Order processing and inventory"). NOT: "I don't know", "none", "good", "same as before", "N/A", "TBD", "to be determined" without detail.
- description: Optional; if filled, should add context, not "good", "fine", "same".
- user_count_estimate: Number or range (e.g. 1000, 10K-50K). NOT: "I don't know", "many", "few", "none".
- priority: One of critical/high/medium/low (valid).
- rto: Time duration (e.g. "4 hours", "1 day"). NOT: "I don't know", "none", "good", "asap", "minimal".
- rpo: Time duration (e.g. "1 hour", "15 min"). NOT: placeholder or vague.
- known_risks, constraints, additional_notes: If filled, should be substantive. Flag: "none", "n/a", "good", "I don't know", "no idea".

**2. Architecture**
- tech_stack: Technology names (e.g. Java, Spring Boot, Oracle). NOT: "various", "I don't know", "good", "standard", "legacy" only.
- current_environment / target_environment: Valid selection (on-prem, azure, etc.).
- current_architecture_description: Description of components (e.g. "Three-tier: web, app, DB"). NOT: "good", "I don't know", "architecture is good", "standard", "same as diagram", "none", "N/A", "complex" without detail.
- future_architecture_description: If filled, should describe target state. NOT: "same", "good", "TBD" without any detail.

**3. Data Management**
- contains_database_migration: "yes" or "no".
- total_data_volume: Size with unit (e.g. 500 GB, 2 TB). NOT: "I don't know", "lots", "none", "good".
- database_types: Database product names. NOT: "various", "I don't know", "none" when migration is Yes.
- current_databases_description: Concrete description of DBs. NOT: "good", "I don't know", "standard", "none".
- data_ingestion, data_ingress, data_egress, etl_pipelines: If filled, should be substantive. Flag placeholders.

**4. Business Continuity & DR**
- current_dr_strategy: Describe actual approach (e.g. "Daily backups to NAS"). NOT: "none", "I don't know", "good", "standard", "no DR".
- backup_frequency: e.g. daily, weekly. NOT: "I don't know", "none", "good".
- failover_approach: Describe strategy. NOT: placeholder.
- dr_testing_frequency: e.g. quarterly, annually. NOT: "I don't know", "never", "none".

**5. Cost**
- current_annual_cost, migration_budget: Amount or range if filled. NOT: "I don't know", "none", "good", "TBD" only.
- cost_constraints, licensing_considerations: If filled, substantive. Flag placeholders.

**6. Security**
- authentication_type: e.g. SAML, OAuth, AD, LDAP. NOT: "I don't know", "none", "good", "standard" only.
- encryption_at_rest, encryption_in_transit: e.g. AES-256, TLS 1.2. NOT: "I don't know", "none", "yes", "good".
- pii_handling, compliance_frameworks: If filled, substantive. Flag placeholders.

**7. Project & Timeline**
- project_manager, timeline_expectation, team_size: If filled, substantive. NOT: "I don't know", "none", "TBD" only.
- dependencies, integrations: If filled, names or description. NOT: "none", "various", "good" only.
- preferred_go_live: e.g. Q2 2025. NOT: "I don't know", "asap", "good" only.

**General rules**
- Flag any value that is clearly placeholder, vague, or non-informative: "I don't know", "idk", "none", "n/a", "N/A", "good", "fine", "same", "standard", "TBD", "to be determined", "no idea", "not sure", "same as above", "see above", "architecture is good", "data is good", "asap", "minimal", "various", "lots", "few", "many", "complex" (without detail), "legacy" (without detail).
- If the value is empty or the field was skipped, do NOT list it (we only validate filled fields).
- Only list fields where the VALUE deviates from what is expected or looks like nonsense/placeholder.
"""


def profile_to_kv_map(profile: ApplicationProfile) -> dict[str, str]:
    """Build a flat key -> value map for all non-empty profile fields. Keys are human-readable labels."""
    out: dict[str, str] = {}
    raw = profile.model_dump()
    for key, label in FIELD_LABELS.items():
        if key not in raw:
            continue
        val = raw[key]
        if val is None:
            continue
        if isinstance(val, list):
            s = ", ".join(str(x).strip() for x in val if x).strip()
            if not s:
                continue
            out[label] = s
        else:
            s = (val or "").strip()
            if not s:
                continue
            out[label] = s
    return out


def _parse_llm_findings(text: str) -> list[dict]:
    """Parse LLM response into list of finding dicts. Expects JSON array of { field, value, issue, suggestion }."""
    findings = []
    text = (text or "").strip()
    # Try to extract JSON array (allow markdown code block)
    if "```" in text:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if m:
            text = m.group(1).strip()
    # Find first '[' and last ']'
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        try:
            arr = json.loads(text[start : end + 1])
            for item in arr:
                if isinstance(item, dict) and item.get("field") and item.get("issue"):
                    findings.append({
                        "type": "content_placeholder",
                        "field": item.get("field", ""),
                        "value": item.get("value", ""),
                        "message": item.get("issue", ""),
                        "severity": "warning",
                    })
        except json.JSONDecodeError:
            pass
    return findings


# Phrases that are always considered placeholder/nonsense (rules-based fallback)
_PLACEHOLDER_PHRASES = re.compile(
    r"^(i\s*don'?t\s*know|idk|none|n/?a|n\.?a\.?|good|fine|same|standard|tbd|to\s*be\s*determined|no\s*idea|not\s*sure|asap|minimal|various|lots|few|many|architecture\s*is\s*good|data\s*is\s*good|no\s*dr|never)$",
    re.IGNORECASE,
)
_MAX_PLACEHOLDER_LEN = 50  # Very short free-text likely placeholder


def _rules_based_content_findings(profile: ApplicationProfile) -> list[dict]:
    """Quick rules-based pass: flag obvious placeholder phrases across text fields."""
    findings = []
    raw = profile.model_dump()
    for key, label in FIELD_LABELS.items():
        if key not in raw:
            continue
        val = raw[key]
        if isinstance(val, list):
            val = ", ".join(str(x).strip() for x in val if x).strip()
        else:
            val = (val or "").strip()
        if not val or len(val) > _MAX_PLACEHOLDER_LEN:
            continue
        if _PLACEHOLDER_PHRASES.match(val):
            findings.append({
                "type": "content_placeholder",
                "field": label,
                "value": val,
                "message": f"Value looks like a placeholder or non-informative. Please provide a concrete answer.",
                "severity": "warning",
            })
    return findings


def validate_profile_content_with_llm(profile: ApplicationProfile) -> list[dict]:
    """
    Validate all filled profile fields against expected value guidelines.
    Uses rules-based check first, then LLM for deeper validation.
    Returns list of findings: { type, field, value, message, severity }.
    Field is the human-readable label (e.g. "Current architecture description").
    """
    findings = _rules_based_content_findings(profile)

    use_llm = os.getenv("PROFILE_CONTENT_VALIDATION_USE_LLM", "true").strip().lower() in ("true", "1", "yes")
    if not use_llm:
        return findings

    kv = profile_to_kv_map(profile)
    if not kv:
        return findings

    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from backend.services.diagnostics.recorder import invoke_llm
        from backend.services.llm_provider import get_llm

        llm = get_llm(temperature=0, max_tokens=1500)

        kv_text = "\n".join(f"  {k}: {v}" for k, v in kv.items())

        system = """You are validating an application profile for a cloud migration assessment. We collected the following key-value pairs from the user. Your job is to identify fields where the VALUE is placeholder, nonsense, or clearly does not match what we expect (e.g. "I don't know", "none", "good", "architecture is good", "N/A", "TBD" without detail, vague single words).

Reply with a JSON array of objects. Each object has: "field" (the exact field label as shown below), "value" (the current value), "issue" (short description of the problem), "suggestion" (optional, what to enter instead). Only include fields that need correction. If everything looks substantive, reply with an empty array [].

Example: [{"field": "Current architecture description", "value": "architecture is good", "issue": "Placeholder; does not describe components.", "suggestion": "Describe tiers e.g. web, app, database"}]
"""

        user = f"""Expected value guidelines:
{EXPECTED_VALUE_GUIDELINES}

Collected profile (key-value map):
{kv_text}

Reply with ONLY a JSON array of findings (or [] if no issues). Use the exact field names from the "Collected profile" list above for "field"."""

        resp = invoke_llm(llm, [
            SystemMessage(content=system),
            HumanMessage(content=user),
        ], "profile_content_validation", assessment_id=None)
        content = (resp.content or "").strip()
        llm_findings = _parse_llm_findings(content)
        # Dedupe by field (rules may have already flagged; prefer LLM message if both)
        seen_fields = {f["field"] for f in findings}
        for f in llm_findings:
            if f.get("field") and f["field"] not in seen_fields:
                findings.append(f)
                seen_fields.add(f["field"])
        return findings
    except Exception:
        return findings
