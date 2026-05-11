"""
PDF generation for the Wood Panel Wall Designer.

Two outputs:
  (a) Tiled 1:1 hanging template — multi-page A4, prints at 100% scale.
  (b) Scaled reference sheet — single A4/A3 page with labelled layout + drill-point table.

ACCURACY CONTRACT:
  All coordinates use MM_TO_PT = 72/25.4 exactly.
  No intermediate rounding. Every measurement stays in mm until the final
  ReportLab draw call. This guarantees ±0 mm error from the maths; the only
  source of error is the printer's own accuracy, which this PDF cannot control.
  A 100 mm calibration square on page 1 lets the customer verify their printer
  before taping anything together.

PRINTING INSTRUCTIONS embedded in every PDF footer:
  "Print at 100% / Actual Size. NEVER use Fit to Page or Shrink to Printable Area."
"""

import io
import math
from typing import List, Tuple, Optional
from dataclasses import dataclass

from reportlab.lib.pagesizes import A4, A3
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas as rl_canvas

from app.services.geometry import (
    Point,
    MM_TO_PT,
    hole_to_wall,
    wall_to_tile_pdf,
    wall_to_pdf,
    fallback_hole,
)

# A4 dimensions in mm
A4_W_MM = 210.0
A4_H_MM = 297.0
A3_W_MM = 297.0
A3_H_MM = 420.0

# Crop mark length and offset from tile edge
CROP_MARK_LEN_MM = 5.0
CROP_MARK_OFFSET_MM = 2.0

# Colours
COLOUR_PANEL_OUTLINE = colors.HexColor("#333333")
COLOUR_HOLE_MARK = colors.HexColor("#CC0000")
COLOUR_CROP_MARK = colors.HexColor("#888888")
COLOUR_CALIBRATION = colors.HexColor("#0000CC")
COLOUR_LABEL = colors.HexColor("#333333")
COLOUR_GRID = colors.HexColor("#DDDDDD")


@dataclass
class HoleData:
    label: str
    x_mm: float    # panel-local
    y_mm: float    # panel-local


@dataclass
class PanelData:
    panel_id: str
    label: str          # e.g. "Panel 1"
    x_mm: float         # wall top-left
    y_mm: float
    width_mm: float
    height_mm: float
    rotation_deg: float
    holes: List[HoleData]
    has_hole_config: bool


@dataclass
class WallLayout:
    wall_width_mm: float
    wall_height_mm: float
    panels: List[PanelData]
    job_title: str


def _mm(v: float) -> float:
    """Convert mm to ReportLab points (exact)."""
    return v * MM_TO_PT


def _draw_cross(c: rl_canvas.Canvas, x_pt: float, y_pt: float, size_pt: float = 6.0):
    """Draw a ✕ drill mark centred at (x_pt, y_pt)."""
    h = size_pt / 2
    c.line(x_pt - h, y_pt - h, x_pt + h, y_pt + h)
    c.line(x_pt + h, y_pt - h, x_pt - h, y_pt + h)


def _draw_crop_marks(c: rl_canvas.Canvas, tile_w_mm: float, tile_h_mm: float):
    """Draw crop marks at all four corners of a tile page."""
    c.setStrokeColor(COLOUR_CROP_MARK)
    c.setLineWidth(0.5)
    offset = _mm(CROP_MARK_OFFSET_MM)
    length = _mm(CROP_MARK_LEN_MM)

    # bottom-left corner (PDF origin)
    c.line(-offset, 0, -offset - length, 0)
    c.line(0, -offset, 0, -offset - length)

    # bottom-right
    w = _mm(tile_w_mm)
    c.line(w + offset, 0, w + offset + length, 0)
    c.line(w, -offset, w, -offset - length)

    # top-left
    h = _mm(tile_h_mm)
    c.line(-offset, h, -offset - length, h)
    c.line(0, h + offset, 0, h + offset + length)

    # top-right
    c.line(w + offset, h, w + offset + length, h)
    c.line(w, h + offset, w, h + offset + length)


