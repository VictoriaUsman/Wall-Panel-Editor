"""
Unit tests for geometry.py — the most safety-critical module.

Every test uses exact mm values and asserts within 0.001 mm tolerance.
These tests must pass before any PDF is generated or template is printed.
"""
import math
import pytest
from app.services.geometry import (
    Point,
    PdfPoint,
    MM_TO_PT,
    rotate_point_about,
    hole_to_wall,
    wall_to_pdf,
    wall_to_tile_pdf,
    fallback_hole,
    panel_center,
)

TOL = 0.001  # mm tolerance for all assertions


def approx(a: float, b: float, tol: float = TOL) -> bool:
    return abs(a - b) <= tol


# ---------------------------------------------------------------------------
# MM_TO_PT constant
# ---------------------------------------------------------------------------

def test_mm_to_pt_exact():
    # 25.4 mm = 1 inch = 72 pt  →  1 mm = 72/25.4 pt
    assert abs(MM_TO_PT - 72.0 / 25.4) < 1e-10
    # 25.4 mm must equal exactly 72 pt
    assert abs(25.4 * MM_TO_PT - 72.0) < 1e-10


# ---------------------------------------------------------------------------
# rotate_point_about
# ---------------------------------------------------------------------------

def test_rotate_0_degrees():
    p = Point(10, 20)
    origin = Point(5, 5)
    result = rotate_point_about(p, origin, 0.0)
    assert approx(result.x_mm, 10.0)
    assert approx(result.y_mm, 20.0)


def test_rotate_360_degrees_is_identity():
    p = Point(100, 50)
    origin = Point(60, 30)
    result = rotate_point_about(p, origin, 360.0)
    assert approx(result.x_mm, 100.0)
    assert approx(result.y_mm, 50.0)


def test_rotate_90_clockwise():
    # Point at (1, 0) rotated 90° CW about origin → (0, -1)
    # In screen coords (y down): (1,0) rotated 90° CW about (0,0) → (0, 1)?
    # CW rotation in y-down coords:
    #   x' = cos(90)*dx + sin(90)*dy = 0*1 + 1*0 = 0
    #   y' = -sin(90)*dx + cos(90)*dy = -1*1 + 0*0 = -1
    # So (1,0) CW 90° about (0,0) in y-down → (0, -1)
    p = Point(1.0, 0.0)
    result = rotate_point_about(p, Point(0, 0), 90.0)
    assert approx(result.x_mm, 0.0)
    assert approx(result.y_mm, -1.0)


def test_rotate_180():
    p = Point(10.0, 0.0)
    origin = Point(5.0, 0.0)
    result = rotate_point_about(p, origin, 180.0)
    assert approx(result.x_mm, 0.0)
    assert approx(result.y_mm, 0.0)


def test_rotate_90_cw_y_down_sanity():
    """
    Panel at (0,0), size 200x100. Centre = (100, 50).
    Top-right corner (200, 0) rotated 90° CW about centre.
    Expected: centre + rotate((200-100, 0-50), 90°)
             = (100,50) + rotate((100,-50), 90°)
    rotate (dx,dy) 90 CW in y-down: x'=dx*cos+dy*sin, y'=-dx*sin+dy*cos
             = (100*0 + (-50)*1,  -(100)*1 + (-50)*0)
             = (-50, -100)
    Result = (100+(-50), 50+(-100)) = (50, -50)
    """
    panel_x, panel_y, pw, ph = 0.0, 0.0, 200.0, 100.0
    corner = Point(panel_x + pw, panel_y)  # top-right (200, 0)
    centre = panel_center(panel_x, panel_y, pw, ph)  # (100, 50)
    result = rotate_point_about(corner, centre, 90.0)
    assert approx(result.x_mm, 50.0)
    assert approx(result.y_mm, -50.0)


# ---------------------------------------------------------------------------
# hole_to_wall
# ---------------------------------------------------------------------------

def test_hole_to_wall_no_rotation():
    # Panel at (100, 200), size 400x300. Hole at (50, 30) from panel top-left.
    # Expected wall position: (150, 230) — pure translation, no rotation.
    result = hole_to_wall(
        hole_x_mm=50.0, hole_y_mm=30.0,
        panel_x_mm=100.0, panel_y_mm=200.0,
        panel_w_mm=400.0, panel_h_mm=300.0,
        rotation_deg=0.0,
    )
    assert approx(result.x_mm, 150.0)
    assert approx(result.y_mm, 230.0)


