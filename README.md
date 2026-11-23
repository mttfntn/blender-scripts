# blender-scripts

[![Blender](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fmttfntn%2Fblender-scripts%2Fmain%2Fmanifest.json&query=%24.blender_version&label=Blender&color=orange&logo=blender&logoColor=white)](manifest.json)
[![Release](https://img.shields.io/github/v/release/mttfntn/blender-scripts)](https://github.com/mttfntn/blender-scripts/releases/latest)
[![Download size](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fmttfntn%2Fblender-scripts%2Fbadges%2Fdownload-size.json)](https://github.com/mttfntn/blender-scripts/releases/latest)
[![Tests](https://github.com/mttfntn/blender-scripts/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/mttfntn/blender-scripts/actions/workflows/tests.yml)
[![License](https://img.shields.io/github/license/mttfntn/blender-scripts)](LICENSE)
[![Language](https://img.shields.io/github/languages/top/mttfntn/blender-scripts)](scripts)

A collection of standalone Python scripts for Blender 5.3. They are not an
add-on: open one in Blender's Text Editor and press **Run Script**.

## Scripts

| Script | What it does | After running, also found in |
| --- | --- | --- |
| [`rotate_z_90.py`](scripts/rotate_z_90.py) | Rotates the selected objects 90° around their own Z axis (works for parented objects and any rotation mode). Angle and direction can be changed in the redo panel. | Object › Transform › **Rotate 90° Z** |
| [`grid_circle.py`](scripts/grid_circle.py) | Adds a flat disc made only of quads (a square grid warped into a circle), so it subdivides cleanly. Radius, subdivisions and roundness in the redo panel; starting values are variables at the top of the file. | Add › Mesh › **Grid Circle** |
| [`gn_simple_deform.py`](scripts/gn_simple_deform.py) | Blender's Simple Deform (Twist, Bend, Taper, Stretch) rebuilt in Geometry Nodes, with a falloff controlled by two ring empties on the deform axis, plus an Origin empty for pivot and orientation. | Object › **Add GN Simple Deform** |
| [`uv_channels.py`](scripts/uv_channels.py) | Renames the first UV map of the selected meshes to `UV_Materials` and adds `UV_Graphics` as a copy of it. Safe to run twice. | Object › **Setup UV Channels** |
| [`proxy_setup.py`](scripts/proxy_setup.py) | Adds a `PROXY_Setup` Geometry Nodes modifier to the selected meshes: lighter in the viewport (merge by distance), full mesh at render time. | (runs once, no menu entry) |
| [`rotate_view.py`](scripts/rotate_view.py) | Rolls the 3D Viewport 90° around the axis pointing out of the screen. Only the view changes, not the objects. | (runs once, no menu entry) |

## Usage

1. Download the latest release zip, or copy a single script from [`scripts/`](scripts).
2. In Blender 5.3, open the **Text Editor**, then **Text › Open** and pick the script.
3. Select what the script works on (see the table), then press **Run Script** (Alt+P).

Scripts with a menu entry register it when run, so after the first run you can
use the menu or F3 search instead. Running a script again is safe: it replaces
its own menu entry instead of adding a second one.

More detail on each script, including known limits, is in
[HANDOVER.md](HANDOVER.md#the-scripts).

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
