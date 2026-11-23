# SPDX-License-Identifier: GPL-3.0-or-later
"""Roll the 3D Viewport around the axis pointing out of the screen.

Run from Blender's Text Editor. Change ANGLE_DEGREES to roll by another amount.
"""

import math

import bpy

# Use a negative value to turn the other way.
ANGLE_DEGREES = 90


def find_view3d(window):
    """Return the first 3D Viewport area and its main region, or (None, None)."""
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            for region in area.regions:
                if region.type == 'WINDOW':
                    return area, region
    return None, None


def show_message(message):
    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title="Rotate View", icon='ERROR')


def rotate_view(degrees=ANGLE_DEGREES):
    """Roll the first 3D Viewport in the current window by `degrees`."""
    window = bpy.context.window
    area, region = find_view3d(window)
    if area is None:
        show_message("No 3D Viewport is open in this window.")
        return

    with bpy.context.temp_override(window=window, area=area, region=region):
        bpy.ops.view3d.view_roll(angle=math.radians(degrees), type='ANGLE')


if __name__ == "__main__":
    rotate_view()
