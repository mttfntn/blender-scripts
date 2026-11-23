"""Simple Deform (Twist / Bend / Taper / Stretch) rebuilt in Geometry Nodes,
with a falloff controlled by two empties on the deform axis.

Run from Blender's Text Editor (Run Script) with a mesh object active.
It builds a "GN Simple Deform" node group, adds it as a modifier and creates:

  * SD_Origin       -> pivot and orientation of the deform (like the Simple
                       Deform modifier's "Origin"). Rotate it to tilt the axis.
  * SD_Falloff_A    -> where the deform starts. Below it the mesh is untouched.
  * SD_Falloff_B    -> where the deform reaches full strength. Past it the
                       deformed shape carries on rigidly.

A and B are rings parented to SD_Origin and locked so they only slide along
the deform axis. The point halfway between them is the middle of the falloff;
moving them apart makes the transition softer, closer makes it sharper.
The "Falloff Shape" Float Curve node (Geometry Nodes editor) sets how the
transition eases in and out for Twist, Taper and Stretch. Bend always bends
evenly between A and B so the mesh keeps its length.

Modifier panel: Mode, Axis, Angle (Twist/Bend), Factor (Taper/Stretch),
Origin, Use Falloff (off = deform across the whole mesh), Falloff Start/End,
Invert (swap A and B). The falloff value is stored as a "falloff" point
attribute for use in materials or the Spreadsheet.
"""

import math

import bpy
from mathutils import Matrix, Vector

GROUP_NAME = "GN Simple Deform"
MODES = ("Twist", "Bend", "Taper", "Stretch")
AXES = ("X", "Y", "Z")


# --- Node tree building helpers ---------------------------------------------

