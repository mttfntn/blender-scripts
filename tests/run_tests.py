# SPDX-License-Identifier: GPL-3.0-or-later
"""Test suite for the scripts, run inside a background Blender.

Usage (from the repository root):

    blender -b --factory-startup --python tests/run_tests.py -- [--scripts DIR] [--json OUT]

Each script is run the way a user runs it (as "__main__", like Run Script in
the Text Editor), then its operator is called with a broad set of options.
Every test checks known-correct values and also records a fingerprint of the
resulting geometry. --json writes those fingerprints, so two versions of the
scripts can be compared (see tests/compare.py). Exit code 1 means a failure.
"""

import argparse
import hashlib
import json
import math
import os
import runpy
import sys
import traceback

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))

results = {}
failures = []


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--scripts", default=os.path.join(HERE, "..", "scripts"))
    parser.add_argument("--json", default=None)
    return parser.parse_args(argv)


ARGS = parse_args()


def run_script(name):
    runpy.run_path(os.path.join(ARGS.scripts, name), run_name="__main__")


def check(name, condition, detail=""):
    if not condition:
        failures.append(f"{name}: {detail}")
        print(f"  FAIL {name} {detail}")


def fingerprint(coords):
    """Short hash of a list of vectors, rounded so float noise doesn't count."""
    text = ";".join(f"{c[0]:.4f},{c[1]:.4f},{c[2]:.4f}" for c in coords)
    return hashlib.sha1(text.replace("-0.0000", "0.0000").encode()).hexdigest()[:12]


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def select_only(*objects):
    for obj in bpy.context.view_layer.objects:
        obj.select_set(obj in objects)
    bpy.context.view_layer.objects.active = objects[0] if objects else None


def evaluated_coords(obj):
    bpy.context.view_layer.update()
    mesh = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    return [v.co.copy() for v in mesh.vertices]


