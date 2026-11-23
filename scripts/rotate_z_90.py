# SPDX-License-Identifier: GPL-3.0-or-later
"""Rotate selected objects 90 degrees around their Z axis.

Run from Blender's Text Editor (Run Script). It runs once on the current
selection and registers nothing. Change ANGLE_DEGREES and CLOCKWISE below
to rotate by another amount.
"""

import math

import bpy
from mathutils import Matrix

ANGLE_DEGREES = 90
CLOCKWISE = False  # True: clockwise when looking down from +Z


def rotate_objects(objects, angle_degrees=ANGLE_DEGREES, clockwise=CLOCKWISE):
    """Rotate each object around a Z axis through its own origin, in world space."""
    angle = math.radians(-angle_degrees if clockwise else angle_degrees)
    rot = Matrix.Rotation(angle, 4, 'Z').to_quaternion()
    for obj in objects:
        # Rebuild matrix_world so it works for any rotation mode and for
        # parented objects.
        loc, quat, scale = obj.matrix_world.decompose()
        obj.matrix_world = Matrix.LocRotScale(loc, rot @ quat, scale)


if __name__ == "__main__":
    if bpy.context.mode != 'OBJECT':
        print("Rotate Z: switch to Object Mode first")
    else:
        selected = bpy.context.selected_objects
        rotate_objects(selected)
        print(f"Rotated {len(selected)} object(s) by {ANGLE_DEGREES} degrees")
