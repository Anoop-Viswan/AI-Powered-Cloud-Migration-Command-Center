"""
Profile validation: mandatory fields, sanity checks, optional LLM completeness.

Prevents hallucination by ensuring enough context before Research/Summarize.
"""

import os
import re
from dataclasses import dataclass, field

from backend.services.assessment.models import ApplicationProfile


@dataclass
class ValidationResult:
    """Result of profile validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)  # For API: list of Finding-like dicts


# ─── Required fields and validation ───────────────────────────────────────────

MIN_BUSINESS_PURPOSE_LEN = 3
MIN_TECH_STACK_ITEMS = 1


def _has_substance(val: str | list, min_len: int = MIN_BUSINESS_PURPOSE_LEN) -> bool:
    """Check if field has meaningful content (not empty, not placeholder)."""
    if isinstance(val, list):
        items = [str(x).strip() for x in val if x]
        return len(items) >= MIN_TECH_STACK_ITEMS
    s = (val or "").strip()
    return len(s) >= min_len and s.lower() not in ("n/a", "tbd", "none", "-", "na", "n/a")


def _is_yes_no(s: str) -> bool:
    """Check if value is a clear yes/no."""
    v = (s or "").strip().lower()
    return v in ("yes", "no", "y", "n")


# ─── Sanity checks ───────────────────────────────────────────────────────────

# Data volume: parse "500 GB", "2 TB", "1000 PB" -> TB equivalent
_DATA_VOLUME_PATTERN = re.compile(
    r"([\d.,]+)\s*(bytes?|b|kb|mb|gb|tb|pb)\b",
    re.IGNORECASE,
)
_MAX_DATA_TB = 100_000  # 100 PB


def _parse_data_volume_tb(s: str) -> float | None:
    """Parse data volume string to TB. Returns None if unparseable."""
    if not (s or "").strip():
        return None
    m = _DATA_VOLUME_PATTERN.search(s)
    if not m:
        return None
    try:
        num = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    unit = (m.group(2) or "").strip().lower()
    multipliers = {
        "b": 1 / (1024**4),
        "byte": 1 / (1024**4),
        "bytes": 1 / (1024**4),
        "kb": 1 / (1024**3),
        "mb": 1 / (1024**2),
        "gb": 1 / 1024,
        "tb": 1.0,
        "pb": 1024.0,
    }
    mult = multipliers.get(unit, 1.0)
    return num * mult


def _parse_user_count(s: str) -> int | None:
    """Extract numeric user count. Handles 10K, 50K-100K, 1M."""
    if not (s or "").strip():
        return None
    s = s.strip().replace(",", "").upper()
    m = re.search(r"([\d.]+)\s*([KMB])?", s)
    if not m:
        try:
            return int(float(s))
        except ValueError:
            return None
    try:
        num = float(m.group(1))
    except ValueError:
        return None
    suffix = (m.group(2) or "").strip()
    if suffix == "K":
        num *= 1_000
    elif suffix == "M":
        num *= 1_000_000
    elif suffix == "B":
        num *= 1_000_000_000
    return int(num)


_MAX_USER_COUNT = 10_000_000_000  # 10 billion


def _parse_currency_usd(s: str) -> float | None:
    """Extract dollar amount. Handles $50K, $1.2M, etc."""
    if not (s or "").strip():
        return None
    s = s.strip().replace(",", "").upper()
    m = re.search(r"\$?\s*([\d.]+)\s*([KMB])?", s)
    if not m:
        try:
            return float(re.search(r"[\d.]+", s).group())
        except (ValueError, AttributeError):
            return None
    try:
        num = float(m.group(1))
    except ValueError:
        return None
    suffix = (m.group(2) or "").strip()
    if suffix == "K":
        num *= 1_000
    elif suffix == "M":
        num *= 1_000_000
    elif suffix == "B":
        num *= 1_000_000_000
    return num


_MAX_COST_USD = 10_000_000_000  # $10B

# RTO/RPO: parse to hours for reasonableness checks
_RTO_RPO_PATTERN = re.compile(
    r"([\d.,]+)\s*(hour?s?|hr?s?|min(?:ute)?s?|day?s?|week?s?|month?s?|year?s?)\b",
    re.IGNORECASE,
)


def _parse_rto_rpo_hours(s: str) -> float | None:
    """Parse RTO/RPO string to hours. e.g. '4 hours' -> 4, '1 day' -> 24, '30 min' -> 0.5."""
    if not (s or "").strip():
        return None
    m = _RTO_RPO_PATTERN.search(s)
    if not m:
        return None
    try:
        num = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    unit = (m.group(2) or "").strip().lower()
    if unit.startswith("hour") or unit.startswith("hr"):
        return num
    if "min" in unit:
        return num / 60.0
    if unit.startswith("day"):
        return num * 24
    if unit.startswith("week"):
        return num * 24 * 7
    if unit.startswith("month"):
        return num * 24 * 30
    if unit.startswith("year"):
        return num * 24 * 365
    return None


# Reasonableness thresholds
_RTO_HOURS_WARN = 168  # 1 week
_RTO_HOURS_CONFIRM = 8760  # 1 year
_DATA_TB_WARN = 1000  # 1 PB
_DATA_TB_CONFIRM = 100_000  # 100 PB (existing max)


def _finding(typ: str, field: str, value: str, message: str, severity: str) -> dict:
    return {"type": typ, "field": field, "value": value, "message": message, "severity": severity}


# ─── LLM completeness check ─────────────────────────────────────────────────

def _llm_completeness_check(profile: ApplicationProfile) -> tuple[bool, list[str]]:
    """
    Ask LLM: is there enough context for meaningful recommendations?
    Returns (ready: bool, suggestions: list).
    """
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        from backend.services.llm_provider import get_llm

        llm = get_llm(temperature=0, max_tokens=300)
        context = profile.to_context_text()

        system = """You are a migration assessment validator. Given an application profile, decide if there is ENOUGH context to produce meaningful migration recommendations.

