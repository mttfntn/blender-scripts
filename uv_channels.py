"""Set up two UV channels on the selected mesh objects.

  * Channel 1: the current first UV map, renamed to UV_Materials.
  * Channel 2: UV_Graphics, a new UV map starting as a copy of channel 1.

Objects without any UV map get both channels, unwrapped with a default
layout. Objects that already have the names are left as they are, so the
script is safe to run more than once.

Run from Blender's Text Editor (Run Script). It registers "Setup UV Channels"
(Object menu, or F3 search) and runs it once on the selection.
"""

import bpy

# Names of the two UV channels. Edit these to use other names.
MATERIALS_UV = "UV_Materials"
GRAPHICS_UV = "UV_Graphics"


def setup_uv_channels(mesh):
    uv_layers = mesh.uv_layers
    if len(uv_layers) == 0:
        uv_layers.new(name=MATERIALS_UV)
    elif MATERIALS_UV not in uv_layers:
        uv_layers[0].name = MATERIALS_UV

    if GRAPHICS_UV not in uv_layers:
        uv_layers.new(name=GRAPHICS_UV, do_init=False)
        # Look both up again: adding a layer can invalidate older references.
        source, graphics = uv_layers[MATERIALS_UV], uv_layers[GRAPHICS_UV]
        for src, dst in zip(source.uv, graphics.uv):
            dst.vector = src.vector

    # Channel 1 stays the one used for rendering and editing.
    uv_layers.active = uv_layers[MATERIALS_UV]
    uv_layers[MATERIALS_UV].active_render = True


class OBJECT_OT_setup_uv_channels(bpy.types.Operator):
    """Rename the first UV map to UV_Materials and add a UV_Graphics copy"""

    bl_idname = "object.setup_uv_channels"
    bl_label = "Setup UV Channels"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and any(o.type == 'MESH' for o in context.selected_objects)

    def execute(self, context):
        meshes = {o.data for o in context.selected_objects if o.type == 'MESH'}
        for mesh in meshes:
            setup_uv_channels(mesh)
        self.report({'INFO'}, f"UV channels set up on {len(meshes)} mesh(es)")
        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(OBJECT_OT_setup_uv_channels.bl_idname, icon='UV')


def register():
    bpy.utils.register_class(OBJECT_OT_setup_uv_channels)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    bpy.utils.unregister_class(OBJECT_OT_setup_uv_channels)


def _cleanup_previous_run():
    """Remove what an earlier run of this script registered, so it can be re-run."""
    menu = bpy.types.VIEW3D_MT_object
    for func in list(menu._dyn_ui_initialize()):
        if getattr(func, "__name__", "") == "menu_func" and func.__module__ == __name__:
            menu.remove(func)
    old_cls = getattr(bpy.types, OBJECT_OT_setup_uv_channels.__name__, None)
    if old_cls is not None:
        bpy.utils.unregister_class(old_cls)


if __name__ == "__main__":
    _cleanup_previous_run()
    register()
    if bpy.ops.object.setup_uv_channels.poll():
        bpy.ops.object.setup_uv_channels()
