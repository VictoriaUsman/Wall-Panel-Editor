# Wood Panel Wall Designer

A full-stack web app that takes customers from photo upload to a 1:1 printed hanging template they can tape to their wall and drill through.

## Quick Start

```bash
# Start everything (Postgres + backend + frontend)
make dev

# In a second terminal, seed the database with an operator account + default canvas sizes
make seed

# Run geometry unit tests (no Docker needed)
make test-local
```

Then open:
- **Customer app**: http://localhost:5173
- **API docs**: http://localhost:8000/docs

**Operator login** (seeded): `operator@woodpanel.com` / `operator123`

Register any email/password to create a customer account.

---

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | React 18 + TypeScript + Vite + Konva.js + Tailwind + Zustand + React Query v5 |
| Backend | FastAPI + SQLAlchemy async + PostgreSQL + asyncpg |
| PDF | ReportLab (exact `MM_TO_PT = 72/25.4`, no intermediate rounding) |
| Image processing | Pillow 11.x (300 dpi print-master export) |
| Storage | Mock: local disk + `/mock-upload` PUT endpoint. Swap `app/services/storage.py` for real S3/R2 |
| Auth | JWT in httpOnly cookie, 7-day expiry |
| Container | Docker Compose (db + backend + frontend) |

---

## Architecture

### Coordinate system

All measurements are millimetres end-to-end.
- `Panel.x_mm / y_mm` = top-left corner in wall coordinates (mm from wall top-left)
- `Hole.x_mm / y_mm` = position relative to panel top-left (mm)
- Rotation is clockwise degrees about the panel centre
- No pixels or normalised percentages anywhere in the data model

### Geometry module (`backend/app/services/geometry.py`)

The critical transform chain:
```
hole (panel-local mm)
  → rotate about panel centre
  → wall coords (mm)
  → tile-page PDF coords (pt, via exact MM_TO_PT = 72/25.4)
```

**21 unit tests** in `backend/tests/test_geometry.py` cover this chain including:
- 0°, 90°, 180°, 270° rotations with hand-verified expected values
- Invariance: hole at panel centre is unchanged under any rotation
- 2 m span precision test: gap between two points 2000 mm apart must equal `2000 × MM_TO_PT` within 0.001 pt

### PDF accuracy

The tiled hanging template is accurate to within printer mechanical tolerance:
- `MM_TO_PT = 72 / 25.4` — exact IEEE 754 double arithmetic; no rounding
- All intermediate coordinates stay in mm until the final ReportLab draw call
- Page 1 contains a **100 mm × 100 mm calibration square** — customer must measure this before proceeding
- Footer on every page: "PRINT AT 100% / ACTUAL SIZE — NEVER 'Fit to Page'"
- Reference sheet is A3, with the wall diagram pinned near the top and a centred drill-point table below

### Wall editor

- Konva.js canvas, scales to fit viewport
- Drag photo from tray → wall to place a new panel at the cursor centre
- Drag a photo from the tray **onto an existing panel** to swap its photo in place
- Snap to 10 mm grid on drag-end
- Panels rotate about their visual centre (Konva Group anchored at panel centre, no offset)
- Rotate by ±90° / ±180° via 2×2 button grid in the control panel
- **20-step undo/redo** in Zustand store (Ctrl+Z / Ctrl+Shift+Z)
- Auto-save: debounced 800 ms after every change, batch-PUT to `/api/jobs/:id/panels`
- Panel size label shown in a translucent strip at the bottom edge of each panel

### Job status pipeline

```
DRAFT → UPLOADED → ARRANGING → PROOFING → APPROVED → PRINTED → SHIPPED
```

**Customer buttons:**

| Current status | Button | Result |
|---|---|---|
| DRAFT | Mark photos uploaded | → UPLOADED |
| UPLOADED | Start arranging | → ARRANGING |
| ARRANGING | Submit for review | → PROOFING |
| PROOFING (proof not yet sent) | _(disabled, awaiting operator)_ | — |
| PROOFING (proof sent) | Request changes | → ARRANGING |
| PROOFING (proof sent) | Approve | → APPROVED |

**Operator buttons:**

