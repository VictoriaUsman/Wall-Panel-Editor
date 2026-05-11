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
| PDF | ReportLab (pure Python, exact mm→pt conversion) |
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

### Wall editor
- Konva.js canvas, scales to fit viewport
- Drag photo from tray → wall to place a new panel; photo drops at cursor centre
- Drag a photo from the tray **onto an existing panel** to swap its photo in place
- Snap to 10 mm grid on drag-end
- Panels rotate about their visual centre (Konva Group anchored at panel centre, no offset)
- Rotate by ±90° / ±180° via 2×2 button grid in the control panel
- **20-step undo/redo** in Zustand store (Ctrl+Z / Ctrl+Shift+Z)
- Auto-save: debounced 800 ms after every change, batch-PUT to `/api/jobs/:id/panels`
- Panel label shown in a translucent strip at the bottom edge of each panel

### Job status pipeline
```
DRAFT → UPLOADED → ARRANGING → PROOFING → APPROVED → PRINTED → SHIPPED
```

Customer buttons at each step:
| Status | Button | Transitions to |
|---|---|---|
| DRAFT | Mark photos uploaded | UPLOADED |
| UPLOADED | Start arranging | ARRANGING |
| ARRANGING | Submit for review | PROOFING |
| PROOFING | Approve | APPROVED |
| PROOFING | Request changes | ARRANGING |

Operator buttons:
| Status | Button | Transitions to |
|---|---|---|
| ARRANGING | Send proof | PROOFING |
| APPROVED | Mark printed | PRINTED |
| PRINTED | Mark shipped | SHIPPED |

Invalid transitions are rejected by the API. Customers cannot transition to PROOFING (only operators send proofs). The editor is read-only for customers while in PROOFING.

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
6. Once in PROOFING: view the read-only layout, download the hanging template + reference sheet PDFs, then Approve or Request Changes

### Operator
1. Log in at the same URL — redirected to `/operator` pipeline view
2. See all customer jobs grouped by status (auto-refreshes every 30 s)
3. Open any job to refine the layout, then Send Proof → customer moves to PROOFING
4. After customer approves: Mark Printed, then Mark Shipped
5. Download a ZIP of 300 dpi per-panel print masters + MANIFEST.txt at any point after APPROVED
6. Manage canvas sizes and hole positions at `/operator/catalog`

---

## Assumptions & Simplifications

1. **Mock storage**: photos are stored on the backend container's local disk. The presigned PUT flow is fully wired — swap `storage.py` for boto3/R2 to use real object storage without changing any other code.

2. **Operator identity**: any user with `is_operator=True` is an operator. The seed script creates one. To create more operators, set `is_operator=True` in the database directly.

3. **Proof sending**: `POST /api/jobs/:id/send-proof` accepts an optional `proof_url` string. Transitioning the job to PROOFING via the UI uses `POST /api/jobs/:id/transition` which is equivalent. The `proof_url` field is the hook for attaching a rendered preview link in a future iteration.

4. **Print-master export**: resizes source photos to `300 dpi × catalog dimensions` using Pillow. If the source photo is lower resolution than required it will be upscaled — a production system would warn the operator.

5. **No email notifications**: the status pipeline is implemented but email triggers (e.g. "proof ready") would require an SMTP/SES integration not included here.

6. **A4 tiles only**: the tiled template uses A4 (210 × 297 mm). Letter (216 × 279 mm) is straightforward to add as a parameter to `build_tiled_template`.

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
