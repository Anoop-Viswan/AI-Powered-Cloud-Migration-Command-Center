# Research migration documentation with Parallel Search MCP

Use [Parallel Search MCP](https://docs.parallel.ai/integrations/mcp/search-mcp) in VS Code to find current vendor documentation, fetch relevant pages, and prepare reviewed notes for the Command Center's knowledge base. Search uses Fast mode; anonymous search and page fetching need no Parallel account or API key.

This is a **manual preparation workflow** in an external MCP client. The backend's automatic official-document search still uses Tavily. The Tool Gateway's MCP examples in the [Tool Extension Guide](Tool-Extension-Guide.md) are pseudocode; adding this client configuration does not register tools in the backend.

## 1. Connect your research client

You need VS Code with Copilot Chat and access to MCP tools. Follow the [VS Code MCP setup guide](https://code.visualstudio.com/docs/copilot/customization/mcp-servers) if MCP is unavailable in your environment.

Run **MCP: Open User Configuration** from the Command Palette. Merge the following entry into the existing `servers` object, keeping your other servers and settings:

```json
{
  "servers": {
    "parallel-migration-research": {
      "type": "http",
      "url": "https://search.parallel.ai/mcp",
      "headers": {
        "User-Agent": "Cloud-Migration-Command-Center-Research-Guide/1.0"
      }
    }
  }
}
```

This is the VS Code user-profile format. Use the command to open the correct file rather than creating `~/.vscode/mcp.json`. See the [configuration reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration) for supported fields.

Run **MCP: List Servers**, select `parallel-migration-research`, and start it. Review any trust prompt. In Chat's tool picker, enable this server's `web_search` and `web_fetch` tools. If the tools do not appear, use the server's **Show Output** action to inspect the connection.

## 2. Find and read official sources

Start a research conversation with a focused migration question. For example:

> Use Parallel's web_search to find current Microsoft Learn documentation for migrating an on-premises PostgreSQL 14 workload to Azure Database for PostgreSQL Flexible Server. Search for migration prerequisites, supported versions and extensions, networking, and cutover. Prefer learn.microsoft.com. Use web_fetch to read the relevant official pages. For each requirement, include its source URL, the page's update date when shown, and today's retrieval date. Keep workload assumptions and unanswered questions separate from documented requirements.

Check that the tool calls actually use the Parallel server. Search operators such as `site:learn.microsoft.com` can help focus queries, but verify each returned URL's host and the page's relevance yourself. Prefer vendor documentation over third-party summaries. If a page cannot be fetched, open it in a browser and review it before using its claims.

Anonymous use has rate limits. If a tool returns a quota or rate-limit message, pause and follow its retry guidance; an error is not research evidence. See [Parallel's setup and limits](https://docs.parallel.ai/integrations/mcp/search-mcp) for account options when you need higher limits.

## 3. Save reviewed evidence in your existing KB directory

Review the sources and write a short Markdown note under the **project directory already used by your KB**. For example, save `FinanceApp/migration-research.md` under `/path/to/your/docs`. The first folder becomes the application metadata (`FinanceApp`); see [Manifest](Manifest.md).

Use a structure like this, replacing the placeholders with verified information:

```markdown
# FinanceApp: PostgreSQL to Azure migration research

Reviewed: YYYY-MM-DD
Workload assumptions: [versions, region, availability requirements]

## Finding: [one migration requirement]
Verified summary: [what the vendor page actually says]
Source: [exact official URL]
Page updated: [date shown, or "not stated"]
Retrieved: YYYY-MM-DD
Applicability / open questions: [what still needs checking for this workload]
```

Keep the source URL next to each finding so it remains available in retrieved text. A saved Markdown file is a snapshot: recheck time-sensitive limits and supported versions before making migration decisions.

## 4. Seed and check the knowledge base

Complete the app's [one-time setup](../Setup-and-Reference/One-Time-Setup.md) first. The KB still needs its Pinecone key and index; Assessment and Chat also need the configured LLM. Parallel's anonymous endpoint only removes the credential requirement for this external web-research step.

From the repository root, using the same project-directory path for both commands:

```bash
python -m backend.semantic_search --project-dir /path/to/your/docs --seed
python -m backend.semantic_search --project-dir /path/to/your/docs --query "PostgreSQL to Azure migration prerequisites" --application FinanceApp
```

Replace `/path/to/your/docs` and `FinanceApp` with your existing KB root and application folder. Seeding scans the whole project directory and uses the existing Pinecone spend guardrail. See the [Pinecone guide](Pinecone-Guide.md) for setup, usage, and seeding from Admin.

Check that the search returns the reviewed note's file path and relevant text. Configure `PINECONE_PROJECT_DIR` to that same KB root for the app to use the same namespace. Assessment research can then retrieve the note as KB evidence; it is not a live Parallel result or an entry in the separate `official_docs` results. Repeat the review and seed steps when refreshing your notes.
