"""Add a "Grid Circle" mesh primitive: a flat disc filled with clean quads.

A square grid is warped into a disc, so every face is a quad and the mesh
subdivides nicely (the classic "grid fill" circle topology).

Run from Blender's Text Editor (Run Script). It registers Add > Mesh >
Grid Circle and adds one at the 3D cursor. Tweak it in the redo panel.
"""

import math

import bmesh
import bpy
from bpy_extras.object_utils import AddObjectHelper, object_data_add

# Defaults shown in the redo panel. Edit these to change the starting values.
DEFAULT_SUBDIVISIONS = 8
DEFAULT_RADIUS = 1.0
DEFAULT_ROUNDNESS = 1.0


def square_to_disc(x, y):
    """Map a point of the [-1, 1] square onto the unit disc (elliptical mapping)."""
    return (
        x * math.sqrt(1.0 - y * y / 2.0),
        y * math.sqrt(1.0 - x * x / 2.0),
    )


def build_grid_circle(radius, subdivisions, roundness):
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


class MESH_OT_primitive_grid_circle_add(bpy.types.Operator, AddObjectHelper):
    """Add a disc made of a quad grid"""

    bl_idname = "mesh.primitive_grid_circle_add"
    bl_label = "Grid Circle"
    bl_options = {'REGISTER', 'UNDO'}

    radius: bpy.props.FloatProperty(
        name="Radius",
        default=DEFAULT_RADIUS,
        min=0.0001,
        subtype='DISTANCE',
        unit='LENGTH',
    )
    subdivisions: bpy.props.IntProperty(
        name="Subdivisions",
        description="Number of quads across the disc",
        default=DEFAULT_SUBDIVISIONS,
        min=1,
        max=512,
    )
    roundness: bpy.props.FloatProperty(
        name="Roundness",
        description="0 = square grid, 1 = full circle",
        default=DEFAULT_ROUNDNESS,
        min=0.0,
        max=1.0,
        subtype='FACTOR',
    )

    def execute(self, context):
        mesh = build_grid_circle(self.radius, self.subdivisions, self.roundness)
        object_data_add(context, mesh, operator=self)
        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(MESH_OT_primitive_grid_circle_add.bl_idname, icon='MESH_CIRCLE')


def register():
    bpy.utils.register_class(MESH_OT_primitive_grid_circle_add)
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)


def unregister():
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)
    bpy.utils.unregister_class(MESH_OT_primitive_grid_circle_add)


def _cleanup_previous_run():
    """Remove what an earlier run of this script registered, so it can be re-run."""
    menu = bpy.types.VIEW3D_MT_mesh_add
    for func in list(menu._dyn_ui_initialize()):
        if getattr(func, "__name__", "") == "menu_func" and func.__module__ == __name__:
            menu.remove(func)
    old_cls = getattr(bpy.types, MESH_OT_primitive_grid_circle_add.__name__, None)
    if old_cls is not None:
        bpy.utils.unregister_class(old_cls)


if __name__ == "__main__":
    _cleanup_previous_run()
    register()
    if bpy.ops.mesh.primitive_grid_circle_add.poll():
        bpy.ops.mesh.primitive_grid_circle_add()
