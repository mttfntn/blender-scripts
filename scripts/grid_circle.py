# SPDX-License-Identifier: GPL-3.0-or-later
"""Add a "Grid Circle" mesh primitive: a flat disc filled with clean quads.

A square grid is warped into a disc, so every face is a quad and the mesh
subdivides nicely (the classic "grid fill" circle topology).

Run from Blender's Text Editor (Run Script). It adds one Grid Circle at the
3D cursor and registers nothing. Change the settings below to get another
size or density.
"""

import math

import bmesh
import bpy
from bpy_extras.object_utils import object_data_add

# Settings. Edit these, then run the script again.
SUBDIVISIONS = 8   # quads across the disc (1 or more)
RADIUS = 1.0
ROUNDNESS = 1.0    # 0 = square grid, 1 = full circle


def square_to_disc(x, y):
    """Map a point of the [-1, 1] square onto the unit disc (elliptical mapping)."""
    return (
        x * math.sqrt(1.0 - y * y / 2.0),
        y * math.sqrt(1.0 - x * x / 2.0),
    )


def build_grid_circle(radius, subdivisions, roundness):
    """Return a new mesh: a subdivisions x subdivisions quad grid warped into a disc."""
    bm = bmesh.new()
    n = subdivisions
    verts = []
    for j in range(n + 1):
        row = []
        y = -1.0 + 2.0 * j / n
        for i in range(n + 1):
            x = -1.0 + 2.0 * i / n
            dx, dy = square_to_disc(x, y)
            px = (x + (dx - x) * roundness) * radius
            py = (y + (dy - y) * roundness) * radius
            row.append(bm.verts.new((px, py, 0.0)))
        verts.append(row)

    for j in range(n):
        for i in range(n):
            bm.faces.new((
                verts[j][i],
                verts[j][i + 1],
                verts[j + 1][i + 1],
                verts[j + 1][i],
            ))

    mesh = bpy.data.meshes.new("GridCircle")
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def add_grid_circle(context, radius=RADIUS, subdivisions=SUBDIVISIONS, roundness=ROUNDNESS):
    """Add a Grid Circle object at the 3D cursor and return it."""
    mesh = build_grid_circle(radius, subdivisions, roundness)
    return object_data_add(context, mesh)


if __name__ == "__main__":
    obj = add_grid_circle(bpy.context)
    print(f"Added {obj.name}: {SUBDIVISIONS}x{SUBDIVISIONS} quads, radius {RADIUS}")
