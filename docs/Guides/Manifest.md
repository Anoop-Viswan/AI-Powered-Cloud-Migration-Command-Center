# Application manifest

The indexer derives **application name** from your folder structure and can attach extra metadata from a **manifest file**.

## How application name is derived

- **Application name** = first path segment under the project directory.
- Files directly in the project root get application name `default`.

Examples (project dir = `/path/to/Documents`):

| File path under project dir     | Application name |
|---------------------------------|-------------------|
| `FinanceApp/reports/Q1.pdf`     | `FinanceApp`      |
| `MyService/specs/design.docx`   | `MyService`      |
| `readme.md`                     | `default`        |

So: create one folder per application (e.g. `FinanceApp`, `MyService`) and put that app’s documents inside it.

## Manifest file

Place a file named **`manifest.json`** in the **project directory** (same root as your application folders). It is optional; if missing, only `application` (and `file_path`, `category`) are set.

### Schema

- **Top level:** object whose keys are **application names** (must match the folder name).
- **Values:** object with optional string fields. All are stored as Pinecone metadata and can be used for filtering or display.

Supported fields (all optional):

| Field         | Description                          | Example                    |
|---------------|--------------------------------------|----------------------------|
| `technology`  | Tech stack or languages              | `"Python, React, Postgres"`|
| `tools`       | Tools used (CI, infra, etc.)         | `"Docker, AWS, GitHub"`    |
| `description` | Short description of the application | `"Internal finance dashboard"` |
| `owner`       | Team or owner                        | `"Platform Team"`          |

You can add other string keys; the indexer will send them as metadata (Pinecone allows string, number, boolean, list of strings).

### Example `manifest.json`

```json
{
  "FinanceApp": {
    "technology": "Python, React, PostgreSQL",
    "tools": "Docker, AWS, GitHub Actions",
    "description": "Internal finance and reporting dashboard",
    "owner": "Finance Tech"
  },
  "MyService": {
    "technology": "Go, gRPC, Redis",
    "tools": "Kubernetes, Terraform, Datadog",
    "description": "Core API service for orders",
    "owner": "Backend Team"
  },
  "default": {
    "description": "Documents at project root (no app folder)"
  }
}
```

- Use the key `default` for files that live in the project root (no subfolder).
- Only include applications you want to describe; others will still get `application` from the folder name but no extra metadata.

## Filtering by application

When searching, you can restrict results to one application:

```bash
python semantic_search.py --query "deployment" --application FinanceApp
```

This uses Pinecone metadata filter `application = FinanceApp`. You can also filter by `category` (file type) and, in code, by any other manifest field you add.

## Where to put the manifest

- **Path:** `<project_dir>/manifest.json`
- Example: if `PINECONE_PROJECT_DIR=/Users/me/Documents`, then put the file at `/Users/me/Documents/manifest.json`.
- Copy from the example in the repo: `manifest.json.example` → rename/copy to `manifest.json` in your project directory.