class TreeBuilder:
    """Small helper to create and wire nodes with little boilerplate."""

    def __init__(self, ng):
        self.ng = ng
        self.column_x = 0
        self.row = 0

    def column(self, x):
        self.column_x = x
        self.row = 0

    def node(self, node_type, label=None, **props):
        node = self.ng.nodes.new(node_type)
        node.location = (self.column_x + (self.row // 8) * 200, -(self.row % 8) * 160)
        self.row += 1
        if label:
            node.label = label
        for key, value in props.items():
            setattr(node, key, value)
        return node

    def set(self, socket, value):
        if isinstance(value, bpy.types.NodeSocket):
            self.ng.links.new(value, socket)
        else:
            socket.default_value = value

    def math(self, operation, a, b=0.0, c=None, label=None, clamp=False):
        node = self.node('ShaderNodeMath', label, operation=operation, use_clamp=clamp)
        self.set(node.inputs[0], a)
        self.set(node.inputs[1], b)
        if c is not None:
            self.set(node.inputs[2], c)
        return node.outputs[0]

    def separate(self, vector):
        node = self.node('ShaderNodeSeparateXYZ')
        self.set(node.inputs[0], vector)
        return node.outputs["X"], node.outputs["Y"], node.outputs["Z"]

    def combine(self, x, y, z, label=None):
        node = self.node('ShaderNodeCombineXYZ', label)
        for socket, value in zip(node.inputs, (x, y, z)):
            self.set(socket, value)
        return node.outputs[0]

    def add_vectors(self, a, b, label=None):
        node = self.node('ShaderNodeVectorMath', label, operation='ADD')
        self.set(node.inputs[0], a)
        self.set(node.inputs[1], b)
        return node.outputs["Vector"]

    def rotate(self, vector, center, angle, axis, label=None):
        node = self.node('ShaderNodeVectorRotate', label, rotation_type=f'{axis}_AXIS')
        self.set(node.inputs["Vector"], vector)
        self.set(node.inputs["Center"], center)
        self.set(node.inputs["Angle"], angle)
        return node.outputs["Vector"]

    def switch(self, input_type, condition, false, true, label=None):
        node = self.node('GeometryNodeSwitch', label, input_type=input_type)
        self.set(node.inputs["Switch"], condition)
        self.set(node.inputs["False"], false)
        self.set(node.inputs["True"], true)
        return node.outputs["Output"]

    def index_switch(self, data_type, index, values, label=None):
        node = self.node('GeometryNodeIndexSwitch', label, data_type=data_type)
        while len(node.index_switch_items) < len(values):
            node.index_switch_items.new()
        self.set(node.inputs[0], index)
        for socket, value in zip(node.inputs[1:], values):
            self.set(socket, value)
        return node.outputs[0]

    def menu_index(self, menu_socket, names, label=None):
        """Menu Switch that turns a dropdown into an index (0, 1, 2...)."""
        node = self.node('GeometryNodeMenuSwitch', label, data_type='INT')
        node.enum_items.clear()
        for name in names:
            node.enum_items.new(name)
        self.set(node.inputs["Menu"], menu_socket)
        for i, name in enumerate(names):
            node.inputs[name].default_value = i
        return node.outputs["Output"]


def _new_input(ng, name, socket_type, default=None, subtype=None, description="", parent=None):
    """Add a modifier input socket to the node group's interface."""
    sock = ng.interface.new_socket(name, in_out='INPUT', socket_type=socket_type,
                                   description=description, parent=parent)
    if default is not None and socket_type != 'NodeSocketMenu':
        sock.default_value = default
    if subtype is not None:
        sock.subtype = subtype
    return sock


def build_node_group():
    """Create the "GN Simple Deform" node group.

    Data flow: object positions -> Origin space -> axis space (chosen axis
    becomes local Z) -> falloff 0..1 between the two empties -> one of the
    four deforms -> back to object space -> Set Position.
    """
    ng = bpy.data.node_groups.new(GROUP_NAME, 'GeometryNodeTree')
    ng.is_modifier = True

    # --- Modifier inputs ----------------------------------------------------
    _new_input(ng, "Geometry", 'NodeSocketGeometry')
    deform_panel = ng.interface.new_panel("Deform")
    mode_sock = _new_input(ng, "Mode", 'NodeSocketMenu', parent=deform_panel)
    axis_sock = _new_input(ng, "Axis", 'NodeSocketMenu', parent=deform_panel,
                           description="Axis the deform runs along")
    _new_input(ng, "Angle", 'NodeSocketFloat', math.radians(90.0), subtype='ANGLE', parent=deform_panel,
               description="Total twist/bend angle between the falloff empties")
    _new_input(ng, "Factor", 'NodeSocketFloat', 0.5, parent=deform_panel,
               description="Amount for Taper and Stretch")
    _new_input(ng, "Origin", 'NodeSocketObject', parent=deform_panel,
               description="Pivot and orientation of the deform")
    falloff_panel = ng.interface.new_panel("Falloff")
    _new_input(ng, "Use Falloff", 'NodeSocketBool', True, parent=falloff_panel,
               description="Off: deform evenly across the whole mesh")
    _new_input(ng, "Falloff Start", 'NodeSocketObject', parent=falloff_panel,
               description="Empty where the deform starts")
    _new_input(ng, "Falloff End", 'NodeSocketObject', parent=falloff_panel,
               description="Empty where the deform reaches full strength")
    _new_input(ng, "Invert", 'NodeSocketBool', False, parent=falloff_panel,
               description="Swap start and end")
    ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    b = TreeBuilder(ng)
    b.column(-2200)
    gi = b.node('NodeGroupInput')
    mode = b.menu_index(gi.outputs["Mode"], MODES, "Mode")
    axis = b.menu_index(gi.outputs["Axis"], AXES, "Axis")
    mode_sock.default_value = "Twist"
    mode_sock.menu_expanded = True
    axis_sock.default_value = "Z"
    axis_sock.menu_expanded = True

    def to_axis_space(vector):
        # Cyclic swizzle so the chosen axis becomes local Z.
        x, y, z = b.separate(vector)
        return b.index_switch('VECTOR', axis, [b.combine(y, z, x), b.combine(z, x, y), vector], "To Axis Space")

    def from_axis_space(vector):
        x, y, z = b.separate(vector)
        return b.index_switch('VECTOR', axis, [b.combine(z, x, y), b.combine(y, z, x), vector], "From Axis Space")

    # --- Positions in origin / axis space -------------------------------------
    b.column(-1900)
    origin = b.node('GeometryNodeObjectInfo', "Origin", transform_space='RELATIVE')
    b.set(origin.inputs["Object"], gi.outputs["Origin"])
    invert_matrix = b.node('FunctionNodeInvertMatrix')
    b.set(invert_matrix.inputs[0], origin.outputs["Transform"])
    to_origin = invert_matrix.outputs["Matrix"]

    def to_local(point):
        node = b.node('FunctionNodeTransformPoint')
        b.set(node.inputs["Vector"], point)
        b.set(node.inputs["Transform"], to_origin)
        return to_axis_space(node.outputs["Vector"])

    position = b.node('GeometryNodeInputPosition').outputs["Position"]
    b.column(-1600)
    local = to_local(position)
    x, y, z = b.separate(local)

    # --- Falloff range a..b along the axis ------------------------------------
    b.column(-1300)
    start = b.node('GeometryNodeObjectInfo', "Falloff Start", transform_space='RELATIVE')
    b.set(start.inputs["Object"], gi.outputs["Falloff Start"])
    end = b.node('GeometryNodeObjectInfo', "Falloff End", transform_space='RELATIVE')
    b.set(end.inputs["Object"], gi.outputs["Falloff End"])
    start_z = b.separate(to_local(start.outputs["Location"]))[2]
    end_z = b.separate(to_local(end.outputs["Location"]))[2]

    b.column(-1000)
    bounds = b.node('GeometryNodeAttributeStatistic', "Mesh Extent", data_type='FLOAT', domain='POINT')
    b.set(bounds.inputs["Geometry"], gi.outputs["Geometry"])
    b.set(bounds.inputs["Attribute"], z)
    range_a = b.switch('FLOAT', gi.outputs["Use Falloff"], bounds.outputs["Min"], start_z)
    range_b = b.switch('FLOAT', gi.outputs["Use Falloff"], bounds.outputs["Max"], end_z)
    lo = b.switch('FLOAT', gi.outputs["Invert"], range_a, range_b, "Start")
    hi = b.switch('FLOAT', gi.outputs["Invert"], range_b, range_a, "End")
    length = b.math('SUBTRACT', hi, lo, label="Length")

    b.column(-700)
    t = b.math('DIVIDE', b.math('SUBTRACT', z, lo), length, label="Falloff 0..1", clamp=True)
    curve = b.node('ShaderNodeFloatCurve', "Falloff Shape")
    curve.location = (-700, 400)
    points = curve.mapping.curves[0].points
    points[0].location = (0.0, 0.0)
    points[1].location = (1.0, 1.0)
    points.new(0.3, 0.08)
    points.new(0.7, 0.92)
    for point in points:
        point.handle_type = 'AUTO'
    curve.mapping.update()
    b.set(curve.inputs["Value"], t)
    falloff = b.switch('FLOAT', gi.outputs["Use Falloff"], t, curve.outputs["Value"], "Falloff")

    # --- Deform modes (in axis space, deform axis = local Z) ------------------
    angle = gi.outputs["Angle"]
    factor = gi.outputs["Factor"]

    b.column(-400)
    twisted = b.rotate(local, (0.0, 0.0, 0.0), b.math('MULTIPLY', angle, falloff), 'Z', "Twist")

    # Bend: the part between start and end wraps around a circle of radius
    # length/angle; the part past the end continues straight along the tangent.
    b.column(-100)
    near_zero = b.math('COMPARE', angle, 0.0, 1e-4)
    safe_angle = b.math('MULTIPLY_ADD', near_zero, 1e-3, angle, label="Safe Angle")
    radius = b.math('DIVIDE', length, safe_angle, label="Bend Radius")
    bend_angle = b.math('MULTIPLY', angle, t)
    along = b.math('MULTIPLY', t, length)
    remainder = b.math('SUBTRACT', b.math('SUBTRACT', z, lo), along, label="Past End")
    b.column(100)
    on_arc = b.rotate(b.combine(x, y, lo), b.combine(radius, 0.0, lo), bend_angle, 'Y', "Bend Arc")
    tangent = b.rotate(b.combine(0.0, 0.0, remainder), (0.0, 0.0, 0.0), bend_angle, 'Y', "Bend Tangent")
    bent = b.add_vectors(on_arc, tangent, "Bend")

    b.column(300)
    taper = b.math('MULTIPLY_ADD', factor, falloff, 1.0, label="Taper Scale")
    tapered = b.combine(b.math('MULTIPLY', x, taper), b.math('MULTIPLY', y, taper), z, "Taper")

    stretch = b.math('MAXIMUM', b.math('MULTIPLY_ADD', factor, falloff, 1.0), 0.01)
    thin = b.math('POWER', stretch, -0.5, label="Keep Volume")
    stretched_z = b.math('ADD', z, b.math('MULTIPLY', b.math('MULTIPLY', factor, length), falloff))
    b.column(500)
    stretched = b.combine(b.math('MULTIPLY', x, thin), b.math('MULTIPLY', y, thin), stretched_z, "Stretch")

    deformed = b.index_switch('VECTOR', mode, [twisted, bent, tapered, stretched], "Mode")

    # --- Back to object space and apply ---------------------------------------
    b.column(800)
    back = b.node('FunctionNodeTransformPoint')
    b.set(back.inputs["Vector"], from_axis_space(deformed))
    b.set(back.inputs["Transform"], origin.outputs["Transform"])

    b.column(1100)
    store = b.node('GeometryNodeStoreNamedAttribute', "Store Falloff", data_type='FLOAT', domain='POINT')
    b.set(store.inputs["Geometry"], gi.outputs["Geometry"])
    b.set(store.inputs["Name"], "falloff")
    b.set(store.inputs["Value"], falloff)
    set_pos = b.node('GeometryNodeSetPosition')
    b.set(set_pos.inputs["Geometry"], store.outputs["Geometry"])
    b.set(set_pos.inputs["Position"], back.outputs["Vector"])
    go = b.node('NodeGroupOutput')
    b.set(go.inputs["Geometry"], set_pos.outputs["Geometry"])

    return ng


def get_node_group():
    """Return the existing node group, or build it on the first run."""
    ng = bpy.data.node_groups.get(GROUP_NAME)
    if ng is None or ng.bl_idname != 'GeometryNodeTree':
        ng = build_node_group()
    return ng


# --- Modifier input access ----------------------------------------------------

def _set_input(mod, name, value):
    """Set the modifier input called `name` (the panel label) to `value`."""
    # Blender 5.2+ exposes inputs as mod.properties.inputs.<identifier>.value;
    # the old mod["Socket_N"] = value form raises TypeError there.
    for item in mod.node_group.interface.items_tree:
        if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.name == name:
            getattr(mod.properties.inputs, item.identifier).value = value
            return
    raise KeyError(name)


# --- Operator -----------------------------------------------------------------

def _new_empty(context, name, display_type, size, parent=None, location=(0.0, 0.0, 0.0)):
    """Create an empty in the active collection."""
    empty = bpy.data.objects.new(name, None)
    empty.empty_display_type = display_type
    empty.empty_display_size = size
    empty.parent = parent
    empty.location = location
    context.collection.objects.link(empty)
    return empty


class OBJECT_OT_add_gn_simple_deform(bpy.types.Operator):
    """Add a Geometry Nodes Simple Deform with two falloff empties"""

    bl_idname = "object.add_gn_simple_deform"
    bl_label = "Add GN Simple Deform"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return context.mode == 'OBJECT' and obj is not None and obj.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        ng = get_node_group()

        # Origin sits at the object's origin with its rotation (no scale).
        loc, rot, _scale = obj.matrix_world.decompose()
        origin_matrix = Matrix.LocRotScale(loc, rot, Vector((1.0, 1.0, 1.0)))
        to_origin = origin_matrix.inverted() @ obj.matrix_world
        points = [to_origin @ v.co for v in obj.data.vertices] or [Vector()]
        z_min = min(p.z for p in points)
        z_max = max(p.z for p in points)
        width = max(max(abs(p.x), abs(p.y)) for p in points)
        ring_size = max(width * 1.25, 0.1)

        origin = _new_empty(context, "SD_Origin", 'ARROWS', ring_size * 0.5)
        origin.matrix_world = origin_matrix
        start = _new_empty(context, "SD_Falloff_A", 'CIRCLE', ring_size, origin, (0.0, 0.0, z_min))
        end = _new_empty(context, "SD_Falloff_B", 'CIRCLE', ring_size, origin, (0.0, 0.0, z_max))
        for empty in (start, end):
            # Circle empties lie in local XY, i.e. as rings around the Z axis.
            empty.lock_location = (True, True, False)

        mod = obj.modifiers.new(GROUP_NAME, 'NODES')
        mod.node_group = ng
        _set_input(mod, "Origin", origin)
        _set_input(mod, "Falloff Start", start)
        _set_input(mod, "Falloff End", end)
        obj.update_tag()

        # Select the end ring so it can be moved (G Z) right away.
        for other in context.selected_objects:
            other.select_set(False)
        end.select_set(True)
        context.view_layer.objects.active = end
        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(OBJECT_OT_add_gn_simple_deform.bl_idname, icon='MOD_SIMPLEDEFORM')


def register():
    bpy.utils.register_class(OBJECT_OT_add_gn_simple_deform)
    bpy.types.VIEW3D_MT_object.append(menu_func)


def unregister():
    bpy.types.VIEW3D_MT_object.remove(menu_func)
    bpy.utils.unregister_class(OBJECT_OT_add_gn_simple_deform)


def _cleanup_previous_run():
    """Remove what an earlier run of this script registered, so it can be re-run."""
    menu = bpy.types.VIEW3D_MT_object
    for func in list(menu._dyn_ui_initialize()):
        if getattr(func, "__name__", "") == "menu_func" and func.__module__ == __name__:
            menu.remove(func)
    old_cls = getattr(bpy.types, OBJECT_OT_add_gn_simple_deform.__name__, None)
    if old_cls is not None:
        bpy.utils.unregister_class(old_cls)


if __name__ == "__main__":
    _cleanup_previous_run()
    register()
    if bpy.ops.object.add_gn_simple_deform.poll():
        bpy.ops.object.add_gn_simple_deform()