def _draw_panel_on_tile(
    c: rl_canvas.Canvas,
    panel: PanelData,
    tile_origin_x_mm: float,
    tile_origin_y_mm: float,
    tile_h_mm: float,
    draw_holes: bool = True,
):
    """
    Draw panel outline and hole marks on the current tile page.
    Only draws the portion of the panel that overlaps this tile.
    ReportLab canvas is already set up for this tile.
    """
    # The four corners of the panel in wall coords (before rotation)
    corners_local = [
        Point(0.0, 0.0),
        Point(panel.width_mm, 0.0),
        Point(panel.width_mm, panel.height_mm),
        Point(0.0, panel.height_mm),
    ]
    from app.services.geometry import rotate_point_about, panel_center as pc
    centre = pc(panel.x_mm, panel.y_mm, panel.width_mm, panel.height_mm)

    def local_to_wall(lp: Point) -> Point:
        wall_unrotated = Point(panel.x_mm + lp.x_mm, panel.y_mm + lp.y_mm)
        return rotate_point_about(wall_unrotated, centre, panel.rotation_deg)

    wall_corners = [local_to_wall(lp) for lp in corners_local]

    def to_pdf(wp: Point) -> Tuple[float, float]:
        pp = wall_to_tile_pdf(wp, tile_origin_x_mm, tile_origin_y_mm, tile_h_mm)
        return pp.x_pt, pp.y_pt

    # Draw panel outline
    c.setStrokeColor(COLOUR_PANEL_OUTLINE)
    c.setLineWidth(1.0)
    path = c.beginPath()
    x0, y0 = to_pdf(wall_corners[0])
    path.moveTo(x0, y0)
    for wc in wall_corners[1:]:
        x, y = to_pdf(wc)
        path.lineTo(x, y)
    path.close()
    c.drawPath(path, stroke=1, fill=0)

    # Panel label at centre
    cw = to_pdf(Point(
        sum(wc.x_mm for wc in wall_corners) / 4,
        sum(wc.y_mm for wc in wall_corners) / 4,
    ))
    c.setFillColor(COLOUR_LABEL)
    c.setFont("Helvetica", 7)
    c.drawCentredString(cw[0], cw[1] - 3, panel.label)

    if not panel.has_hole_config:
        c.setFont("Helvetica-Oblique", 6)
        c.setFillColor(colors.orange)
        c.drawCentredString(cw[0], cw[1] - 11, "[!] needs hole config")

    if not draw_holes:
        return

    # Draw hole marks
    c.setStrokeColor(COLOUR_HOLE_MARK)
    c.setFillColor(COLOUR_HOLE_MARK)
    c.setLineWidth(1.5)

    for hole in panel.holes:
        wall_pos = hole_to_wall(
            hole.x_mm, hole.y_mm,
            panel.x_mm, panel.y_mm,
            panel.width_mm, panel.height_mm,
            panel.rotation_deg,
        )
        hx, hy = to_pdf(wall_pos)
        _draw_cross(c, hx, hy, size_pt=8.0)

        # Hole label
        c.setFont("Helvetica", 5)
        c.drawString(hx + 5, hy + 2, hole.label)


def build_tiled_template(layout: WallLayout, page_size_mm: Tuple[float, float] = (A4_W_MM, A4_H_MM)) -> bytes:
    """
    Generate the 1:1 tiled hanging template PDF.

    Page 1: calibration check square + printing instructions.
    Pages 2+: tiles covering the full wall at 1:1 scale.
    """
    tile_w_mm, tile_h_mm = page_size_mm
    buf = io.BytesIO()

    page_w_pt = _mm(tile_w_mm)
    page_h_pt = _mm(tile_h_mm)
    c = rl_canvas.Canvas(buf, pagesize=(page_w_pt, page_h_pt))

    # --- Page 1: calibration + instructions ---
    _draw_calibration_page(c, tile_w_mm, tile_h_mm, layout.job_title)
    c.showPage()

    # Tile grid
    cols = math.ceil(layout.wall_width_mm / tile_w_mm)
    rows = math.ceil(layout.wall_height_mm / tile_h_mm)
    total_tiles = cols * rows
    tile_num = 1

    for row in range(rows):
        for col in range(cols):
            tile_origin_x = col * tile_w_mm
            tile_origin_y = row * tile_h_mm

            # Background (white)
            c.setFillColor(colors.white)
            c.rect(0, 0, page_w_pt, page_h_pt, stroke=0, fill=1)

            _draw_crop_marks(c, tile_w_mm, tile_h_mm)

            # Draw all panels that intersect this tile
            for panel in layout.panels:
                _draw_panel_on_tile(c, panel, tile_origin_x, tile_origin_y, tile_h_mm)

            # Tile label
            c.setFillColor(COLOUR_LABEL)
            c.setFont("Helvetica-Bold", 8)
            c.drawString(_mm(5), _mm(5), f"Tile {tile_num}/{total_tiles}  (col {col+1}/{cols}, row {row+1}/{rows})")
            c.setFont("Helvetica", 7)
            c.drawString(_mm(5), _mm(12), f"{layout.job_title}  |  Wall origin offset: ({tile_origin_x:.0f}, {tile_origin_y:.0f}) mm")

            # CRITICAL footer: print-size warning
            _draw_print_footer(c, tile_w_mm, tile_h_mm)

            c.showPage()
            tile_num += 1

    c.save()
    return buf.getvalue()