def test_hole_to_wall_180_rotation():
    """
    Panel at (0,0), 400x300. Hole at (50, 30).
    180° rotation about centre (200, 150).
    Hole unrotated at (50, 30).
    dx = 50-200 = -150, dy = 30-150 = -120
    180° CW: x' = cos180*dx + sin180*dy = -dx = 150
             y' = -sin180*dx + cos180*dy = -(-dy) = ... wait
    cos(180)=-1, sin(180)=0
    x' = -1*(-150) + 0*(-120) = 150
    y' = -0*(-150) + -1*(-120) = 120
    Result = (200+150, 150+120) = wait that's wrong

    Actually:
    x' = origin.x + cos*dx + sin*dy = 200 + (-1)(-150) + 0*(-120) = 200 + 150 = 350
    y' = origin.y + (-sin)*dx + cos*dy = 150 + 0*(-150) + (-1)*(-120) = 150 + 120 = 270

    So hole at (50,30) on 400x300 panel at (0,0) rotated 180° → wall pos (350, 270).
    Makes sense: 180° rotation mirrors the hole to (400-50, 300-30) = (350, 270).
    """
    result = hole_to_wall(
        hole_x_mm=50.0, hole_y_mm=30.0,
        panel_x_mm=0.0, panel_y_mm=0.0,
        panel_w_mm=400.0, panel_h_mm=300.0,
        rotation_deg=180.0,
    )
    assert approx(result.x_mm, 350.0)
    assert approx(result.y_mm, 270.0)


def test_hole_to_wall_90_rotation():
    """
    Panel at (0,0), 200x100. Hole at (10, 10).
    Centre = (100, 50).
    Hole unrotated in wall = (10, 10).
    dx = 10-100 = -90, dy = 10-50 = -40
    90° CW: x' = 100 + 0*(-90) + 1*(-40) = 60
            y' =  50 + -1*(-90) + 0*(-40) = 140
    """
    result = hole_to_wall(
        hole_x_mm=10.0, hole_y_mm=10.0,
        panel_x_mm=0.0, panel_y_mm=0.0,
        panel_w_mm=200.0, panel_h_mm=100.0,
        rotation_deg=90.0,
    )
    assert approx(result.x_mm, 60.0)
    assert approx(result.y_mm, 140.0)


def test_hole_at_panel_centre_is_invariant_under_rotation():
    """A hole at the panel centre stays at the panel centre under any rotation."""
    pw, ph = 300.0, 200.0
    px, py = 150.0, 100.0
    hole_x, hole_y = pw / 2, ph / 2  # panel-local centre

    for angle in [0, 30, 45, 90, 135, 180, 270, 360]:
        result = hole_to_wall(hole_x, hole_y, px, py, pw, ph, float(angle))
        expected_x = px + pw / 2
        expected_y = py + ph / 2
        assert approx(result.x_mm, expected_x), f"Failed at {angle}°: x={result.x_mm}"
        assert approx(result.y_mm, expected_y), f"Failed at {angle}°: y={result.y_mm}"


def test_hole_to_wall_panel_offset():
    """Panel not at origin. Hole must be offset by panel position before rotation."""
    result = hole_to_wall(
        hole_x_mm=0.0, hole_y_mm=0.0,   # top-left corner of panel
        panel_x_mm=500.0, panel_y_mm=300.0,
        panel_w_mm=200.0, panel_h_mm=100.0,
        rotation_deg=0.0,
    )
    assert approx(result.x_mm, 500.0)
    assert approx(result.y_mm, 300.0)


# ---------------------------------------------------------------------------
# wall_to_pdf (full-wall single-page)
# ---------------------------------------------------------------------------

def test_wall_to_pdf_origin():
    # Wall top-left (0,0) → PDF bottom-left of page (0, height*MM_TO_PT)
    pt = wall_to_pdf(Point(0.0, 0.0), wall_height_mm=1000.0)
    assert approx(pt.x_pt, 0.0)
    assert approx(pt.y_pt, 1000.0 * MM_TO_PT)


def test_wall_to_pdf_bottom_right():
    # Wall bottom-right (W, H) → PDF (W*MM_TO_PT, 0)
    W, H = 2000.0, 1500.0
    pt = wall_to_pdf(Point(W, H), wall_height_mm=H)
    assert approx(pt.x_pt, W * MM_TO_PT)
    assert approx(pt.y_pt, 0.0)


