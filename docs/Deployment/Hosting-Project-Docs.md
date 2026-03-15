# Hosting project info & documentation (journey, lessons, design)

This project has **static HTML and Markdown docs** you may want to host publicly: the project info page (journey, timeline, lessons), plus architecture and design HTMLs.

## What we have

| Location | Content |
|----------|--------|
| **docs/index.html** | Main project info page: overview, modules, design summary, **project timeline**, **tools used**, **lessons learnt**. Single-page, no build. |
| **docs/Architecture-and-Design/*.html** | Design docs: Architecture, Decision-Matrix, Wireframes, Assessment-Design, Admin-Command-Center-Design, Diagnostics-Wireframes. |
| **docs/** (Markdown) | Setup, deployment, guides, development-iterations (e.g. AI-Assisted-Development-Narrative.md). |

The **“journey and lessons”** content is in **docs/index.html** (timeline, tools, lessons sections). The narrative in Markdown is in **docs/Development-Iterations/**.

---

## Option A: GitHub Pages (recommended for docs-only)

**Best for:** A dedicated docs/project-info site (e.g. `https://anoop-viswan.github.io/AI-Powered-Cloud-Migration-Command-Center/` or your-org.github.io/repo).

**Pros:**
- Free, fast, and designed for static sites.
- Serves the repo’s `docs/` (or a branch/folder) as a website.
- Separate from the app: no impact on Render, no extra cost.
- Custom domain supported.

**Cons:**
- You need to enable GitHub Pages and choose source (e.g. branch + folder).
- For **project sites** from the same repo, the site is often at `https://<user>.github.io/<repo>/` and the root of the site is the folder you choose (e.g. `/docs` → `index.html` at root of the site if you choose “/docs” as root).

**Steps (high level):**
1. Repo → **Settings** → **Pages**.
2. **Source:** Deploy from a branch.
3. **Branch:** e.g. `main` (or `initial-commit` until merged).
4. **Folder:** Choose **/docs** so that `docs/index.html` becomes the index when someone opens the site root.
5. Save. After a short delay, the site is at `https://<username>.github.io/AI-Powered-Cloud-Migration-Command-Center/` (or your configured URL).
6. All links in `docs/index.html` are relative (e.g. `Architecture-and-Design/Architecture.html`), so they work as long as the site root is the `docs/` folder.

**Note:** If you use **/ (root)** as the docs folder, you’d need to put the static files in a branch like `gh-pages` or in the repo root; using **/docs** keeps the repo clean and matches the current layout.

---

## Option B: Serve from the same Render app (backend)

**Best for:** One URL for both app and docs, or if you prefer not to use GitHub Pages.

**Idea:** The FastAPI app can serve the `docs/` directory as static files (e.g. under `/docs` or `/info`). The “project info” page would be at e.g. `https://cloud-migration-command-center.onrender.com/docs/` or `.../info/`.

**Pros:**
- Single deployment and URL.
- No extra service.

**Cons:**
- Uses the same Render service (and cold starts) as the app.
- Slightly more configuration (mount static route, ensure `index.html` is default for `/docs`).

**Implementation (sketch):** In FastAPI, add something like:
`app.mount("/docs", StaticFiles(directory="docs", html=True), name="docs")`
and ensure `docs/` is copied into the Docker image. Then `https://<your-render-url>/docs/` would serve `docs/index.html`.

---

## Recommendation

- **Use GitHub Pages** for the **project info / journey / lessons** (and the rest of `docs/`): free, standard place for “project website,” and keeps docs separate from the app.
- **Use Render** only for the **app** (API + frontend). If you later want a single entry URL, you can add a link from the app’s UI to the GitHub Pages site, or add the static mount (Option B) so `/docs` is served from the same Render app.

After you enable Pages with **/docs** as the root, the “updated” HTMLs are:

- **Main journey & lessons:** `docs/index.html`  
  → `https://<user>.github.io/AI-Powered-Cloud-Migration-Command-Center/`
- **Design:**  
  - `docs/Architecture-and-Design/Architecture.html`  
  - `docs/Architecture-and-Design/Decision-Matrix.html`  
  - `docs/Architecture-and-Design/Wireframes.html`  
  - `docs/Architecture-and-Design/Assessment-Design.html`  
  - `docs/Architecture-and-Design/Admin-Command-Center-Design.html`  
  - `docs/Architecture-and-Design/Diagnostics-Wireframes.html`  

All of these are already linked from `docs/index.html` (Design section).