def _draw_calibration_page(c: rl_canvas.Canvas, tile_w_mm: float, tile_h_mm: float, job_title: str):
    """
    Page 1 of the tiled PDF: calibration square + full printing instructions.
    Safety-critical: customer MUST verify this before drilling.

    Layout:
      [title / warning]
      [100mm square] | [measure / reprint note]
      [full-width 2-column printer settings]
      [assembly instructions]
    """
    page_w_pt = _mm(tile_w_mm)
    page_h_pt = _mm(tile_h_mm)

    c.setFillColor(colors.white)
    c.rect(0, 0, page_w_pt, page_h_pt, stroke=0, fill=1)

    y = page_h_pt - _mm(15)

    # Title
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(_mm(10), y, f"HANGING TEMPLATE - {job_title}")
    y -= _mm(8)
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(COLOUR_HOLE_MARK)
    c.drawString(_mm(10), y, ">>> STEP 1: VERIFY PRINT SCALE BEFORE DOING ANYTHING ELSE <<<")
    y -= _mm(12)

    # Calibration square: exactly 100 mm x 100 mm
    sq_x = _mm(10)
    sq_y = y - _mm(100)
    sq_side = _mm(100)

    c.setStrokeColor(COLOUR_CALIBRATION)
    c.setLineWidth(1.0)
    c.rect(sq_x, sq_y, sq_side, sq_side, stroke=1, fill=0)

    # Horizontal dimension label (below square, clear of instruction column)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(COLOUR_CALIBRATION)
    c.drawCentredString(sq_x + sq_side / 2, sq_y - _mm(7), "<-- 100 mm -->")

    # Vertical dimension label (right of square, rotated so it reads upward)
    c.saveState()
    c.translate(sq_x + sq_side + _mm(8), sq_y + sq_side / 2)
    c.rotate(90)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(COLOUR_CALIBRATION)
    c.drawCentredString(0, 0, "<-- 100 mm -->")
    c.restoreState()

    # Short measurement check beside the square (fits in ~72 mm column)
    ix = sq_x + sq_side + _mm(18)
    iy = y - _mm(8)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.black)
    c.drawString(ix, iy, "MEASURE THIS SQUARE")
    iy -= _mm(6)
    c.setFont("Helvetica", 9)
    c.drawString(ix, iy, "Both sides must be exactly 100 mm.")
    iy -= _mm(6)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(COLOUR_HOLE_MARK)
    c.drawString(ix, iy, "If either side is wrong: REPRINT.")
    iy -= _mm(8)
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.black)
    c.drawString(ix, iy, "See printer settings below.")

    # --- Full-width printer settings (two columns) below the square ---
    y2 = sq_y - _mm(15)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.black)
    c.drawString(_mm(10), y2, "How to print at 100% / Actual Size:")
    y2 -= _mm(7)

    col1_x = _mm(12)
    col2_x = _mm(107)
    lh = _mm(5)

    # Left column: Acrobat + Chrome
    ly = y2
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.black)
    c.drawString(col1_x, ly, "Adobe Acrobat / Reader:")
    ly -= lh
    c.setFont("Helvetica", 8)
    c.drawString(col1_x, ly, "File > Print > Page Sizing: 'Actual Size'")
    ly -= lh
    c.drawString(col1_x, ly, "NOT 'Fit' or 'Shrink to printable area'")
    ly -= _mm(4)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(col1_x, ly, "Chrome / Edge browser:")
    ly -= lh
    c.setFont("Helvetica", 8)
    c.drawString(col1_x, ly, "Print > More settings > Scale: 100%")
    ly -= lh
    c.drawString(col1_x, ly, "Uncheck 'Fit to page'")

    # Right column: macOS Preview + Windows
    ry = y2
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.black)
    c.drawString(col2_x, ry, "macOS Preview:")
    ry -= lh
    c.setFont("Helvetica", 8)
    c.drawString(col2_x, ry, "File > Print > Scale: 100%")
    ry -= lh
    c.drawString(col2_x, ry, "Uncheck 'Scale to fit'")
    ry -= _mm(4)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(col2_x, ry, "Windows Print dialog:")
    ry -= lh
    c.setFont("Helvetica", 8)
    c.drawString(col2_x, ry, "Printer Properties > Paper/Quality >")
    ry -= lh
    c.drawString(col2_x, ry, "'Actual size' or 'None' scaling")

    # Assembly instructions
    y2 = min(ly, ry) - _mm(12)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(colors.black)
    c.drawString(_mm(10), y2, "ASSEMBLY & DRILLING INSTRUCTIONS")
    y2 -= _mm(7)

    instructions = [
        ("STEP 2 - Tile alignment:",
         "Cut along the crop marks (small grey lines at page corners). Overlap neighbouring"),
        ("",
         "tiles so the crop marks align. Tape from behind with low-tack masking tape."),
        ("STEP 3 - Position on wall:",
         "Use a spirit level. Align the top edge of the template to your chosen height."),
        ("",
         "Mark the wall edges in pencil so you can reposition if the tape slips."),
        ("STEP 4 - Drill:",
         "Drill through the paper at each red X. Use a 4-6 mm bit for D-ring anchors."),
        ("",
         "Hold the template flat against the wall while drilling - do not let it shift."),
        ("STEP 5 - Remove:",
         "Peel the template away. Erase pencil lines. Hang your panels."),
    ]

    c.setFont("Helvetica", 8)
    for heading, body in instructions:
        if heading:
            c.setFont("Helvetica-Bold", 8)
            c.setFillColor(colors.black)
            c.drawString(_mm(10), y2, heading)
            c.setFont("Helvetica", 8)
            c.drawString(_mm(55), y2, body)
        else:
            c.drawString(_mm(55), y2, body)
        y2 -= _mm(5.5)

    _draw_print_footer(c, tile_w_mm, tile_h_mm)


