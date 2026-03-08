# How to run and view changes

## Quick start (first time)

```bash
# 1. Backend (Terminal 1)
source venv/bin/activate   # or: venv\Scripts\activate on Windows
uvicorn backend.main:app --reload --port 8000

# 2. Frontend (Terminal 2)
cd frontend
npm install
npm run dev
```

## Open the app

- **Frontend:** [http://localhost:5173](http://localhost:5173)
- **Backend API:** [http://localhost:8000](http://localhost:8000)

## View the first module (Assessment Profile)

1. Open [http://localhost:5173](http://localhost:5173)
2. Click **Assessment** in the nav
3. You should see:
   - Step indicator: 1. Profile | 2. Research | 3. Report
   - Instruction: "Please fill in all sections before proceeding to Research"
   - Seven pillar tabs: Overview | Architecture | Data | BC & DR | Cost | Security | Project
   - On **Overview** tab: "Continue to Architecture" button
   - On **Project** tab (last): "Save & continue to research" button

## Do I need to refresh?

- **Vite (frontend):** Hot Module Replacement (HMR) is on. Most changes auto-refresh. If not, refresh the browser (Cmd+R / Ctrl+R).
- **Backend:** `--reload` restarts the server on file changes. No manual restart needed.
- **After `npm install`:** Refresh the browser.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Assessment not found" | Backend not running. Start `uvicorn backend.main:app --reload --port 8000` |
| Blank page / CORS | Ensure frontend runs on 5173 and backend on 8000. Vite proxies `/api` to backend. |
| "Starting assessment…" forever | Backend not reachable. Check Terminal 1 for errors. |
