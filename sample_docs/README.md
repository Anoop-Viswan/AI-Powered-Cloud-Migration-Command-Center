# Sample documents for seeding the Knowledge Base

- **SuperNova_Assessment_Report.docx** — Fictitious 3–4 page assessment report for the "SuperNova" migration (on-prem to Azure). Includes Overview, Application Profile, Methodology, Architecture & Platform, Infrastructure, Security and Compliance, Data Management, and TCO Assessment & Management. Uses Azure technologies (AKS, Azure SQL, Blob Storage, Entra ID, etc.).

To use these in your KB, copy them into your project directory (e.g. the path set in `PINECONE_PROJECT_DIR`) and run:

```bash
python semantic_search.py --seed
```

Or place them in an application folder (e.g. `SuperNova/SuperNova_Assessment_Report.docx`) and add an entry for `SuperNova` in `manifest.json` if you use the manifest.

To regenerate the SuperNova report:

```bash
python scripts/generate_supernova_assessment.py
```
