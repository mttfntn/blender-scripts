# AGENTS.md

Compact guide for AI coding assistants. Full human version: [HANDOVER.md](HANDOVER.md).

## Project
- Standalone Blender **5.3** Python scripts in `scripts/`, run via Text Editor › Run Script. Not an add-on (no `bl_info`, no extension manifest). **No releases.**
- Scripts run once and register nothing (no operators, menus, handlers, redo panel); the owner wants it that way. Settings are constants at the top of each file.
- Name everywhere: `blender-scripts`. Repo: https://github.com/mttfntn/blender-scripts (public, GPL-3.0-or-later, not a fork). Branch: `main`.
- `manifest.json`: `name`, `blender_version` (badge), `blender_download` (CI).

## Commands
```bash
# tests (exit 0 = pass); always factory settings + scratch profile
BLENDER_USER_RESOURCES=/tmp/bs-profile blender -b --factory-startup --python-exit-code 1 --python tests/run_tests.py
# before/after comparison
blender -b --factory-startup --python tests/run_tests.py -- --scripts OLD/scripts --json before.json
blender -b --factory-startup --python tests/run_tests.py -- --json after.json
python tests/compare.py before.json after.json     # exit 1 on any difference
```
Local Blender: `C:\Program Files\Blender Foundation\Blender 5.3\blender.exe`.

## Architecture
- Every script: SPDX line + docstring → constants → plain functions taking settings as defaults (`rotate_objects`, `add_grid_circle`, `add_simple_deform`, `setup_uv_channels`, `rotate_view`, `quad_fill`) → `__main__` checks context (Object Mode / active mesh), calls once, prints one line. `proxy_setup` runs top to bottom.
- Tests load functions with `runpy.run_path(path, run_name="<name>")` (skips `__main__`) and assert `check_registers_nothing`.
- `quad_fill` (Edit Mode): selected border loops → `candidate_layouts` (4 corners + orientation, scored by angle and side balance) → `plan_rows` (grid / shrink2 = 3-1, 4-2: outer columns turn, inner run into trapezoids / corner = 2-3: centred split + edge to the extra right-side vertex / one triangle if odd) → `layout_faces` (exact square coordinates, no relaxing) → `build_patch` (Coons patch) → `is_clean` check, else next layout, else triangle fill + join. Faces selected on run → `clear_fill` + next of `layout_variants` (matched by `signature`), so re-running cycles rotations; `LAYOUT` > 0 fixes the variant number instead. Pure functions are testable without a mesh.
- `gn_simple_deform` data flow: position → inverse Origin transform → axis swizzle (chosen axis → local Z) → t = clamp((z−A)/(B−A)) (A/B = ring empties, or mesh min/max if Use Falloff off; Invert swaps) → Float Curve (not for Bend) → Twist/Bend/Taper/Stretch via Index Switch → inverse swizzle → Origin transform → Set Position; stores `falloff` attribute. Node group reused by name `GN Simple Deform`. Built with `TreeBuilder` helper.

## Rules and pitfalls
- Never add `register_class`, menu `append`, handlers or `bpy.props` to the scripts.
- Run Script has the UNDO flag: Ctrl+Z undoes a whole script run.
- Modifier inputs on 5.2+: `mod.properties.inputs.<identifier>.value`; `mod["Socket_N"]` raises TypeError. Menu inputs take item names as strings.
- Background mode: after setting modifier inputs call `obj.update_tag()` before reading evaluated data.
- Adding a UV layer can invalidate references to existing layers; look them up again.
- Merge by Distance mode is the `"Mode"` input (`'All'`), not `.mode`.
- Re-running reuses node groups by name: delete/rename old groups when testing node changes.
- Never test in the user's running Blender or real profile; use `-b --factory-startup` and `BLENDER_USER_RESOURCES`.
- Each script must stay a single self-contained file (users copy them loose). Keep the SPDX header line.

## Verification used in the cleanup
Baseline = original scripts (first commit). Suite passed before and after (6 tests, 0 failures, Blender 5.3.0); `compare.py`: 98 cases, 0 differences, both for the cleanup and for the conversion from operators to plain scripts. UV copy speed-up measured 2.555 s → 0.008 s on 2M UV points. In the rotate test, call `view_layer.update()` before reading a child's `matrix_world` (operators did this implicitly; without it 7 child cases differed).

## CI
`.github/workflows/tests.yml`: one job on push to `main` and PRs; downloads Blender (retries + 3 official mirrors, pinned SHA-256), runs the suite with a scratch profile. Nothing built or stored. After pushing, check the run for the exact commit.

## Changing the Blender version
Update together: `manifest.json` (`blender_version`, `blender_download`) and workflow env `BLENDER_VERSION`, `BLENDER_SERIES`, `BLENDER_SHA256` (from `download.blender.org/release/BlenderX.Y/blender-X.Y.Z.sha256`, linux-x64 line). CI fails if manifest and workflow disagree.

## Repo files
`README.md` (scripts table, badges), `HANDOVER.md`, `AGENTS.md`, `CONTRIBUTING.md`, `SECURITY.md`, `.github/ISSUE_TEMPLATE/{bug_report,feature_request}.yml` + `config.yml` (blank issues off), `.github/pull_request_template.md`, `LICENSE` (GPL-3.0).

## Git setup
- Author email: `matteofontana@mttfntn.com` (global git config).
- Small commits; message says how the change was verified.
