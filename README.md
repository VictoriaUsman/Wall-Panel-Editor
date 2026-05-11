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
- `MM_TO_PT = 72 / 25.4` — this is exact IEEE 754 double arithmetic; no rounding
- All intermediate coordinates stay in mm until the final ReportLab draw call
- Page 1 contains a **100 mm × 100 mm calibration square** — customer must measure this before proceeding
- Footer on every page: "PRINT AT 100% / ACTUAL SIZE — NEVER 'Fit to Page'"

### Wall editor
- Konva.js canvas, scales to fit viewport
- Drag photos from tray → wall to add panels
- Snap to 10 mm grid on drag-end
- Rotate by 90°/180°/-90° via control panel
- **20-step undo/redo** in Zustand store (Ctrl+Z / Ctrl+Shift+Z)
- Auto-save: debounced 800ms after every change, batch-PUT to `/api/jobs/:id/panels`

### Job status pipeline
```
DRAFT → UPLOADED → ARRANGING → PROOFING → APPROVED → PRINTED → SHIPPED
```
Invalid transitions are rejected by the API. Customers cannot transition to PROOFING (only operators send proofs). Customers can request changes from PROOFING → ARRANGING.

### Canvas catalog & hole positions
- Operator-only
- Interactive hole editor: click panel to place hole, drag to reposition, edit exact mm coordinates
- Holes stored in mm from panel top-left — never pixels
- Canvas sizes with no holes fall back to one centred hole 50 mm from top, with a UI warning

---

## Assumptions & Simplifications

1. **Mock storage**: photos are stored on the backend container's local disk. The presigned PUT flow is fully wired — swap `storage.py` for boto3/R2 to use real object storage without changing any other code.

2. **Operator identity**: any user with `is_operator=True` is an operator. The seed script creates one. To make more operators, set `is_operator=True` in the database or add an admin endpoint.

3. **Proof sending**: `POST /api/jobs/:id/send-proof` accepts a `proof_url` string (could be a link to a rendered preview image). The brief calls for a visual proof workflow; this is the backend hook for it.

4. **Print-master export**: resizes source photos to `300 dpi × catalog dimensions` using Pillow. If the source photo is smaller than 300 dpi at the target size, it will be upscaled — a production system would warn the operator.

5. **No email notifications**: the status pipeline is implemented but email triggers (e.g. "proof ready") would require an SMTP/SES integration not included here.

6. **A4 tiles only**: the tiled template uses A4 (210 × 297 mm). Letter (216 × 279 mm) is straightforward to add as a parameter.

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
