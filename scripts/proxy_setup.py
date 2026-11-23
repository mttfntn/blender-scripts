"""Add the PROXY_Setup Geometry Nodes modifier to every selected mesh.

In the viewport it merges vertices closer than DISTANCE (a lighter
preview); renders use the full mesh. If the PROXY_Setup node group already
exists it is reused, and meshes that already have it are skipped.

Paste in Blender's Text Editor and press Run Script (Alt+P).
"""

import bpy

GROUP_NAME = "PROXY_Setup"
DISTANCE = 0.01


def build_group():
    """Create the PROXY_Setup node group.

    In the viewport the mesh goes through Merge by Distance; at render time
    the Is Viewport switch passes the original geometry through unchanged.
    """
    group = bpy.data.node_groups.new(GROUP_NAME, 'GeometryNodeTree')
    group.is_modifier = True

    iface = group.interface
    iface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    dist = iface.new_socket("Distance", in_out='INPUT', socket_type='NodeSocketFloat')
    dist.default_value = DISTANCE
    dist.min_value = 0.0
    dist.subtype = 'DISTANCE'
    iface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    nodes, links = group.nodes, group.links

    n_in = nodes.new('NodeGroupInput')
    n_in.location = (-400, 0)

    n_merge = nodes.new('GeometryNodeMergeByDistance')
    n_merge.location = (-150, -100)
    n_merge.inputs["Mode"].default_value = 'All'

    n_view = nodes.new('GeometryNodeIsViewport')
    n_view.location = (-150, 150)

    n_switch = nodes.new('GeometryNodeSwitch')
    n_switch.location = (100, 50)
    n_switch.input_type = 'GEOMETRY'

    n_out = nodes.new('NodeGroupOutput')
    n_out.location = (350, 50)

    links.new(n_in.outputs["Geometry"], n_merge.inputs["Geometry"])
    links.new(n_in.outputs["Distance"], n_merge.inputs["Distance"])
    links.new(n_in.outputs["Geometry"], n_switch.inputs["False"])
    links.new(n_merge.outputs["Geometry"], n_switch.inputs["True"])
    links.new(n_view.outputs["Is Viewport"], n_switch.inputs["Switch"])
    links.new(n_switch.outputs["Output"], n_out.inputs["Geometry"])
    return group


group = bpy.data.node_groups.get(GROUP_NAME)
if group is None or group.bl_idname != 'GeometryNodeTree':
    group = build_group()

added = 0
for obj in bpy.context.selected_objects:
    if obj.type != 'MESH':
        continue
    if any(m.type == 'NODES' and m.node_group == group for m in obj.modifiers):
        continue
    mod = obj.modifiers.new(GROUP_NAME, 'NODES')
    mod.node_group = group
    added += 1

print(f"PROXY_Setup added to {added} object(s)")
