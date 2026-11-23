# AGENTS.md

Compact guide for AI coding assistants. Full human version: [HANDOVER.md](HANDOVER.md).

## Project
- Standalone Blender **5.3** Python scripts in `scripts/`, run via Text Editor › Run Script. Not an add-on (no `bl_info`, no extension manifest).
- Name everywhere: `blender-scripts`. Repo: https://github.com/mttfntn/blender-scripts (public, GPL-3.0-or-later, not a fork). Branch: `main`.
- `manifest.json`: `name`, `version`, `blender_version` (badge), `blender_download` (CI). Single source of truth for version.

## Commands
```bash
# tests (exit 0 = pass); always factory settings + scratch profile
BLENDER_USER_RESOURCES=/tmp/bs-profile blender -b --factory-startup --python-exit-code 1 --python tests/run_tests.py
# before/after comparison
blender -b --factory-startup --python tests/run_tests.py -- --scripts OLD/scripts --json before.json
blender -b --factory-startup --python tests/run_tests.py -- --json after.json
python tests/compare.py before.json after.json     # exit 1 on any difference
# release zip (plain Python)
python tools/build_release.py [--tag vX.Y.Z] [--badge-json out.json]
```
Local Blender: `C:\Program Files\Blender Foundation\Blender 5.3\blender.exe`.

## Architecture
- Operator scripts (`rotate_z_90`, `grid_circle`, `gn_simple_deform`, `uv_channels`): constants at top → Operator (`REGISTER|UNDO`) → `menu_func` → `register/unregister` → `_cleanup_previous_run()` (removes earlier menu entry + class via private `menu._dyn_ui_initialize()`) → `__main__`: cleanup, register, run once if `poll()`.
- Plain scripts (`proxy_setup`, `rotate_view`): run top to bottom, no registration.
- `gn_simple_deform` data flow: position → inverse Origin transform → axis swizzle (chosen axis → local Z) → t = clamp((z−A)/(B−A)) (A/B = ring empties, or mesh min/max if Use Falloff off; Invert swaps) → Float Curve (not for Bend) → Twist/Bend/Taper/Stretch via Index Switch → inverse swizzle → Origin transform → Set Position; stores `falloff` attribute. Node group reused by name `GN Simple Deform`. Built with `TreeBuilder` helper.

## Rules and pitfalls
- Operator class docstrings are UI tooltips: one short line; use `#` comments inside classes.
- Modifier inputs on 5.2+: `mod.properties.inputs.<identifier>.value`; `mod["Socket_N"]` raises TypeError. Menu inputs take item names as strings.
- Background mode: after setting modifier inputs call `obj.update_tag()` before reading evaluated data.
- Adding a UV layer can invalidate references to existing layers; look them up again.
- Merge by Distance mode is the `"Mode"` input (`'All'`), not `.mode`.
- Re-running reuses node groups by name: delete/rename old groups when testing node changes.
- Never test in the user's running Blender or real profile; use `-b --factory-startup` and `BLENDER_USER_RESOURCES`.
- Each script must stay a single self-contained file (users copy them loose). Keep the SPDX header line.

## Verification used in the cleanup
Baseline = original scripts (first commit). Suite passed before and after (6 tests, 0 failures, Blender 5.3.0); `compare.py`: 98 cases, 0 differences. UV copy speed-up measured 2.555 s → 0.008 s on 2M UV points.

## Release checklist
1. Bump `manifest.json` `version`; commit.
2. `git tag -a vX.Y.Z -m "notes"`; `git push origin main vX.Y.Z`.
3. CI (`.github/workflows/tests.yml`, one job): tests → tag == manifest check → zip → `gh release create` (title `blender-scripts vX.Y.Z`, notes = tag message, fetched explicitly) → force-push `download-size.json` to branch `badges`. **Never delete the `badges` branch.**
4. Check the run for that exact tag/commit and the release page.

## Changing the Blender version
Update together: `manifest.json` (`blender_version`, `blender_download`) and workflow env `BLENDER_VERSION`, `BLENDER_SERIES`, `BLENDER_SHA256` (from `download.blender.org/release/BlenderX.Y/blender-X.Y.Z.sha256`, linux-x64 line). CI fails if manifest and workflow disagree.

## Repo files
`README.md` (scripts table, badges), `HANDOVER.md`, `AGENTS.md` (not shipped in zip), `CONTRIBUTING.md`, `SECURITY.md`, `.github/ISSUE_TEMPLATE/{bug_report,feature_request}.yml` + `config.yml` (blank issues off), `.github/pull_request_template.md`, `LICENSE` (GPL-3.0).

## Git setup
- Author email: `matteofontana@mttfntn.com` (global git config).
- Small commits; message says how the change was verified.
