"""
Pinecone Semantic Search System (Python)

Search is restricted to a single project directory. Only files under that
directory are indexed; search returns only those documents.

- Create the index first with the CLI (see README).
- Set PINECONE_API_KEY in .env.
- Set PINECONE_PROJECT_DIR to your project path, or use --project-dir.
- Run: python semantic_search.py --project-dir /path/to/project --seed
- Run: python semantic_search.py --project-dir /path/to/project --query "..."
"""

import argparse
import hashlib
import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from pinecone import Pinecone
from pinecone.exceptions import PineconeException

from document_extractors import extract_content
from usage_tracker import (
    add_read_units,
    add_write_units,
    check_spend_guardrail,
    get_estimated_spend,
    report_usage,
)

load_dotenv()

INDEX_NAME = "coe-kb-search"
MANIFEST_FILENAME = "manifest.json"

# Directories to skip when scanning the project (hidden and common build/dep dirs)
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "env", "__pycache__", ".cache", "dist", "build", ".next", ".turbo"}
# File extensions to include (text/code + documents)
INCLUDE_EXTENSIONS = {
    ".md", ".txt", ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".rst",
    ".yml", ".yaml", ".toml", ".cfg", ".ini", ".sh", ".bash", ".zsh",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".pptx",
}
# Max chars per record (Pinecone limits); chunk larger files
MAX_CONTENT_CHARS = 8000
# Overlap when chunking (chars) to avoid cutting mid-sentence
CHUNK_OVERLAP = 200


def get_client():
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError(
            "PINECONE_API_KEY not set. Copy .env.example to .env and add your key from https://app.pinecone.io/"
        )
    return Pinecone(api_key=api_key)


def namespace_for_project(project_dir):
    """Stable namespace for this project so search is scoped to this directory only."""
    path = os.path.abspath(project_dir)
    # Use hash so any path is valid (no special chars, length limit)
    h = hashlib.sha256(path.encode()).hexdigest()[:16]
    return f"project_{h}"


def get_project_dir(args):
    """Resolve project dir from --project-dir or PINECONE_PROJECT_DIR."""
    path = (args.project_dir if args is not None and getattr(args, "project_dir", None) else None) or os.getenv("PINECONE_PROJECT_DIR")
    if not path:
        return None
    path = os.path.abspath(os.path.expanduser(path))
    if not os.path.isdir(path):
        raise ValueError(f"Project directory does not exist or is not a directory: {path}")
    return path


def load_manifest(project_dir):
    """Load manifest.json from project directory. Returns dict app_name -> metadata, or {} if missing/invalid."""
    path = Path(project_dir) / MANIFEST_FILENAME
    if not path.is_file():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except (json.JSONDecodeError, OSError):
        return {}


def application_from_path(rel_path):
    """Derive application name from relative path: first path segment, or 'default' if file is at project root."""
    parts = rel_path.replace("\\", "/").strip("/").split("/")
    if not parts or parts[0] == "":
        return "default"
    # File at project root (no subfolder) -> default
    if len(parts) == 1:
        return "default"
    return parts[0]


def collect_files_from_project(project_dir):
    """Yield (relative_path, full_path) for each includable file under project_dir."""
    root = Path(project_dir)
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        try:
            rel = p.relative_to(root)
        except ValueError:
            continue
        # Skip if any path part is a skipped dir or hidden (except .env)
        parts = rel.parts
        if any(part in SKIP_DIRS for part in parts):
            continue
        if any(part.startswith(".") and part != ".env" for part in parts):
            continue
        if p.suffix.lower() not in INCLUDE_EXTENSIONS:
            continue
        # Do not index the manifest file itself
        if p.name == MANIFEST_FILENAME:
            continue
        yield str(rel), str(p)


