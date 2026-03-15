# Profile Validation

Prevents hallucination by ensuring required fields are present before **submitting** a migration request. Validation runs per section when moving to the next section and again on **"Submit for assessment"**. Research and report generation are **Admin-only**; Application Users only submit validated profile data. See [Migration Request Flow](./MIGRATION_REQUEST_FLOW.md).

## Rules

### 1. Overview (mandatory)

- **Application name** – Required.
- **Business purpose** – Required (at least a brief description, min 3 characters).
- **User count (estimate)** – Required (e.g. 1000, 10K-50K).
- **Priority** – Required (Critical / High / Medium / Low).
- **RTO** – Required (e.g. 1 hour, 4 hours). Hints: critical → typical 1 hour; high → 4 hours.
- **RPO** – Required (e.g. 1 hour, 15 min).

### 2. Architecture (mandatory)

- **Tech stack** – Required (at least one technology).
- **Current environment** – Required (On-prem / VM / Cloud / Other).
- **Target environment** – Required (Azure / AWS / GCP / Other).
- **Current state** – Either **architecture description** or **uploaded diagram** (one required). Target/future state is encouraged; hint shown if missing.

### 3. Data (mandatory + conditional)

- **Contains database migration?** – Required (Yes/No).
- If **Yes**: **Total data volume**, **Database types**, **Current databases description** are required.
- Cost-related fields remain optional.

### 4. BC & DR (all mandatory)

- **Current DR strategy**, **Backup frequency**, **Failover approach**, **DR testing frequency** – All required.

### 5. Cost

- All optional.

### 6. Security (mandatory)

- **Authentication type** – Required (e.g. SAML, OAuth, AD, LDAP).
- **Encryption at rest** – Required (e.g. AES-256, TDE).
- **Encryption in transit** – Required (e.g. TLS 1.2).

### Content validation (all screens / fields)

After mandatory and sanity checks, the profile is validated for **placeholder or nonsense values** across every field from every screen:

- **Internal map:** All non-empty profile fields are built into a key-value map (key = human-readable field label, value = what the user entered).
- **Expected value guidelines:** Each field/section has defined expectations (e.g. "Current architecture description: describe components, not 'good' or 'I don't know'").
- **Rules-based:** Obvious placeholders are always flagged: e.g. "I don't know", "none", "good", "architecture is good", "N/A", "TBD", "no idea", "standard", "various".
- **LLM-based (optional):** If `PROFILE_CONTENT_VALIDATION_USE_LLM=true` (default), the full map + guidelines are sent to the LLM, which returns any additional fields where the value deviates or looks non-informative.
- **Findings** are returned in the same `findings` array (type `content_placeholder`) and shown in the pre-research review screen so the user can confirm or edit.

See `backend/services/assessment/profile_content_validator.py` for the field map and expected value guidelines.

### Sanity & logical checks (warnings / data quality)

| Field | Check | Threshold |
|-------|-------|-----------|
| Data volume | Parsed as TB (e.g. "500 GB", "2 TB") | > 100 PB → warning |
| User count | Parsed (e.g. "10K", "1M") | > 10 billion → warning |
| Current cost | Parsed as USD | > $10B → warning |
| Migration budget | Parsed as USD | > $10B → warning |

- **RTO/RPO**: Should contain a number (e.g. "1 hour"); placeholder values (n/a, tbd, x) trigger a warning.
- **User count**: Placeholder values trigger a warning.

Warnings do not block research; they prompt the user to verify.

### Optional LLM Check

Set `PROFILE_VALIDATION_USE_LLM=yes` in `.env` to add an LLM-based completeness check. The LLM evaluates whether the profile has enough context for meaningful recommendations. Adds one extra API call before research.

## API

- `GET /api/assessment/{id}/validate` – Returns `{ valid, errors, warnings, suggestions }`
- Research and Summarize endpoints call validation internally; invalid profiles return 400 with error detail.

## Implementation

- `backend/services/assessment/profile_validator.py` – Validation logic
- Frontend: Research step fetches validation, shows errors, disables "Run research" until valid