def make_bar(axis="Z", cuts=20):
    bpy.ops.mesh.primitive_cube_add()
    bar = bpy.context.active_object
    bar.scale = (0.3, 0.3, 2.0) if axis == "Z" else (2.0, 0.3, 0.3)
    bpy.ops.object.transform_apply(scale=True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.subdivide(number_cuts=cuts)
    bpy.ops.object.mode_set(mode='OBJECT')
    return bar


def menu_entries(menu):
    return [f for f in menu._dyn_ui_initialize() if getattr(f, "__name__", "") == "menu_func"]


# --- rotate_z_90.py ---------------------------------------------------------

def test_rotate_z_90():
    reset_scene()
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.context.active_object
    bpy.ops.object.empty_add(location=(2, 0, 0))
    child = bpy.context.active_object
    child.parent = cube
    child.rotation_mode = 'QUATERNION'
    select_only(cube)
    run_script("rotate_z_90.py")
    check("rotate_z_90 run", abs(math.degrees(cube.rotation_euler.z) - 90) < 1e-4,
          f"z={math.degrees(cube.rotation_euler.z)}")
    run_script("rotate_z_90.py")
    check("rotate_z_90 rerun menu", len(menu_entries(bpy.types.VIEW3D_MT_transform_object)) == 1)

    out = {}
    for angle in (90, 45, -30, 180):
        for clockwise in (False, True):
            for target in ("cube", "child"):
                obj = cube if target == "cube" else child
                select_only(obj)
                before = obj.matrix_world.copy()
                bpy.ops.object.rotate_z_90(angle=math.radians(angle), clockwise=clockwise)
                signed = -angle if clockwise else angle
                expected = Matrix.Translation(before.translation) @ Matrix.Rotation(math.radians(signed), 4, 'Z') \
                    @ Matrix.Translation(-before.translation) @ before
                diff = max(abs(a - b) for ra, rb in zip(obj.matrix_world, expected) for a, b in zip(ra, rb))
                check(f"rotate_z_90 {target} {angle} cw={clockwise}", diff < 1e-4, f"max diff {diff}")
                out[f"{target}:{angle}:{clockwise}"] = fingerprint([Vector(r[:3]) for r in obj.matrix_world])
    results["rotate_z_90"] = out


# --- grid_circle.py ---------------------------------------------------------

def test_grid_circle():
    reset_scene()
    run_script("grid_circle.py")
    obj = bpy.context.active_object
    check("grid_circle default faces", obj is not None and len(obj.data.polygons) == 64)
    run_script("grid_circle.py")
    check("grid_circle rerun menu", len(menu_entries(bpy.types.VIEW3D_MT_mesh_add)) == 1)

    out = {}
    for subdivisions in (1, 2, 8, 17):
        for roundness in (0.0, 0.5, 1.0):
            for radius in (0.5, 2.0):
                bpy.ops.mesh.primitive_grid_circle_add(
                    subdivisions=subdivisions, roundness=roundness, radius=radius)
                me = bpy.context.active_object.data
                tag = f"{subdivisions}:{roundness}:{radius}"
                check(f"grid_circle faces {tag}", len(me.polygons) == subdivisions ** 2)
                check(f"grid_circle quads {tag}", all(len(p.vertices) == 4 for p in me.polygons))
                far = max(v.co.length for v in me.vertices)
                expected = radius * (math.sqrt(2) if roundness == 0.0 else 1.0) if roundness != 0.5 else None
                if expected is not None:
                    check(f"grid_circle extent {tag}", abs(far - expected) < 1e-4, f"{far} != {expected}")
                out[tag] = fingerprint([v.co for v in me.vertices])
    results["grid_circle"] = out


# --- gn_simple_deform.py ----------------------------------------------------

def _gn_input(mod, name):
    for item in mod.node_group.interface.items_tree:
        if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.name == name:
            return getattr(mod.properties.inputs, item.identifier)
    raise KeyError(name)


def _gn_set(obj, mod, name, value):
    _gn_input(mod, name).value = value
    # Setting a modifier input from Python doesn't refresh it in background mode.
    obj.update_tag()


def test_gn_simple_deform():
    reset_scene()
    bar = make_bar()
    run_script("gn_simple_deform.py")
    mod = bar.modifiers[0]
    end = bpy.data.objects["SD_Falloff_B"]
    orig = [v.co.copy() for v in bar.data.vertices]
    top = [i for i, c in enumerate(orig) if abs(c.z - 2) < 1e-4]
    bottom = [i for i, c in enumerate(orig) if abs(c.z + 2) < 1e-4]
    corner = max(top, key=lambda i: orig[i].x + orig[i].y)

    def centroid(coords, idx):
        return sum((coords[i] for i in idx), Vector()) / len(idx)

    check("gn defaults", _gn_input(mod, "Mode").value == "Twist" and _gn_input(mod, "Axis").value == "Z")
    cs = evaluated_coords(bar)
    check("gn twist corner", (cs[corner] - Vector((-0.3, 0.3, 2.0))).length < 1e-3, f"{cs[corner]}")
    check("gn twist bottom untouched", max((cs[i] - orig[i]).length for i in bottom) < 1e-5)

    _gn_set(bar, mod, "Mode", "Bend")
    _gn_set(bar, mod, "Use Falloff", False)
    radius = 4 / (math.pi / 2)
    c = centroid(evaluated_coords(bar), top)
    check("gn bend tip", (c - Vector((radius, 0, -2 + radius))).length < 1e-3, f"{c}")
    _gn_set(bar, mod, "Use Falloff", True)
    end.location.z = 0.0
    radius = 2 / (math.pi / 2)
    c = centroid(evaluated_coords(bar), top)
    check("gn bend falloff tip", (c - Vector((radius + 2, 0, -2 + radius))).length < 1e-3, f"{c}")
    end.location.z = 2.0

    _gn_set(bar, mod, "Mode", "Taper")
    cs = evaluated_coords(bar)
    check("gn taper", (cs[corner] - Vector((0.45, 0.45, 2.0))).length < 1e-3, f"{cs[corner]}")
    _gn_set(bar, mod, "Mode", "Stretch")
    cs = evaluated_coords(bar)
    side = 0.3 / math.sqrt(1.5)
    check("gn stretch", (cs[corner] - Vector((side, side, 4.0))).length < 1e-3, f"{cs[corner]}")
    _gn_set(bar, mod, "Mode", "Twist")
    _gn_set(bar, mod, "Invert", True)
    cs = evaluated_coords(bar)
    check("gn invert keeps top", max((cs[i] - orig[i]).length for i in top) < 1e-5)
    _gn_set(bar, mod, "Invert", False)
    check("gn falloff attribute", "falloff" in bar.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.attributes)

    # Broad sweep for the before/after comparison.
    out = {}
    for mode in ("Twist", "Bend", "Taper", "Stretch"):
        for axis in ("X", "Y", "Z"):
            for use_falloff in (True, False):
                for invert in (False, True):
                    _gn_set(bar, mod, "Mode", mode)
                    _gn_set(bar, mod, "Axis", axis)
                    _gn_set(bar, mod, "Use Falloff", use_falloff)
                    _gn_set(bar, mod, "Invert", invert)
                    _gn_set(bar, mod, "Angle", math.radians(-60 if invert else 120))
                    _gn_set(bar, mod, "Factor", -0.4 if invert else 0.7)
                    cs = evaluated_coords(bar)
                    out[f"{mode}:{axis}:{use_falloff}:{invert}"] = fingerprint(cs)
                    check(f"gn finite {mode} {axis}", all(math.isfinite(v) for co in cs for v in co))
    results["gn_simple_deform"] = out

    select_only(bar)
    run_script("gn_simple_deform.py")
    check("gn rerun reuses group", len([g for g in bpy.data.node_groups if g.name.startswith("GN Simple Deform")]) == 1)
    check("gn rerun menu", len(menu_entries(bpy.types.VIEW3D_MT_object)) == 1)


# --- uv_channels.py ---------------------------------------------------------

def test_uv_channels():
    reset_scene()
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.context.active_object
    bpy.ops.mesh.primitive_plane_add(location=(3, 0, 0))
    plane = bpy.context.active_object
    plane.data.uv_layers.remove(plane.data.uv_layers[0])
    bpy.ops.mesh.primitive_monkey_add(location=(-3, 0, 0))
    monkey = bpy.context.active_object
    monkey.data.uv_layers[0].name = "MyUV"
    monkey.data.uv_layers.new(name="Extra")
    monkey.data.uv_layers.active = monkey.data.uv_layers["Extra"]
    select_only(cube, plane, monkey)
    before = [tuple(l.vector) for l in cube.data.uv_layers[0].uv]
    run_script("uv_channels.py")
    run_script("uv_channels.py")

    out = {}
    for obj, expected in ((cube, ["UV_Materials", "UV_Graphics"]),
                          (plane, ["UV_Materials", "UV_Graphics"]),
                          (monkey, ["UV_Materials", "Extra", "UV_Graphics"])):
        uvs = obj.data.uv_layers
        names = [l.name for l in uvs]
        check(f"uv names {obj.name}", names == expected, f"{names}")
        check(f"uv active {obj.name}", uvs.active.name == "UV_Materials")
        check(f"uv render {obj.name}", uvs["UV_Materials"].active_render)
        same = [tuple(l.vector) for l in uvs["UV_Materials"].uv] == [tuple(l.vector) for l in uvs["UV_Graphics"].uv]
        check(f"uv copy {obj.name}", same)
        out[obj.name] = {"names": names, "uv": fingerprint([Vector((*l.vector, 0)) for l in uvs["UV_Graphics"].uv])}
    check("uv layout kept", [tuple(l.vector) for l in cube.data.uv_layers["UV_Materials"].uv] == before)
    check("uv rerun menu", len(menu_entries(bpy.types.VIEW3D_MT_object)) == 1)
    results["uv_channels"] = out


# --- proxy_setup.py ---------------------------------------------------------

def test_proxy_setup():
    reset_scene()
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=4, y_subdivisions=4)
    grid = bpy.context.active_object
    bpy.ops.mesh.primitive_cube_add(location=(3, 0, 0))
    cube = bpy.context.active_object
    # A copy of the grid shifted by less than DISTANCE, to be merged away.
    bpy.ops.object.select_all(action='DESELECT')
    select_only(grid)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.duplicate_move(TRANSFORM_OT_translate={"value": (0.001, 0, 0)})
    bpy.ops.object.mode_set(mode='OBJECT')
    raw = len(grid.data.vertices)
    bpy.ops.object.empty_add()
    empty = bpy.context.active_object
    select_only(grid, cube, empty)
    run_script("proxy_setup.py")
    run_script("proxy_setup.py")
    check("proxy one modifier", [m.type for m in grid.modifiers] == ['NODES'] and len(cube.modifiers) == 1)
    check("proxy one group", len([g for g in bpy.data.node_groups if g.name.startswith("PROXY_Setup")]) == 1)
    merged = len(evaluated_coords(grid))
    # The depsgraph evaluates in viewport mode here, so the merge is active.
    check("proxy merges in viewport", merged == raw // 2, f"{raw} -> {merged}")
    results["proxy_setup"] = {"raw": raw, "viewport": merged, "cube": len(evaluated_coords(cube))}


# --- rotate_view.py ---------------------------------------------------------

def test_rotate_view():
    # A 3D Viewport needs a UI window, which background Blender doesn't have,
    # so only the viewport lookup is tested here, on stand-in objects.
    ns = runpy.run_path(os.path.join(ARGS.scripts, "rotate_view.py"), run_name="rotate_view")

    class Obj:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    region = Obj(type='WINDOW')
    view = Obj(type='VIEW_3D', regions=[Obj(type='HEADER'), region])
    window = Obj(screen=Obj(areas=[Obj(type='OUTLINER', regions=[]), view]))
    check("rotate_view finds viewport", ns["find_view3d"](window) == (view, region))
    empty_window = Obj(screen=Obj(areas=[Obj(type='OUTLINER', regions=[])]))
    check("rotate_view no viewport", ns["find_view3d"](empty_window) == (None, None))
    check("rotate_view angle", ns["ANGLE_DEGREES"] == 90)
    results["rotate_view"] = {"angle": ns["ANGLE_DEGREES"]}


TESTS = [test_rotate_z_90, test_grid_circle, test_gn_simple_deform, test_uv_channels,
         test_proxy_setup, test_rotate_view]


def main():
    print(f"Blender {bpy.app.version_string}, scripts: {os.path.abspath(ARGS.scripts)}")
    for test in TESTS:
        print(test.__name__)
        try:
            test()
        except Exception:
            failures.append(f"{test.__name__}: exception")
            traceback.print_exc()
    if ARGS.json:
        with open(ARGS.json, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=1, sort_keys=True)
    print(f"{len(TESTS)} tests, {len(failures)} failure(s)")
    for failure in failures:
        print("  " + failure)
    sys.exit(1 if failures else 0)


main()