def _metadata_for_pinecone(manifest_meta):
    """Convert manifest entry to Pinecone-safe metadata (string, number, boolean, list of strings)."""
    out = {}
    for k, v in manifest_meta.items():
        if v is None:
            continue
        if isinstance(v, bool):
            out[k] = v
        elif isinstance(v, (int, float)):
            out[k] = v
        elif isinstance(v, list):
            out[k] = [str(x) for x in v]
        else:
            out[k] = str(v)
    return out


def build_records_from_project(project_dir):
    """Build list of records with content and metadata (file_path, category, application, content_type, manifest fields)."""
    manifest = load_manifest(project_dir)
    records = []
    for rel_path, full_path in collect_files_from_project(project_dir):
        ext = Path(full_path).suffix.lower() or "txt"
        category = ext.lstrip(".")
        result = extract_content(full_path, ext)
        if not result:
            continue
        chunks, content_type = result
        if not chunks:
            continue
        application = application_from_path(rel_path)
        manifest_meta = manifest.get(application, {})
        if not isinstance(manifest_meta, dict):
            manifest_meta = {}
        extra_meta = _metadata_for_pinecone(manifest_meta)
        for i, chunk in enumerate(chunks):
            record_id = re.sub(r"[^a-zA-Z0-9_-]", "_", rel_path) + f"__{i}"
            if len(record_id) > 200:
                record_id = hashlib.sha256(record_id.encode()).hexdigest()[:32] + f"__{i}"
            meta = {
                "file_path": rel_path,
                "category": category,
                "application": application,
                "content_type": content_type,
                **extra_meta,
            }
            chunk_text = chunk.strip()
            # Index field_map may be "text=content": record must include that key (some Pinecone setups)
            # or separate "text" / "content" fields. We send all so either convention works.
            record = {
                "_id": record_id,
                "text": chunk_text,
                "content": chunk_text,
                **meta,
            }
            record["text=content"] = chunk_text
            records.append(record)
    return records


def exponential_backoff_retry(func, max_retries=5):
    for attempt in range(max_retries):
        try:
            return func()
        except PineconeException as e:
            status_code = getattr(e, "status", None)
            if status_code and (status_code >= 500 or status_code == 429):
                if attempt < max_retries - 1:
                    delay = min(2**attempt, 60)
                    time.sleep(delay)
                else:
                    raise
            else:
                raise


def _record_search_usage(response):
    """Extract read_units from search response and add to usage tracker."""
    ru = None
    usage = getattr(response, "usage", None)
    if usage is not None:
        ru = getattr(usage, "read_units", None) or getattr(usage, "readUnits", None)
    if ru is None and hasattr(response, "result"):
        usage = getattr(response.result, "usage", None)
        if usage is not None:
            ru = getattr(usage, "read_units", None) or getattr(usage, "readUnits", None)
    if ru is not None:
        add_read_units(int(ru))


def seed_documents(index, project_dir, batch_size=96):
    """Upsert only files from the given project directory into a project-scoped namespace. Returns (namespace, record_count)."""
    namespace = namespace_for_project(project_dir)
    records = build_records_from_project(project_dir)
    if not records:
        print(f"No text files found under {project_dir}. Check INCLUDE_EXTENSIONS and that the path is correct.")
        return namespace, 0
    # Debug: confirm record has fields required by index field_map (check terminal when running seed)
    if records:
        print(f"[Seed] First record keys: {list(records[0].keys())}")
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        exponential_backoff_retry(lambda: index.upsert_records(namespace, batch))
        add_write_units(len(batch))  # ~1 write unit per record (serverless)
        time.sleep(0.1)
    print(f"Upserted {len(records)} chunks from {project_dir} into namespace '{namespace}'.")
    print("Waiting 10 seconds for indexing before search is reliable...")
    time.sleep(10)
    return namespace, len(records)