def _draw_print_footer(c: rl_canvas.Canvas, tile_w_mm: float, tile_h_mm: float):
    """Print-size warning footer on every page."""
    y = _mm(4)
    c.setFillColor(COLOUR_HOLE_MARK)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(
        _mm(tile_w_mm) / 2, y,
        "[!]  PRINT AT 100% / ACTUAL SIZE -- NEVER 'Fit to Page' or 'Shrink to Printable Area'  [!]"
    )


def build_reference_sheet(layout: WallLayout) -> bytes:
    """
    Scaled reference sheet: single A3 page with the full wall layout scaled to fit,
    labelled panels, and a drill-point table.
    """
    # Fit wall into A3 with 20mm margins
    margin_mm = 20.0
    table_height_mm = 80.0  # reserved for the table at bottom
    avail_w = A3_W_MM - 2 * margin_mm
    avail_h = A3_H_MM - 2 * margin_mm - table_height_mm - 10.0

    scale = min(avail_w / layout.wall_width_mm, avail_h / layout.wall_height_mm)
    drawn_w = layout.wall_width_mm * scale
    drawn_h = layout.wall_height_mm * scale

    # Centre the wall drawing horizontally
    wall_offset_x_mm = margin_mm + (avail_w - drawn_w) / 2
    wall_offset_y_mm = margin_mm + table_height_mm + 10.0

    buf = io.BytesIO()
    page_w_pt = _mm(A3_W_MM)
    page_h_pt = _mm(A3_H_MM)
    c = rl_canvas.Canvas(buf, pagesize=(page_w_pt, page_h_pt))

    # Wall bounding box
    c.setStrokeColor(colors.HexColor("#AAAAAA"))
    c.setLineWidth(0.5)
    wx = _mm(wall_offset_x_mm)
    wy = page_h_pt - _mm(wall_offset_y_mm) - _mm(drawn_h)
    c.rect(wx, wy, _mm(drawn_w), _mm(drawn_h), stroke=1, fill=0)

    from app.services.geometry import rotate_point_about, panel_center as pc

    drill_rows: List[dict] = []

    for panel in layout.panels:
        # Draw panel in scaled coords
        corners_local = [
            Point(0.0, 0.0),
            Point(panel.width_mm, 0.0),
            Point(panel.width_mm, panel.height_mm),
            Point(0.0, panel.height_mm),
        ]
        centre = pc(panel.x_mm, panel.y_mm, panel.width_mm, panel.height_mm)

        def to_ref_pdf(wp: Point) -> Tuple[float, float]:
            sx = wall_offset_x_mm + wp.x_mm * scale
            sy = wall_offset_y_mm + wp.y_mm * scale
            return _mm(sx), page_h_pt - _mm(sy)

        def local_to_wall(lp: Point) -> Point:
            wall_unrotated = Point(panel.x_mm + lp.x_mm, panel.y_mm + lp.y_mm)
            return rotate_point_about(wall_unrotated, centre, panel.rotation_deg)

        wall_corners = [local_to_wall(lp) for lp in corners_local]
        pdf_corners = [to_ref_pdf(wc) for wc in wall_corners]

        c.setStrokeColor(COLOUR_PANEL_OUTLINE)
        c.setLineWidth(0.7)
        path = c.beginPath()
        path.moveTo(*pdf_corners[0])
        for pc_ in pdf_corners[1:]:
            path.lineTo(*pc_)
        path.close()
        c.drawPath(path, stroke=1, fill=0)

        # Panel label at centroid
        cx = sum(p[0] for p in pdf_corners) / 4
        cy = sum(p[1] for p in pdf_corners) / 4
        c.setFont("Helvetica-Bold", 6)
        c.setFillColor(COLOUR_LABEL)
        c.drawCentredString(cx, cy, panel.label)

        # Hole marks
        c.setStrokeColor(COLOUR_HOLE_MARK)
        c.setLineWidth(0.8)
        for hole in panel.holes:
            wall_pos = hole_to_wall(
                hole.x_mm, hole.y_mm,
                panel.x_mm, panel.y_mm,
                panel.width_mm, panel.height_mm,
                panel.rotation_deg,
            )
            hx, hy = to_ref_pdf(wall_pos)
            _draw_cross(c, hx, hy, size_pt=4.0)
            drill_rows.append({
                "panel": panel.label,
                "hole": hole.label,
                "wall_x": f"{wall_pos.x_mm:.1f}",
                "wall_y": f"{wall_pos.y_mm:.1f}",
                "panel_local_x": f"{hole.x_mm:.1f}",
                "panel_local_y": f"{hole.y_mm:.1f}",
            })

    # Title
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.black)
    c.drawString(_mm(margin_mm), page_h_pt - _mm(margin_mm - 5), f"Reference Sheet - {layout.job_title}")
    c.setFont("Helvetica", 8)
    c.drawString(_mm(margin_mm), page_h_pt - _mm(margin_mm + 3),
                 f"Wall: {layout.wall_width_mm:.0f} × {layout.wall_height_mm:.0f} mm  |  Scale 1:{1/scale:.0f}")

    # Drill-point table
    _draw_drill_table(c, drill_rows, margin_mm, table_height_mm, page_h_pt, A3_W_MM)

    c.save()
    return buf.getvalue()