def test_wall_to_pdf_mm_to_pt_conversion():
    # 25.4 mm in x → 72 pt
    pt = wall_to_pdf(Point(25.4, 0.0), wall_height_mm=100.0)
    assert approx(pt.x_pt, 72.0)


# ---------------------------------------------------------------------------
# wall_to_tile_pdf
# ---------------------------------------------------------------------------

def test_tile_origin_maps_to_pdf_top_left():
    # Tile starting at (210, 297) in wall coords. That tile's own (0,0) in PDF
    # should map to (0, tile_height*MM_TO_PT).
    tile_h = 297.0
    pt = wall_to_tile_pdf(Point(210.0, 297.0), 210.0, 297.0, tile_h)
    assert approx(pt.x_pt, 0.0)
    assert approx(pt.y_pt, tile_h * MM_TO_PT)


def test_tile_local_coords_correct():
    # Wall point at (250, 350), tile origin (210, 297), tile height 297.
    # Local x = 40, local y = 53
    pt = wall_to_tile_pdf(Point(250.0, 350.0), 210.0, 297.0, 297.0)
    assert approx(pt.x_pt, 40.0 * MM_TO_PT)
    assert approx(pt.y_pt, (297.0 - 53.0) * MM_TO_PT)


# ---------------------------------------------------------------------------
# fallback_hole
# ---------------------------------------------------------------------------

def test_fallback_hole_centred():
    h = fallback_hole(400.0, 300.0)
    assert approx(h.x_mm, 200.0)
    assert approx(h.y_mm, 50.0)


def test_fallback_hole_50mm_from_top():
    for w, ht in [(200, 100), (600, 400), (100, 200)]:
        h = fallback_hole(float(w), float(ht))
        assert approx(h.y_mm, 50.0), f"y should be 50mm, got {h.y_mm}"


# ---------------------------------------------------------------------------
# Round-trip: hole → wall → tile PDF (integration path)
# ---------------------------------------------------------------------------

def test_full_pipeline_no_rotation():
    """
    Panel at (100, 200), 400x300. Hole at (200, 50).
    No rotation → wall pos = (300, 250).
    Tile origin (0, 0), tile h=297.
    PDF coords: x=300*MM_TO_PT, y=(297-250)*MM_TO_PT=47*MM_TO_PT.
    """
    wall_pos = hole_to_wall(200.0, 50.0, 100.0, 200.0, 400.0, 300.0, 0.0)
    assert approx(wall_pos.x_mm, 300.0)
    assert approx(wall_pos.y_mm, 250.0)

    pdf_pt = wall_to_tile_pdf(wall_pos, 0.0, 0.0, 297.0)
    assert approx(pdf_pt.x_pt, 300.0 * MM_TO_PT)
    assert approx(pdf_pt.y_pt, 47.0 * MM_TO_PT)


def test_full_pipeline_180_rotation():
    """
    Panel at (0,0), 400x300. Hole at (50, 30).
    180° → wall (350, 270) [verified above].
    Tile origin (0,0), tile h=297.
    PDF: x=350*MM_TO_PT, y=(297-270)*MM_TO_PT=27*MM_TO_PT.
    """
    wall_pos = hole_to_wall(50.0, 30.0, 0.0, 0.0, 400.0, 300.0, 180.0)
    pdf_pt = wall_to_tile_pdf(wall_pos, 0.0, 0.0, 297.0)
    assert approx(pdf_pt.x_pt, 350.0 * MM_TO_PT)
    assert approx(pdf_pt.y_pt, 27.0 * MM_TO_PT)


def test_2m_span_precision():
    """
    Across a 2000 mm span, MM_TO_PT * 2000 = 5669.29... pt.
    Two points 2000 mm apart must produce PDF coords with a gap of exactly
    2000 * MM_TO_PT points — no rounding error from intermediate steps.
    """
    p1 = wall_to_tile_pdf(Point(0.0, 0.0), 0.0, 0.0, 2000.0)
    p2 = wall_to_tile_pdf(Point(2000.0, 0.0), 0.0, 0.0, 2000.0)
    gap_pt = p2.x_pt - p1.x_pt
    expected = 2000.0 * MM_TO_PT
    # Must be within 0.001 pt — well within the ±2 mm tolerance
    assert abs(gap_pt - expected) < 0.001, f"Gap {gap_pt} pt ≠ {expected} pt"
