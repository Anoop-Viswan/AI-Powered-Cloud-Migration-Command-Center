"""Assessment data models – expanded for migration project pillars."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApplicationProfile(BaseModel):
    """
    Structured application profile for migration assessment.
    Organized around architecture pillars; all fields optional except application_name.
    """

    model_config = ConfigDict(extra="ignore")  # Ignore unknown fields for backward compat

    # ─── 1. General Overview ─────────────────────────────────────────────────
    application_name: str = Field(..., min_length=1, description="Application name")
    business_purpose: str = Field(default="", description="What business it does")
    description: str = Field(default="", description="Brief description")
    user_count_estimate: str = Field(default="", description="e.g. 1000, 10K-50K")
    priority: Literal["critical", "high", "medium", "low"] = Field(
        default="medium", description="Application priority"
    )
    rto: str = Field(default="", description="Recovery Time Objective")
    rpo: str = Field(default="", description="Recovery Point Objective")
    compliance_requirements: list[str] = Field(default_factory=list, description="e.g. PCI, HIPAA")
    known_risks: str = Field(default="", description="Known risks")
    constraints: str = Field(default="", description="Constraints")
    additional_notes: str = Field(default="", description="Additional notes")

    # ─── 2. Architecture ────────────────────────────────────────────────────
    tech_stack: list[str] = Field(default_factory=list, description="e.g. Java 11, Spring Boot")
    current_environment: Literal["on-prem", "vm", "cloud-legacy", "other"] = Field(
        default="on-prem"
    )
    target_environment: Literal["azure", "aws", "gcp", "other"] = Field(default="azure")
    current_architecture_description: str = Field(default="", description="Current state description")
    current_architecture_diagram_path: str | None = Field(
        default=None, description="Path to uploaded current-state diagram (PNG)"
    )
    future_architecture_description: str = Field(default="", description="Future state description")
    future_architecture_diagram_path: str | None = Field(
        default=None, description="Path to uploaded future-state diagram (PNG)"
    )

    # ─── 3. Data Management ───────────────────────────────────────────────────
    contains_database_migration: str = Field(
        default="",
        description="Does this application contain database migration? yes | no",
    )
    total_data_volume: str = Field(default="", description="e.g. 500 GB, 2 TB")
    database_types: list[str] = Field(
        default_factory=list, description="e.g. Oracle, SQL Server, PostgreSQL"
    )
    current_databases_description: str = Field(default="", description="Current DBs and sizes")
    target_databases_description: str = Field(default="", description="Target DBs if known")
    data_retention_requirements: str = Field(default="", description="Retention policy")
    data_migration_notes: str = Field(default="", description="Data migration considerations")
    # Ingestion, ingress, egress, ETLs (critical for migration assessments)
    data_ingestion: str = Field(
        default="",
        description="How data enters: batch, real-time, streaming, APIs, file drops, etc.",
    )
    data_ingress: str = Field(
        default="",
        description="Ingress sources, formats, volume – e.g. API from OrderSys, Kafka 10K msg/day",
    )
    data_egress: str = Field(
        default="",
        description="Egress destinations, formats – e.g. data warehouse, reports, 3rd party APIs",
    )
    etl_pipelines: str = Field(
        default="",
        description="ETLs if any: tools, schedules, pipelines – e.g. SSIS daily, Informatica hourly",
    )

    # ─── 4. Business Continuity & DR ──────────────────────────────────────────
    current_dr_strategy: str = Field(default="", description="Current DR approach")
    backup_frequency: str = Field(default="", description="e.g. daily, weekly")
    failover_approach: str = Field(default="", description="Failover strategy")
    dr_testing_frequency: str = Field(default="", description="DR test cadence")
    bc_dr_notes: str = Field(default="", description="BC/DR additional notes")

    # ─── 5. Cost ──────────────────────────────────────────────────────────────
    current_annual_cost: str = Field(default="", description="Current infra/ops cost")
    migration_budget: str = Field(default="", description="Budget for migration")
    cost_constraints: str = Field(default="", description="Cost limitations")
    licensing_considerations: str = Field(default="", description="Licensing notes")

    # ─── 6. Security ──────────────────────────────────────────────────────────
    authentication_type: str = Field(
        default="", description="e.g. SAML, OAuth, AD, LDAP"
    )
    encryption_at_rest: str = Field(default="", description="At-rest encryption")
    encryption_in_transit: str = Field(default="", description="In-transit encryption")
    pii_handling: str = Field(default="", description="PII handling approach")
    compliance_frameworks: list[str] = Field(
        default_factory=list, description="e.g. SOC2, GDPR, HIPAA"
    )

    # ─── 7. Project & Timeline ──────────────────────────────────────────────────
    project_manager: str = Field(default="", description="PM or owner")
    timeline_expectation: str = Field(default="", description="Expected timeline")
    team_size: str = Field(default="", description="Team size or range")
    dependencies: list[str] = Field(default_factory=list, description="Other apps, DBs")
    integrations: list[str] = Field(default_factory=list, description="Integrations")
    preferred_go_live: str = Field(default="", description="Preferred go-live window")

    def to_context_text(self) -> str:
        """Build markdown summary for LLM context (research/summarizer)."""
        def _row(label: str, val: str | list | None) -> str:
            if isinstance(val, list):
                val = ", ".join(val) if val else ""
            v = (val or "").strip()
            return f"- **{label}:** {v or 'Not specified'}"

        lines = [
            "## 1. General Overview",
            _row("Application", self.application_name),
            _row("Business purpose", self.business_purpose or self.description),
            _row("Users (est.)", self.user_count_estimate),
            _row("Priority", self.priority),
            _row("RTO", self.rto),
            _row("RPO", self.rpo),
            _row("Compliance", self.compliance_requirements),
            _row("Risks", self.known_risks),
            _row("Constraints", self.constraints),
            "",
            "## 2. Architecture",
            _row("Tech stack", self.tech_stack),
            _row("Current env", self.current_environment),
            _row("Target env", self.target_environment),
            _row("Current architecture", self.current_architecture_description),
            _row("Future architecture", self.future_architecture_description),
            "",
            "## 3. Data Management",
            _row("Contains database migration", self.contains_database_migration),
            _row("Data volume", self.total_data_volume),
            _row("Database types", self.database_types),
            _row("Current DBs", self.current_databases_description),
            _row("Target DBs", self.target_databases_description),
            _row("Data retention", self.data_retention_requirements),
            _row("Data ingestion", self.data_ingestion),
            _row("Ingress", self.data_ingress),
            _row("Egress", self.data_egress),
            _row("ETL pipelines", self.etl_pipelines),
            "",
            "## 4. Business Continuity & DR",
            _row("DR strategy", self.current_dr_strategy),
            _row("Backup frequency", self.backup_frequency),
            _row("Failover", self.failover_approach),
            "",
            "## 5. Cost",
            _row("Current cost", self.current_annual_cost),
            _row("Migration budget", self.migration_budget),
            "",
            "## 6. Security",
            _row("Auth", self.authentication_type),
            _row("Encryption at rest", self.encryption_at_rest),
            _row("Encryption in transit", self.encryption_in_transit),
            _row("Compliance", self.compliance_frameworks),
            "",
            "## 7. Project & Timeline",
            _row("PM", self.project_manager),
            _row("Timeline", self.timeline_expectation),
            _row("Team size", self.team_size),
            _row("Dependencies", self.dependencies),
            _row("Integrations", self.integrations),
            _row("Go-live", self.preferred_go_live),
            _row("Notes", self.additional_notes),
        ]
        return "\n".join(lines)


class AssessmentState(BaseModel):
    """Full assessment state (profile + approach + report + optional quality check)."""

    id: str
    profile: ApplicationProfile | None = None
    approach_document: str | None = None
    report: str | None = None
    status: Literal["draft", "submitted", "researching", "research_done", "summarizing", "done", "error"] = (
        "draft"
    )
    error_message: str | None = None
    quality_check: dict | None = None  # Scores, reasons, suggestions (see quality_check.py)
    research_details: dict | None = None  # kb_hits + official_docs for transparency (what was retrieved)
