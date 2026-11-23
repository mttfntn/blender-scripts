# Handover

Everything needed to maintain **blender-scripts** without the original author.
A compact version for AI assistants is in [AGENTS.md](AGENTS.md).

## What this is

Six standalone Python scripts for Blender 5.3, run from Blender's Text Editor
(**Run Script**). They are not an add-on: there is no `bl_info`, no extension
manifest and nothing to install. Four of them register an operator and a menu
entry when run, so they can be reused from menus or F3 search for the rest of
the Blender session.

The repository is public at <https://github.com/mttfntn/blender-scripts>,
licensed GPL-3.0-or-later. It is not a fork.

## What you need

- Blender **5.3** (the only supported version). Locally it was installed at
  `C:\Program Files\Blender Foundation\Blender 5.3\blender.exe`.
- Python 3 (any recent version) for `tools/build_release.py` and
  `tests/compare.py`. These don't import Blender.
- `git` and, for releases, push access to the repository.

## How the code is organized

| Path | Purpose |
| --- | --- |
| `scripts/rotate_z_90.py` | Operator `object.rotate_z_90`: rotate selected objects around their own Z. |
| `scripts/grid_circle.py` | Operator `mesh.primitive_grid_circle_add`: quad-grid disc primitive. |
| `scripts/gn_simple_deform.py` | Operator `object.add_gn_simple_deform`: builds the "GN Simple Deform" node group and its empties. |
| `scripts/uv_channels.py` | Operator `object.setup_uv_channels`: `UV_Materials` + `UV_Graphics`. |
| `scripts/proxy_setup.py` | Plain script: adds the "PROXY_Setup" Geometry Nodes modifier. |
| `scripts/rotate_view.py` | Plain script: rolls the 3D Viewport. |
| `tests/run_tests.py` | Test suite, run inside background Blender. |
| `tests/compare.py` | Diffs two `run_tests.py --json` result files. |
| `tools/build_release.py` | Builds `dist/blender-scripts-vX.Y.Z.zip`. |
| `manifest.json` | Name, version, supported Blender version. Read by CI and the Blender badge. |
| `.github/workflows/tests.yml` | CI: tests on every push/PR; release on `v*` tags. |
| `.github/ISSUE_TEMPLATE/`, `.github/pull_request_template.md` | Issue forms and PR template. |
| `CONTRIBUTING.md`, `SECURITY.md` | Contributor and security-report guides. |
| `HANDOVER.md`, `AGENTS.md` | This file and its AI-assistant version. Not shipped in the zip. |

### The common script pattern

The four operator scripts share one shape, keep it when adding a script:

1. Settings as module-level constants at the top (`DEFAULT_SUBDIVISIONS`,
   `MATERIALS_UV`, ...), so users can edit them without reading the code.
2. An operator class with `bl_options = {'REGISTER', 'UNDO'}`. Its docstring is
   the tooltip Blender shows, so keep it one short line; use `#` comments for
   anything else inside the class.
3. `menu_func`, `register()`, `unregister()`.
4. `_cleanup_previous_run()`: removes the menu entry and operator class an
   earlier run registered, so running the script twice doesn't add a second
   menu entry. It finds the old menu function through
   `menu._dyn_ui_initialize()`, a private Blender API.
5. `if __name__ == "__main__":` clean up, register, then run the operator once
   if its `poll()` allows.

## The scripts

### rotate_z_90.py
Rotates each selected object around a Z axis through its own origin, in world
space, by rebuilding `matrix_world` (so rotation mode and parenting don't
matter). Redo panel: Angle, Clockwise.

### grid_circle.py
Builds an (n+1)×(n+1) grid on [-1, 1]², maps each vertex with the elliptical
square-to-disc mapping `x·√(1−y²/2), y·√(1−x²/2)`, blends with the square by
Roundness, scales by Radius. All faces are quads. Defaults are the
`DEFAULT_*` constants.

### gn_simple_deform.py (the main feature)
Creates three empties and a Geometry Nodes modifier:

- `SD_Origin`: pivot and orientation of the deform.
- `SD_Falloff_A` / `SD_Falloff_B`: rings parented to the Origin, locked to
  slide along local Z, placed at the mesh's lowest and highest points.

Data flow in the node group (`build_node_group`):

