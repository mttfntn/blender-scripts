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

| Script | What it does | Settings at the top of the file |
| --- | --- | --- |
| [`rotate_z_90.py`](scripts/rotate_z_90.py) | Rotates the selected objects 90° around their own Z axis (works for parented objects and any rotation mode). | `ANGLE_DEGREES`, `CLOCKWISE` |
| [`grid_circle.py`](scripts/grid_circle.py) | Adds a flat disc made only of quads (a square grid warped into a circle) at the 3D cursor, so it subdivides cleanly. | `SUBDIVISIONS`, `RADIUS`, `ROUNDNESS` |
| [`gn_simple_deform.py`](scripts/gn_simple_deform.py) | Blender's Simple Deform (Twist, Bend, Taper, Stretch) rebuilt in Geometry Nodes, added to the active mesh, with a falloff controlled by two ring empties on the deform axis plus an Origin empty for pivot and orientation. All controls are in the modifier panel. | none (use the modifier panel) |
| [`uv_channels.py`](scripts/uv_channels.py) | Renames the first UV map of the selected meshes to `UV_Materials` and adds `UV_Graphics` as a copy of it. Safe to run twice. | `MATERIALS_UV`, `GRAPHICS_UV` |
| [`proxy_setup.py`](scripts/proxy_setup.py) | Adds a `PROXY_Setup` Geometry Nodes modifier to the selected meshes: lighter in the viewport (merge by distance), full mesh at render time. | `DISTANCE` |
| [`rotate_view.py`](scripts/rotate_view.py) | Rolls the 3D Viewport 90° around the axis pointing out of the screen. Only the view changes, not the objects. | `ANGLE_DEGREES` |

## Usage

1. Copy a script from [`scripts/`](scripts), or download the whole
   repository (**Code › Download ZIP**).
2. In Blender 5.3, open the **Text Editor**, then **Text › Open** and pick the script.
3. Select what the script works on (see the table), then press **Run Script** (Alt+P).
   To change a setting, edit the value at the top of the file and run it again.

`rotate_z_90.py`, `gn_simple_deform.py` and `uv_channels.py` only run in
Object Mode; in another mode they print a message to the system console and
do nothing.

More detail on each script, including known limits, is in
[HANDOVER.md](HANDOVER.md#the-scripts).

> **Tip:** I usually include these in a personal add-on created using
> [Scripting Nodes](https://scriptingnodes.com/) by Joshua Knauber.

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
