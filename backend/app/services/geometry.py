"""
Geometry module: all coordinate transforms for the panel/hole system.

Rules:
- Everything is in millimetres.
- Panel x_mm, y_mm is the top-left corner in wall coordinates.
- Hole x_mm, y_mm is relative to the panel's own top-left (panel-local coords).
- Rotation is clockwise in degrees, about the panel's centre.
- PDF uses ReportLab points: 1 pt = 25.4/72 mm  →  1 mm = 72/25.4 pt ≈ 2.8346 pt
- Page origin in ReportLab is bottom-left; we flip y when converting to PDF coords.
"""

import math
from dataclasses import dataclass
from typing import NamedTuple

MM_TO_PT: float = 72.0 / 25.4  # exact: 1 mm = 72/25.4 pt


@dataclass(frozen=True)
class Point:
    x_mm: float
    y_mm: float

    def __add__(self, other: "Point") -> "Point":
        return Point(self.x_mm + other.x_mm, self.y_mm + other.y_mm)

    def __sub__(self, other: "Point") -> "Point":
        return Point(self.x_mm - other.x_mm, self.y_mm - other.y_mm)


class PdfPoint(NamedTuple):
    x_pt: float
    y_pt: float  # ReportLab bottom-left origin


def rotate_point_about(point: Point, origin: Point, angle_deg: float) -> Point:
    """
    Rotate `point` clockwise by `angle_deg` degrees about `origin`.

    Clockwise rotation matrix for angle θ:
        x' = cos θ · dx + sin θ · dy
        y' = -sin θ · dx + cos θ · dy
    where (dx, dy) = point - origin, and y increases downward (screen/wall coords).
    """
    angle_rad = math.radians(angle_deg)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    dx = point.x_mm - origin.x_mm
    dy = point.y_mm - origin.y_mm
    return Point(
        x_mm=origin.x_mm + cos_a * dx + sin_a * dy,
        y_mm=origin.y_mm + (-sin_a) * dx + cos_a * dy,
    )


def panel_center(panel_x_mm: float, panel_y_mm: float,
                 panel_w_mm: float, panel_h_mm: float) -> Point:
    return Point(panel_x_mm + panel_w_mm / 2.0, panel_y_mm + panel_h_mm / 2.0)


def hole_to_wall(
    hole_x_mm: float,
    hole_y_mm: float,
    panel_x_mm: float,
    panel_y_mm: float,
    panel_w_mm: float,
    panel_h_mm: float,
    rotation_deg: float,
) -> Point:
    """
    Transform a hole from panel-local coordinates to wall coordinates.

    Steps:
    1. Translate hole from panel-local to wall (unrotated).
    2. Rotate about the panel centre.
    """
    hole_unrotated = Point(panel_x_mm + hole_x_mm, panel_y_mm + hole_y_mm)
    centre = panel_center(panel_x_mm, panel_y_mm, panel_w_mm, panel_h_mm)
    return rotate_point_about(hole_unrotated, centre, rotation_deg)


def wall_to_pdf(wall_pt: Point, wall_height_mm: float) -> PdfPoint:
    """
    Convert wall coords (origin top-left, y down) to ReportLab PDF coords
    (origin bottom-left, y up) for a page that spans the full wall height.

    PDF x = wall x * MM_TO_PT
    PDF y = (wall_height_mm - wall y) * MM_TO_PT   (flip y axis)
    """
    return PdfPoint(
        x_pt=wall_pt.x_mm * MM_TO_PT,
        y_pt=(wall_height_mm - wall_pt.y_mm) * MM_TO_PT,
    )


def wall_to_tile_pdf(
    wall_pt: Point,
    tile_origin_x_mm: float,
    tile_origin_y_mm: float,
    tile_height_mm: float,
) -> PdfPoint:
    """
    Convert a wall coordinate to PDF coords within a single tile page.

    tile_origin_x_mm, tile_origin_y_mm: top-left corner of this tile in wall coords.
    tile_height_mm: height of the tile page (e.g. 297 for A4).
    """
    local_x = wall_pt.x_mm - tile_origin_x_mm
    local_y = wall_pt.y_mm - tile_origin_y_mm
    return PdfPoint(
        x_pt=local_x * MM_TO_PT,
        y_pt=(tile_height_mm - local_y) * MM_TO_PT,
    )


def fallback_hole(panel_w_mm: float, panel_h_mm: float) -> Point:
    """
    Default hole when a canvas size has no configured holes:
    centred horizontally, 50 mm from the top edge.
    """
    return Point(x_mm=panel_w_mm / 2.0, y_mm=50.0)