1. Positions go into Origin space (inverse of the Origin's transform), then
   into "axis space": a cyclic swizzle makes the chosen Axis local Z.
2. The falloff `t` is the position along Z between A and B, clamped to 0..1.
   With Use Falloff off, A and B are replaced by the mesh's min/max along the
   axis. Invert swaps A and B. Twist, Taper and Stretch pass `t` through the
   "Falloff Shape" Float Curve; Bend uses `t` directly so it keeps its length.
3. The deform works like Blender's Simple Deform limits: before A nothing moves,
   between A and B the deform grows, past B the shape continues rigidly.
   Twist rotates by Angle·falloff; Bend wraps the A→B segment around a circle of
   radius length/Angle and continues past B along the tangent; Taper scales
   X/Y by 1 + Factor·falloff; Stretch lengthens by Factor and thins X/Y to keep
   the volume.
4. Results go back through the swizzle and the Origin transform into Set
   Position. The falloff value is stored as the `falloff` point attribute.

The node group is built once and reused by name ("GN Simple Deform").

### uv_channels.py
For each selected mesh: renames UV map 1 to `UV_Materials` (or creates it if
the mesh has none), adds `UV_Graphics` as a bulk copy (`foreach_get/set`), and
keeps `UV_Materials` active and used for rendering. Names that already exist
are left alone, so it is safe to run twice.

### proxy_setup.py
Builds the "PROXY_Setup" group: Merge by Distance (`DISTANCE`, mode All) feeds
a Switch driven by Is Viewport, so the viewport shows the merged mesh and
renders use the original. Skips meshes that already have it.

### rotate_view.py
Finds the first 3D Viewport in the current window and calls
`view3d.view_roll` with `ANGLE_DEGREES`.

## How to make a change

1. Edit the script in `scripts/`.
2. Run the tests (below). If you fix a bug, add a check for it to
   `tests/run_tests.py` first and watch it fail.
3. For refactors, compare results before and after (below): there must be no
   differences you can't explain.
4. Try it once in a real Blender: open the script in the Text Editor, Run Script.
5. Commit with a message that says how you verified it.

## Running the tests

```bash
blender -b --factory-startup --python-exit-code 1 --python tests/run_tests.py
```

Exit code 0 and `6 tests, 0 failure(s)` means pass. Use a scratch profile so
your own Blender settings and add-ons are never involved:

```bash
BLENDER_USER_RESOURCES=/tmp/blender-scratch blender -b --factory-startup --python-exit-code 1 --python tests/run_tests.py
```

Comparing two versions (for example the last commit against your changes):

```bash
git worktree add ../bs-before HEAD
blender -b --factory-startup --python tests/run_tests.py -- --scripts ../bs-before/scripts --json before.json
blender -b --factory-startup --python tests/run_tests.py -- --json after.json
python tests/compare.py before.json after.json
```

The tests can't open a UI window, so `rotate_view.py` is only tested for its
viewport lookup, and `proxy_setup.py` only in viewport mode.

## How to make a release

1. Set the new `version` in `manifest.json` and commit.
2. Create an annotated tag whose message is the release notes, and push it:
   ```bash
   git tag -a v1.1.0 -m "Release notes here"
   git push origin main v1.1.0
   ```
3. CI runs the tests, checks the tag equals the manifest version, builds
   `blender-scripts-v1.1.0.zip`, publishes the GitHub release titled
   "blender-scripts v1.1.0" with the tag message as notes, and updates the
   download-size badge.
4. Check the Actions run for that tag and the release page.

**Don't delete the `badges` branch.** The download-size badge in the README
reads `download-size.json` from it (shields.io can't read release downloads
directly). The release job force-pushes it on every release.

## Updating to a new Blender version

The only supported version is set in three places that must agree:
`manifest.json` (`blender_version`, `blender_download`), and the
`BLENDER_VERSION`, `BLENDER_SERIES` and `BLENDER_SHA256` values in
`.github/workflows/tests.yml` (checksum from
`https://download.blender.org/release/BlenderX.Y/blender-X.Y.Z.sha256`, the
`linux-x64.tar.xz` line). CI fails if the workflow and manifest disagree.

## Things to know

- **Modifier inputs (Blender 5.2+)**: set with
  `mod.properties.inputs.<identifier>.value = ...`. The old
  `mod["Socket_N"] = ...` raises `TypeError`. Menu inputs take the item name
  as a string (`"Bend"`).
- **Background refresh**: setting a modifier input from Python in background
  mode doesn't re-evaluate the object; call `obj.update_tag()` (the tests do).
- **Re-running scripts** reuses node groups by name. If you change a node
  group's layout, delete the old group from the .blend (or rename
  `GROUP_NAME`) before testing, otherwise the old one is reused.
- **Merge by Distance** has a "Mode" menu input in 5.x, not a `.mode` property.

## Known limits

- `gn_simple_deform.py`: the falloff rings are placed on, and locked to, the
  Z axis. Changing Axis to X or Y keeps working but the rings must be moved
  by hand (unlock their X/Y location first); with falloff on and both rings on Z the deform does nothing until
  they are moved apart along the new axis.
- `gn_simple_deform.py`: distances are measured in the deformed object's local
  space, so a scaled object scales the falloff too.
- `rotate_view.py` uses the first 3D Viewport in the window, which may not be
  the one under the mouse; in Quad View, locked panes may not roll.
- Running a script through a remote socket (for example a Blender MCP server)
  may not create an undo step.
