# blender-scripts

[![Blender](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fmttfntn%2Fblender-scripts%2Fmain%2Fmanifest.json&query=%24.blender_version&label=Blender&color=orange&logo=blender&logoColor=white)](manifest.json)
[![Tests](https://github.com/mttfntn/blender-scripts/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/mttfntn/blender-scripts/actions/workflows/tests.yml)
[![License](https://img.shields.io/github/license/mttfntn/blender-scripts)](LICENSE)
[![Language](https://img.shields.io/github/languages/top/mttfntn/blender-scripts)](scripts)

A collection of standalone Python scripts for Blender 5.3. They are not an
add-on: open one in Blender's Text Editor and press **Run Script**. Each
script does its job once and registers nothing (no menu entries, no
operators), so it leaves no trace in Blender's interface.

## Scripts

| Script | What it does | Settings at the top of the file ([details](#settings)) |
| --- | --- | --- |
| [`rotate_z_90.py`](scripts/rotate_z_90.py) | Rotates the selected objects 90° around their own Z axis (works for parented objects and any rotation mode). | `ANGLE_DEGREES`, `CLOCKWISE` |
| [`grid_circle.py`](scripts/grid_circle.py) | Adds a flat disc made only of quads (a square grid warped into a circle) at the 3D cursor, so it subdivides cleanly. | `SUBDIVISIONS`, `RADIUS`, `ROUNDNESS` |
| [`gn_simple_deform.py`](scripts/gn_simple_deform.py) | Blender's Simple Deform (Twist, Bend, Taper, Stretch) rebuilt in Geometry Nodes, added to the active mesh, with a falloff controlled by two ring empties on the deform axis plus an Origin empty for pivot and orientation. All controls are in the modifier panel. | none (use the modifier panel) |
| [`uv_channels.py`](scripts/uv_channels.py) | Renames the first UV map of the selected meshes to `UV_Materials` and adds `UV_Graphics` as a copy of it. Safe to run twice. | `MATERIALS_UV`, `GRAPHICS_UV` |
| [`proxy_setup.py`](scripts/proxy_setup.py) | Adds a `PROXY_Setup` Geometry Nodes modifier to the selected meshes: lighter in the viewport (merge by distance), full mesh at render time. | `DISTANCE` |
| [`quad_fill.py`](scripts/quad_fill.py) | Fills the selected holes with quads, like Grid Fill, but the sides don't need matching edge counts: it finds the 4 corners and builds straight strips joined by the classic cheat-sheet transitions (3-1, 4-2, 5-3 and 1-2, 2-3, 3-4). A hole with an odd number of edges gets exactly one triangle. Edit Mode: select the hole's border (Alt+click). Run it again with the new faces still selected to cycle through the other rotations, or set `LAYOUT` to pick one. | `LAYOUT`, `ALLOW_TRIANGLE`, `FALLBACK_FILL` |
| [`rotate_view.py`](scripts/rotate_view.py) | Rolls the 3D Viewport 90° around the axis pointing out of the screen. Only the view changes, not the objects. | `ANGLE_DEGREES` |

## Usage

1. Copy a script from [`scripts/`](scripts), or download the whole
   repository (**Code › Download ZIP**).
2. In Blender 5.3, open the **Text Editor**, then **Text › Open** and pick the script.
3. Select what the script works on (see the table), then press **Run Script** (Alt+P).
   To change a setting, edit the value at the top of the file and run it again
   (see [Settings](#settings) for what each one accepts).

`rotate_z_90.py`, `gn_simple_deform.py` and `uv_channels.py` only run in
Object Mode; in another mode they print a message to the system console and
do nothing. `quad_fill.py` is the opposite: it only runs in Edit Mode.

More detail on each script, including known limits, is in
[HANDOVER.md](HANDOVER.md#the-scripts).

> **Tip:** I usually include these in a personal add-on created using
> [Scripting Nodes](https://scriptingnodes.com/) by Joshua Knauber.

## Settings

Each script's settings are plain Python variables at the top of the file.
Edit the value, save, and press **Run Script** again (Ctrl+Z first if you
want to redo the previous run with the new value). The types are:

| Type | What to write | Examples |
| --- | --- | --- |
| `int` | a whole number, no decimal point | `8`, `0`, `-90` |
| `float` | a number that may have decimals (a whole number works too) | `1.0`, `0.01`, `2` |
| `bool` | `True` or `False`, with a capital first letter and no quotes | `True` |
| `str` | text in quotes | `"UV_Materials"` |

Values outside the allowed range either raise an error in the system console
(**Window › Toggle System Console** on Windows) or give a result you
probably don't want, as noted below.

### rotate_z_90.py

| Setting | Type | Default | Allowed values | What it does |
| --- | --- | --- | --- | --- |
| `ANGLE_DEGREES` | `int` or `float` | `90` | Any number. Negative turns the other way; `360` (or any multiple) changes nothing. | How far each selected object turns around its own Z axis, in degrees. |
| `CLOCKWISE` | `bool` | `False` | `True` or `False` | `False` turns counter-clockwise when you look down from +Z (Blender's positive direction), `True` clockwise. |

### grid_circle.py

| Setting | Type | Default | Allowed values | What it does |
| --- | --- | --- | --- | --- |
| `SUBDIVISIONS` | `int` | `8` | `1` or more. `0` stops with an error, a negative number adds an empty mesh, a decimal number stops with an error. | Quads across the disc: the disc has `SUBDIVISIONS × SUBDIVISIONS` faces. |
| `RADIUS` | `float` | `1.0` | More than `0`, in scene units (metres by default). `0` gives a disc collapsed to a point. | Radius of the disc (at `ROUNDNESS = 1`). |
| `ROUNDNESS` | `float` | `1.0` | `0.0` to `1.0`. Below `0` the corners stick out past the square; above `1` they are pulled in past the circle. | `0` is a flat square grid (corners at `RADIUS × √2`), `1` a full circle, values between blend the two. |

### gn_simple_deform.py

No settings at the top: every control is an input on the modifier, so you can
change it after running the script. For reference:

| Modifier input | Type | Default | Allowed values | What it does |
| --- | --- | --- | --- | --- |
| Mode | menu | Twist | Twist, Bend, Taper, Stretch | Which deform to apply. |
| Axis | menu | Z | X, Y, Z | Axis the deform runs along, in the Origin empty's space. |
| Angle | angle | 90° | Any angle | Total twist or bend between the two falloff empties (Twist and Bend only). |
| Factor | float | 0.5 | Any number; `0` does nothing, negative goes the other way | Amount of taper or stretch (Taper and Stretch only). |
| Origin | object | the added Origin empty | Any object | Pivot and orientation of the deform. |
| Use Falloff | bool | on | on / off | Off deforms evenly across the whole mesh. |
| Falloff Start / Falloff End | object | the added ring empties | Any objects, apart along the axis | Where the deform starts and where it reaches full strength. |
| Invert | bool | off | on / off | Swaps start and end. |

`GROUP_NAME` (`str`, `"GN Simple Deform"`) is the name of the node group the
script creates and reuses; change it only if you want a separate copy.

### uv_channels.py

| Setting | Type | Default | Allowed values | What it does |
| --- | --- | --- | --- | --- |
| `MATERIALS_UV` | `str` | `"UV_Materials"` | Any non-empty text, different from `GRAPHICS_UV`. An empty name gives an error and Blender uses `UVMap` instead. | Name given to the first UV map (channel 1). |
| `GRAPHICS_UV` | `str` | `"UV_Graphics"` | Any non-empty text, different from `MATERIALS_UV`. | Name of the second UV map (channel 2), created as a copy of the first. |

Meshes that already have a UV map with these names are left as they are, so
if you change a name, run it on meshes that don't have the old names yet.

### proxy_setup.py

| Setting | Type | Default | Allowed values | What it does |
| --- | --- | --- | --- | --- |
| `DISTANCE` | `float` | `0.01` | `0` or more, in scene units (metres by default). `0` merges only vertices at exactly the same spot. The script doesn't stop a negative value, but it is not useful. | Starting value of the modifier's Distance input: in the viewport, vertices closer than this are merged. You can change it later in the modifier panel. |
| `GROUP_NAME` | `str` | `"PROXY_Setup"` | Any non-empty text | Name of the node group. It is reused if it already exists, so a new `DISTANCE` only applies to a new group: delete or rename the old one first. |

### quad_fill.py

| Setting | Type | Default | Allowed values | What it does |
| --- | --- | --- | --- | --- |
| `LAYOUT` | `int` | `0` | `0` or more. Numbers past the last layout wrap around (on a hole with 3 layouts, `4` is layout 1). Negative numbers act like `0`. | Rotation of the pattern. `0`: the best layout first, and running again with the new faces still selected gives the next one. `1`, `2`, `3`, …: always that layout, also when re-filling selected faces. The console prints the one used, for example `layout 2/3`. |
| `ALLOW_TRIANGLE` | `bool` | `True` | `True` or `False` | A hole with an odd number of edges can't be all quads. `True` fills it with exactly one triangle, `False` skips that hole. |
| `FALLBACK_FILL` | `bool` | `True` | `True` or `False` | When no pattern fits (very uneven sides): `True` fills the hole with triangles and joins them into quads where it can, `False` skips that hole. |
| `BALANCE_WEIGHT` | `float` | `0.5` | `0` or more; useful range about `0` to `2`. | How the 4 corners are chosen. `0` picks only the sharpest corners; higher values prefer 4 sides of similar length, and above about `1.5` this can win over clear corners. |
| `MAX_LAYOUTS_TRIED` | `int` | `50` | `1` or more | How many corner choices are checked for folded or flat faces before giving up and using `FALLBACK_FILL`. Higher is slower only on holes that are hard to fill. |

### rotate_view.py

| Setting | Type | Default | Allowed values | What it does |
| --- | --- | --- | --- | --- |
| `ANGLE_DEGREES` | `int` or `float` | `90` | Any number. Negative rolls the other way. | How far the 3D Viewport rolls around the axis pointing out of the screen, in degrees. |

## Requirements

- Blender 5.3. Other versions are not tested; `gn_simple_deform.py` in
  particular relies on the modifier input API introduced in Blender 5.2.

## Running the tests

The tests run each script in a background Blender and check the results:

```bash
blender -b --factory-startup --python-exit-code 1 --python tests/run_tests.py
```

See [HANDOVER.md](HANDOVER.md#running-the-tests) for comparing two versions.

## Contributing

Bug reports and ideas are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md).
Please report security problems privately, as described in [SECURITY.md](SECURITY.md).

Project documentation: [HANDOVER.md](HANDOVER.md) for people,
[AGENTS.md](AGENTS.md) for AI coding assistants.

## License

[GPL-3.0-or-later](LICENSE), the same license as Blender.
