# SPDX-License-Identifier: GPL-3.0-or-later
"""Rotate selected objects 90 degrees around their Z axis.

Run from Blender's Text Editor (Run Script). It registers the operator
"Rotate 90° Z" (Object > Transform, or F3 search) and runs it once on the
current selection. Angle and direction can be changed in the redo panel.
"""

import math

import bpy
from mathutils import Matrix


class OBJECT_OT_rotate_z_90(bpy.types.Operator):
    """Rotate selected objects around their own Z axis"""

    bl_idname = "object.rotate_z_90"
    bl_label = "Rotate 90° Z"
    bl_options = {'REGISTER', 'UNDO'}

    angle: bpy.props.FloatProperty(
        name="Angle",
        default=math.radians(90.0),
        subtype='ANGLE',
    )
    clockwise: bpy.props.BoolProperty(
        name="Clockwise",
        description="Rotate clockwise when looking down from +Z",
        default=False,
    )

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and bool(context.selected_objects)

    def execute(self, context):
        angle = -self.angle if self.clockwise else self.angle
        rot = Matrix.Rotation(angle, 4, 'Z')

        for obj in context.selected_objects:
            # Rotate in place around the object's origin, in world space, so
            # it works for any rotation mode and for parented objects.
            loc, quat, scale = obj.matrix_world.decompose()
            new_quat = (rot.to_quaternion() @ quat)
            obj.matrix_world = Matrix.LocRotScale(loc, new_quat, scale)

        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(OBJECT_OT_rotate_z_90.bl_idname)


def register():
    bpy.utils.register_class(OBJECT_OT_rotate_z_90)
    bpy.types.VIEW3D_MT_transform_object.append(menu_func)


def unregister():
    bpy.types.VIEW3D_MT_transform_object.remove(menu_func)
    bpy.utils.unregister_class(OBJECT_OT_rotate_z_90)


def _cleanup_previous_run():
    """Remove what an earlier run of this script registered, so it can be re-run."""
    menu = bpy.types.VIEW3D_MT_transform_object
    for func in list(menu._dyn_ui_initialize()):
        if getattr(func, "__name__", "") == "menu_func" and func.__module__ == __name__:
            menu.remove(func)
    old_cls = getattr(bpy.types, OBJECT_OT_rotate_z_90.__name__, None)
    if old_cls is not None:
        bpy.utils.unregister_class(old_cls)


if __name__ == "__main__":
    _cleanup_previous_run()
    register()
    if bpy.ops.object.rotate_z_90.poll():
        bpy.ops.object.rotate_z_90()