def search_knowledge_base(index, namespace, query, category_filter=None, application_filter=None, top_k=5):
    """Search only within the given project namespace. Optional filters: category (file type), application."""
    query_dict = {
        "top_k": top_k * 2,
        "inputs": {"text": query},
    }
    filters = []
    if category_filter:
        filters.append({"category": {"$eq": category_filter}})
    if application_filter:
        filters.append({"application": {"$eq": application_filter}})
    if filters:
        query_dict["filter"] = {"$and": filters} if len(filters) > 1 else filters[0]

    # Rerank can fail if a hit's content exceeds the model token limit (e.g. 1024 for bge-reranker-v2-m3).
    # Try with rerank first; fall back to no rerank on token-limit errors.
    rerank_config = {
        "model": "bge-reranker-v2-m3",
        "top_n": top_k,
        "rank_fields": ["content"],
    }
    try:
        results = index.search(
            namespace=namespace,
            query=query_dict,
            rerank=rerank_config,
        )
    except PineconeException as e:
        err_str = str(e).lower()
        if "token" in err_str and "limit" in err_str:
            results = index.search(namespace=namespace, query=query_dict, rerank=None)
        else:
            raise
    _record_search_usage(results)
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Pinecone semantic search restricted to a single project directory"
    )
    parser.add_argument(
        "--project-dir",
        type=str,
        default=None,
        help="Project directory to index and search (only this dir is used). Can also set PINECONE_PROJECT_DIR.",
    )
    parser.add_argument("--seed", action="store_true", help="Upsert documents from --project-dir into the index")
    parser.add_argument("--query", type=str, default=None, help="Run a single query and print results")
    parser.add_argument("--category", type=str, default=None, help="Filter by file extension (e.g. pdf, xlsx)")
    parser.add_argument("--application", type=str, default=None, help="Filter by application name (first folder under project dir)")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results (default 5)")
    parser.add_argument(
        "--check-usage",
        action="store_true",
        help="Print estimated Pinecone usage and spend limit, then exit.",
    )
    parser.add_argument(
        "--allow-over-limit",
        action="store_true",
        help="Allow running even if estimated usage is at or above PINECONE_SPEND_LIMIT (explicit permission).",
    )
    args = parser.parse_args()

    if args.check_usage:
        report_usage()
        return

    check_spend_guardrail(allow_over_limit_flag=args.allow_over_limit)

    project_dir = get_project_dir(args)
    if not project_dir:
        parser.error(
            "Project directory required. Use --project-dir /path/to/your/project or set PINECONE_PROJECT_DIR in .env"
        )

    namespace = namespace_for_project(project_dir)
    pc = get_client()
    index = pc.Index(INDEX_NAME)

    if args.seed:
        seed_documents(index, project_dir)
        if not args.query:
            args.query = "main entry point or configuration"

    if args.query:
        print(f"Project dir: {project_dir}")
        print(f"Namespace:   {namespace}")
        print(f"Query:       {args.query}")
        if args.category:
            print(f"Filter by:   category={args.category}")
        if args.application:
            print(f"Filter by:   application={args.application}")
        print("-" * 60)
        results = search_knowledge_base(
            index, namespace, args.query,
            category_filter=args.category, application_filter=args.application, top_k=args.top_k
        )
        hits = results.result.hits
        for i, hit in enumerate(hits, 1):
            doc_id = hit["_id"]
            score = hit["_score"]
            content = hit.fields["content"]
            file_path = hit.fields.get("file_path", "")
            category = hit.fields.get("category", "")
            application = hit.fields.get("application", "")
            print(f"{i}. [{file_path}] (score: {score:.3f}) app={application} [{category}]\n   {content[:300]}{'...' if len(content) > 300 else ''}\n")
        return

    # No --query: brief usage
    print(f"Project dir: {project_dir}")
    print(f"Namespace:   {namespace}")
    print("Run a query: python semantic_search.py --project-dir <dir> --query 'your question'")
    print("Filter by file type: --category pdf | xlsx | pptx | md ...")
    print("Filter by application: --application <folder name under project dir>")


if __name__ == "__main__":
    main()