| Current status | Button | Result |
|---|---|---|
| PROOFING | Send proof | Sets `proof_url`; status stays PROOFING |
| APPROVED | Mark printed | → PRINTED |
| PRINTED | Mark shipped | → SHIPPED |

**Notes:**
- Customers submit for review themselves (ARRANGING → PROOFING).
- The operator then reviews the layout and clicks **Send proof**. This sets `proof_url` on the job without changing the status — it is the gate that unlocks the customer's Approve button.
- Until the operator sends the proof, the customer sees an "awaiting operator review" banner and the Approve button is hidden.
- The editor is read-only for customers while in PROOFING; Request Changes re-opens editing.
- Invalid transitions are rejected by the API.

### Canvas catalog & hole positions

- Operator-only (`/operator/catalog`)
- Interactive Konva hole editor: click panel to place hole, drag to reposition, type exact mm coordinates, delete
- Holes stored in mm from panel top-left — never pixels
- Canvas sizes with no holes fall back to one centred hole 50 mm from top, with a UI warning in the catalog and on the PDF

---

## Roles

### Customer

1. Register / log in
2. Create a job — set wall title and dimensions (mm)
3. Upload photos via drag-and-drop (JPEG / PNG / WebP); each PUT goes directly to storage, not through the app server
4. Arrange panels on the virtual wall; remove or swap photos at any time
5. Advance through DRAFT → UPLOADED → ARRANGING, then submit for review
6. While in PROOFING: view the read-only layout; once the operator sends the proof, download the **Hanging template** + **Reference sheet** PDFs, then Approve or Request Changes
7. Delete any job not yet in APPROVED / PRINTED / SHIPPED

### Operator

1. Log in at the same URL — redirected to `/operator` pipeline view
2. See all customer jobs grouped by status (auto-refreshes every 30 s)
3. Open any job to inspect or refine the layout
4. Click **Send proof** on any PROOFING job — unlocks the customer's Approve button
5. After customer approves: Mark Printed, then Mark Shipped
6. Download a ZIP of 300 dpi per-panel print masters + `MANIFEST.txt` at any point after APPROVED
7. Manage canvas sizes and hole positions at `/operator/catalog`

---

## Assumptions & Simplifications

1. **Mock storage**: photos are stored on the backend container's local disk. The presigned PUT flow is fully wired — swap `storage.py` for boto3/R2 to use real object storage without changing any other code.

2. **Operator identity**: any user with `is_operator=True` is an operator. The seed script creates one. To promote an existing user to operator, set `is_operator=True` in the database directly.

3. **Proof URL**: `POST /api/jobs/:id/send-proof` accepts an optional `proof_url` string. If omitted, it stores the sentinel value `"sent"`. The field is the hook for attaching a rendered preview link (e.g. a hosted PDF) in a future iteration.

4. **Print-master export**: resizes source photos to `300 dpi × catalog dimensions` using Pillow. If the source photo is lower resolution it will be upscaled — a production system would warn the operator.

5. **No email notifications**: the status pipeline is implemented but email triggers (e.g. "proof ready for review") would require an SMTP/SES integration not included here.

6. **A4 tiles only**: the tiled template uses A4 (210 × 297 mm). Letter (216 × 279 mm) is straightforward to add as a parameter to `build_tiled_template`.

7. **Panel size swap**: the current UI does not have a control to change the canvas size of an already-placed panel. Size is set on initial drag from the tray (defaults to first active catalog size). Changing size requires removing and re-adding the panel.

---

## PDF Printing Instructions (summary)

Page 1 of every tiled PDF contains the full instructions. Key points:

| App | Setting |
|---|---|
| Adobe Acrobat/Reader | File → Print → Page Sizing: **Actual Size** |
| Chrome / Edge | Print → More settings → Scale: **100%**, uncheck **Fit to page** |
| macOS Preview | File → Print → Scale: **100%**, uncheck **Scale to fit** |
| Windows | Printer Properties → **Actual size** / **None** scaling |

**Verify the 100 mm calibration square on page 1 before taping anything.**

---

## Running Tests

```bash
# Inside Docker
docker compose exec backend pytest tests/ -v

# Locally (requires Python env with dependencies installed)
cd backend
pytest tests/test_geometry.py -v
```
