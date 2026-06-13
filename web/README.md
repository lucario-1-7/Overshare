# Overshare — Web UI (Phase 5)

React + Tailwind + react-flow frontend. It is **dumb by design**: it only ever reads
the `Report` contract (`backend/contracts/`) and renders it into fixed sections —
Upload → Annotated Image → Detected Signals → **Exposure Graph** → Risk Scores →
Attack Path → Fixes → Explanation. All intelligence is server-side.

## Run

```bash
cd web
npm install
npm run dev        # http://localhost:5173
```

The dev server **proxies** `/analyze`, `/health`, `/sample-report` to the backend at
`http://localhost:8077` (override with `VITE_API_BASE`). Start the backend separately:

```powershell
..\.venv-ml\Scripts\python.exe -m uvicorn backend.main:app --port 8077   # full GPU stack
# or, EXIF-only, no GPU:  ..\.venv\Scripts\python.exe -m uvicorn backend.main:app --port 8077
```

No backend handy? Click **Load sample** — it renders an embedded copy of
`fixtures/report_sample.json`, so the whole UI works offline.

## Notes

- Develops against the **frozen contract** — every field is treated as optional-friendly
  (`annotatedImage` may be `null`, `graph` may be empty), so partial Phase 1–4 reports render fine.
- The **one-click EXIF strip** (Fixes panel) re-encodes the uploaded image via a canvas
  entirely in the browser — it drops all metadata and downloads a clean copy. Nothing is uploaded for that step.
- Build: `npm run build` → `dist/` (servable from the backend origin behind the Phase 6 tunnel).
