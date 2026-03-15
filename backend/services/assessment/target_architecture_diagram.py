"""
Target state architecture diagram (Mermaid) aligned to Microsoft and cloud reference architectures.

References:
- Azure N-tier: https://learn.microsoft.com/en-us/azure/architecture/reference-architectures/n-tier/multi-region-sql-server
- Secure N-tier App Service: https://learn.microsoft.com/en-us/azure/app-service/tutorial-secure-ntier-app
- Flow: Internet → Edge (Front Door / WAF) → VNet → App tier → Data tier; Identity (Entra ID) and Key Vault for secrets.
"""

from backend.services.assessment.models import ApplicationProfile


def _pick_data_services(profile: ApplicationProfile) -> tuple[str, str | None]:
    """
    Return (primary_db_label, storage_label) for the target cloud.
    Primary DB is the main relational/DB service; storage is blob/object storage.
    """
    target = (profile.target_environment or "azure").lower()
    db_types = [d.lower() for d in (profile.database_types or [])]
    has_db = (profile.contains_database_migration or "").strip().lower() in ("yes", "true", "1")

    if target == "azure":
        if has_db and any("sql" in d or "mssql" in d or "server" in d for d in db_types):
            primary_db = "Azure SQL Database"
        elif has_db and any("postgres" in d for d in db_types):
            primary_db = "Azure Database for PostgreSQL"
        elif has_db and any("mysql" in d for d in db_types):
            primary_db = "Azure Database for MySQL"
        elif has_db and any("cosmos" in d for d in db_types):
            primary_db = "Azure Cosmos DB"
        elif has_db:
            primary_db = "Azure SQL Database"
        else:
            primary_db = "Azure SQL Database"  # default for migration assessment
        return primary_db, "Azure Storage"
    if target == "aws":
        primary_db = "Amazon RDS" if has_db else "Amazon RDS"
        return primary_db, "Amazon S3"
    if target == "gcp":
        primary_db = "Cloud SQL" if has_db else "Cloud SQL"
        return primary_db, "Cloud Storage"
    return "Azure SQL Database", "Azure Storage"


def build_azure_target_mermaid(profile: ApplicationProfile) -> str:
    """
    Build a Mermaid flowchart for Azure target state following Microsoft reference architecture:
    - Edge: Azure Front Door (WAF) for HTTPS
    - VNet with Web/App subnet and Data subnet
    - App Service (or App Service Plan) in app tier
    - Data tier: Azure SQL + Storage with private endpoints
    - Identity: Microsoft Entra ID (Azure AD); Key Vault for secrets
    - Flows: Users → Front Door → App; Users -.-> Entra ID; App → SQL/Storage; App -.-> Key Vault
    """
    app_name = (profile.application_name or "Application").replace('"', "'")[:40]
    primary_db, storage_label = _pick_data_services(profile)

    # Microsoft reference: each tier in its subnet; private endpoints for data; identity separate
    # Use <br/> for line breaks in node labels (Mermaid-compatible)
    return f'''flowchart TB
  subgraph Internet["Internet"]
    Users["Users / Clients"]
  end

  subgraph Edge["Edge - Public"]
    AFD["Azure Front Door<br/>(Web Application Firewall)"]
  end

  subgraph VNet["Azure Virtual Network"]
    subgraph AppTier["App Tier Subnet"]
      App["Azure App Service<br/>{app_name}"]
    end
    subgraph DataTier["Data Tier Subnet"]
      SQL["{primary_db}"]
      Storage["{storage_label}"]
    end
  end

  subgraph Identity["Identity & Security"]
    AAD["Microsoft Entra ID<br/>(Azure AD)"]
    KV["Azure Key Vault"]
  end

  Users -->|"HTTPS"| AFD
  AFD -->|"VNet Integration"| App
  App -->|"Private Endpoint"| SQL
  App -->|"Private Endpoint"| Storage
  Users -.->|"Authenticate"| AAD
  App -.->|"Managed Identity"| AAD
  App -.->|"Secrets"| KV
'''


def build_aws_target_mermaid(profile: ApplicationProfile) -> str:
    """
    AWS reference style: Internet → WAF/CloudFront → VPC → App (ECS/App Runner) → RDS/S3; IAM + Secrets Manager.
    """
    app_name = (profile.application_name or "Application").replace('"', "'")[:40]
    primary_db, storage_label = _pick_data_services(profile)

    return f'''flowchart TB
  subgraph Internet["Internet"]
    Users["Users / Clients"]
  end

  subgraph Edge["Edge"]
    CF["Amazon CloudFront<br/>(WAF)"]
  end

  subgraph VPC["Amazon VPC"]
    subgraph AppSubnet["Application Subnets"]
      App["AWS App Runner / ECS<br/>{app_name}"]
    end
    subgraph DataSubnet["Data Subnets"]
      RDS["{primary_db}"]
      S3["{storage_label}"]
    end
  end

  subgraph Security["Security"]
    IAM["IAM"]
    SM["Secrets Manager"]
  end

  Users -->|"HTTPS"| CF
  CF -->|"VPC"| App
  App -->|"Private"| RDS
  App -->|"Private"| S3
  Users -.->|"Auth"| IAM
  App -.->|"IAM Role"| IAM
  App -.->|"Secrets"| SM
'''


def build_gcp_target_mermaid(profile: ApplicationProfile) -> str:
    """
    GCP reference: Internet → Load Balancer / Cloud Armor → VPC → Cloud Run / GKE → Cloud SQL / GCS; IAP + Secret Manager.
    """
    app_name = (profile.application_name or "Application").replace('"', "'")[:40]
    primary_db, storage_label = _pick_data_services(profile)

    return f'''flowchart TB
  subgraph Internet["Internet"]
    Users["Users / Clients"]
  end

  subgraph Edge["Edge"]
    LB["Cloud Load Balancer<br/>(Cloud Armor)"]
  end

  subgraph VPC["Google Cloud VPC"]
    subgraph AppSubnet["Application"]
      App["Cloud Run / GKE<br/>{app_name}"]
    end
    subgraph DataSubnet["Data"]
      SQL["{primary_db}"]
      GCS["{storage_label}"]
    end
  end

  subgraph Security["Identity & Security"]
    IAP["Identity-Aware Proxy"]
    SM["Secret Manager"]
  end

  Users -->|"HTTPS"| LB
  LB -->|"VPC"| App
  App -->|"Private"| SQL
  App -->|"Private"| GCS
  Users -.->|"Auth"| IAP
  App -.->|"Identity"| IAP
  App -.->|"Secrets"| SM
'''


def build_target_state_mermaid(profile: ApplicationProfile) -> str:
    """
    Return Mermaid diagram for target state based on profile.target_environment.
    Follows Microsoft (Azure) and common reference architectures for AWS/GCP.
    """
    target = (profile.target_environment or "azure").lower()
    if target == "aws":
        return build_aws_target_mermaid(profile).strip()
    if target == "gcp":
        return build_gcp_target_mermaid(profile).strip()
    return build_azure_target_mermaid(profile).strip()