Rules:
- Application name alone is NOT enough.
- Need at least: tech stack OR architecture description OR data/database info OR business purpose.
- If most fields say "Not specified" or are empty, reply NOT_READY.
- If there is substantive context (technologies, data, architecture, purpose), reply READY.

Reply in exactly this format:
STATUS: READY or NOT_READY
SUGGESTIONS: (if NOT_READY, list 1-3 critical missing fields in one line, else "None")"""

        resp = llm.invoke([
            SystemMessage(content=system),
            HumanMessage(content=f"Profile:\n{context}"),
        ])
        text = (resp.content or "").strip().upper()
        ready = "STATUS: NOT_READY" not in text and ("STATUS: READY" in text or "READY" in text)
        suggestions = []

        if "SUGGESTIONS:" in text:
            sugg_part = text.split("SUGGESTIONS:")[-1].strip()
            if sugg_part and "NONE" not in sugg_part[:10]:
                for line in sugg_part.replace(",", "\n").split("\n")[:3]:
                    line = line.strip().strip("-").strip()
                    if line and len(line) > 3:
                        suggestions.append(line)

        return ready, suggestions
    except Exception:
        return True, []  # If LLM fails, allow through (rule-based already passed)


# ─── Main validation ──────────────────────────────────────────────────────────

def validate_profile_for_research(profile: ApplicationProfile) -> ValidationResult:
    """
    Validate profile before Research. All mandatory fields per section; sanity, junk, and reasonableness checks.
    """
    errors: list[str] = []
    warnings: list[str] = []
    suggestions: list[str] = []
    findings: list[dict] = []

    # ─── 1. Overview ────────────────────────────────────────────────────────
    if not (profile.application_name or "").strip():
        errors.append("Application name is required.")
    if not _has_substance(profile.business_purpose):
        errors.append("Business purpose is required (at least a brief description).")
    if not (profile.user_count_estimate or "").strip():
        errors.append("User count (estimate) is required.")
    if not (profile.priority or "").strip():
        errors.append("Priority is required.")
    if not (profile.rto or "").strip():
        errors.append("RTO (Recovery Time Objective) is required.")
    if not (profile.rpo or "").strip():
        errors.append("RPO (Recovery Point Objective) is required.")

    # ─── 2. Architecture ────────────────────────────────────────────────────
    if not _has_substance(profile.tech_stack):
        errors.append("Tech stack is required (at least one technology).")
    if not (profile.current_environment or "").strip():
        errors.append("Current environment is required.")
    if not (profile.target_environment or "").strip():
        errors.append("Target environment is required.")
    has_current_desc = _has_substance(profile.current_architecture_description)
    has_current_diagram = bool(profile.current_architecture_diagram_path and profile.current_architecture_diagram_path.strip())
    if not has_current_desc and not has_current_diagram:
        errors.append("Current state: provide either architecture description or upload a diagram.")

    # ─── 3. Data ────────────────────────────────────────────────────────────
    db_mig = (profile.contains_database_migration or "").strip().lower()
    if not _is_yes_no(profile.contains_database_migration):
        errors.append("Data: answer whether this application contains database migration (Yes/No).")
    elif db_mig in ("yes", "y"):
        if not _has_substance(profile.total_data_volume):
            errors.append("Data: total data volume is required when database migration is Yes.")
        if not _has_substance(profile.database_types):
            errors.append("Data: database types are required when database migration is Yes.")
        if not _has_substance(profile.current_databases_description):
            errors.append("Data: current databases description is required when database migration is Yes.")

    # ─── 4. BC & DR ─────────────────────────────────────────────────────────
    if not _has_substance(profile.current_dr_strategy):
        errors.append("BC & DR: current DR strategy is required.")
    if not (profile.backup_frequency or "").strip():
        errors.append("BC & DR: backup frequency is required.")
    if not (profile.failover_approach or "").strip():
        errors.append("BC & DR: failover approach is required.")
    if not (profile.dr_testing_frequency or "").strip():
        errors.append("BC & DR: DR testing frequency is required.")

    # ─── 5. Cost ────────────────────────────────────────────────────────────
    # Optional per user request

    # ─── 6. Security ────────────────────────────────────────────────────────
    if not (profile.authentication_type or "").strip():
        errors.append("Security: authentication type is required.")
    if not (profile.encryption_at_rest or "").strip():
        errors.append("Security: encryption at rest is required.")
    if not (profile.encryption_in_transit or "").strip():
        errors.append("Security: encryption in transit is required.")

    if errors:
        return ValidationResult(valid=False, errors=errors, warnings=warnings, suggestions=suggestions, findings=[])

    # ─── Sanity & junk checks ─────────────────────────────────────────────────
    def _looks_like_junk(s: str, min_len: int = 2) -> bool:
        if not (s or "").strip():
            return True
        s = (s or "").strip()
        if len(s) < min_len:
            return True
        low = s.lower()
        if low in ("n/a", "na", "tbd", "none", "-", "x", "xx", "asdf", "test", "todo"):
            return True
        if re.match(r"^[x.\-_\s]+$", low):
            return True
        return False

    if (profile.rto or "").strip() and _looks_like_junk(profile.rto, 2):
        warnings.append("RTO looks like a placeholder. Use a real value (e.g. 1 hour, 4 hours).")
    elif (profile.rto or "").strip() and not re.search(r"\d", profile.rto):
        warnings.append("RTO should usually include a number (e.g. 1 hour, 4 hours).")
    if (profile.rpo or "").strip() and _looks_like_junk(profile.rpo, 2):
        warnings.append("RPO looks like a placeholder. Use a real value (e.g. 1 hour, 15 min).")
    elif (profile.rpo or "").strip() and not re.search(r"\d", profile.rpo):
        warnings.append("RPO should usually include a number (e.g. 1 hour, 15 min).")
    if (profile.user_count_estimate or "").strip() and _looks_like_junk(profile.user_count_estimate, 1):
        warnings.append("User count looks like a placeholder. Use a number or range (e.g. 1000, 10K-50K).")

    # ─── Reasonableness findings (flag for user confirmation) ───────────────────
    rto_h = _parse_rto_rpo_hours(profile.rto)
    if rto_h is not None:
        if rto_h > _RTO_HOURS_CONFIRM:
            findings.append(
                _finding(
                    "rto_very_high",
                    "rto",
                    profile.rto,
                    f"RTO ({profile.rto}) is over 1 year. Did you mean 10 hours or 1 day? Please confirm.",
                    "confirm",
                )
            )
        elif rto_h > _RTO_HOURS_WARN:
            findings.append(
                _finding(
                    "rto_high",
                    "rto",
                    profile.rto,
                    f"RTO ({profile.rto}) is over 1 week. Please confirm this is correct.",
                    "warning",
                )
            )

    rpo_h = _parse_rto_rpo_hours(profile.rpo)
    if rpo_h is not None:
        if rpo_h > _RTO_HOURS_CONFIRM:
            findings.append(
                _finding(
                    "rpo_very_high",
                    "rpo",
                    profile.rpo,
                    f"RPO ({profile.rpo}) is over 1 year. Did you mean 1 hour or 15 min? Please confirm.",
                    "confirm",
                )
            )
        elif rpo_h > _RTO_HOURS_WARN:
            findings.append(
                _finding(
                    "rpo_high",
                    "rpo",
                    profile.rpo,
                    f"RPO ({profile.rpo}) is over 1 week. Please confirm this is correct.",
                    "warning",
                )
            )

    vol_tb = _parse_data_volume_tb(profile.total_data_volume)
    if vol_tb is not None:
        if vol_tb > _MAX_DATA_TB:
            warnings.append(
                f"Data volume ({profile.total_data_volume}) seems unusually large (>100 PB). Please verify."
            )
            findings.append(
                _finding(
                    "data_volume_very_high",
                    "total_data_volume",
                    profile.total_data_volume,
                    f"Data volume ({profile.total_data_volume}) is over 100 PB. Please verify.",
                    "confirm",
                )
            )
        elif vol_tb > _DATA_TB_WARN:
            findings.append(
                _finding(
                    "data_volume_high",
                    "total_data_volume",
                    profile.total_data_volume,
                    f"Data volume ({profile.total_data_volume}) is over 1 PB. Please confirm this is correct.",
                    "warning",
                )
            )

    user_count = _parse_user_count(profile.user_count_estimate)
    if user_count is not None and user_count > _MAX_USER_COUNT:
        warnings.append(
            f"User count ({profile.user_count_estimate}) seems unusually high (>10B). Please verify."
        )
        findings.append(
            _finding(
                "user_count_very_high",
                "user_count_estimate",
                profile.user_count_estimate,
                f"User count ({profile.user_count_estimate}) is over 10 billion. Please verify.",
                "confirm",
            )
        )

    cost = _parse_currency_usd(profile.current_annual_cost)
    if cost is not None and cost > _MAX_COST_USD:
        warnings.append(
            f"Current cost ({profile.current_annual_cost}) seems unusually high (>$10B). Please verify."
        )

    budget = _parse_currency_usd(profile.migration_budget)
    if budget is not None and budget > _MAX_COST_USD:
        warnings.append(
            f"Migration budget ({profile.migration_budget}) seems unusually high (>$10B). Please verify."
        )

    # 4. Optional LLM completeness check
    use_llm = os.getenv("PROFILE_VALIDATION_USE_LLM", "").strip().lower() in ("yes", "1", "true")
    if use_llm:
        ready, llm_suggestions = _llm_completeness_check(profile)
        if not ready and llm_suggestions:
            errors.append("Profile lacks sufficient context for meaningful recommendations.")
            suggestions.extend(llm_suggestions)
            return ValidationResult(valid=False, errors=errors, warnings=warnings, suggestions=suggestions, findings=findings)

    # 5. LLM content validation: flag placeholder/nonsense values across all screens/fields
    try:
        from backend.services.assessment.profile_content_validator import validate_profile_content_with_llm
        content_findings = validate_profile_content_with_llm(profile)
        findings.extend(content_findings)
    except Exception:
        pass

    return ValidationResult(valid=True, errors=[], warnings=warnings, suggestions=suggestions, findings=findings)