def _draw_drill_table(
    c: rl_canvas.Canvas,
    rows: List[dict],
    margin_mm: float,
    table_h_mm: float,
    page_h_pt: float,
    page_w_mm: float,
):
    """Draw the drill-point reference table at the bottom of the reference sheet."""
    headers = ["Panel", "Hole", "Wall X (mm)", "Wall Y (mm)", "Panel-local X", "Panel-local Y"]
    col_widths_mm = [35, 35, 30, 30, 30, 30]
    col_widths_pt = [_mm(w) for w in col_widths_mm]

    table_top_y = page_h_pt - _mm(page_w_mm) + _mm(table_h_mm - 5)  # rough placement
    # Actually position at bottom
    y = _mm(margin_mm + table_h_mm - 5)
    x = _mm(margin_mm)
    row_h = _mm(5)

    c.setStrokeColor(colors.HexColor("#CCCCCC"))
    c.setLineWidth(0.3)

    # Header
    c.setFillColor(colors.HexColor("#EEEEEE"))
    c.rect(x, y, sum(col_widths_pt), row_h, stroke=1, fill=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 7)
    cx = x
    for h, cw in zip(headers, col_widths_pt):
        c.drawString(cx + _mm(1), y + _mm(1.2), h)
        cx += cw
    y -= row_h

    c.setFont("Helvetica", 7)
    for row in rows:
        if y < _mm(margin_mm):
            break
        c.setFillColor(colors.white)
        c.rect(x, y, sum(col_widths_pt), row_h, stroke=1, fill=1)
        c.setFillColor(colors.black)
        cx = x
        for val, cw in zip(
            [row["panel"], row["hole"], row["wall_x"], row["wall_y"],
             row["panel_local_x"], row["panel_local_y"]],
            col_widths_pt,
        ):
            c.drawString(cx + _mm(1), y + _mm(1.2), str(val))
            cx += cw
        y -= row_h
