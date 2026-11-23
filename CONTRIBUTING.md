# Contributing

Thanks for helping improve blender-scripts.

## Reporting a problem or an idea

Open an issue using the **Bug report** or **Feature request** form. For bugs,
the Blender version, the steps and a small .blend file make it much quicker to
fix. Security problems go through [SECURITY.md](SECURITY.md), not issues.

## Setting up

1. Install Blender 5.3 (the only supported version).
2. Clone the repository:
   ```bash
   git clone https://github.com/mttfntn/blender-scripts.git
   ```
3. Try a script: in Blender's Text Editor, **Text › Open** a file from
   `scripts/` and press **Run Script**.

## Running the tests

```bash
blender -b --factory-startup --python-exit-code 1 --python tests/run_tests.py
```

It should end with `6 tests, 0 failure(s)`. To keep your own Blender settings
out of it, set `BLENDER_USER_RESOURCES` to an empty folder first.

## Fixing a bug

1. Add a check to `tests/run_tests.py` that reproduces the bug, and confirm it fails.
2. Fix the script and confirm the check passes, along with the rest of the suite.
3. If you changed code without meaning to change results, compare against
   `main` with `tests/compare.py` (see [HANDOVER.md](HANDOVER.md#running-the-tests)).

## Style

- Each script is one self-contained file that users can copy on its own:
  no imports between scripts.
- Settings users might edit are constants at the top of the file.
- Start every file with the SPDX line and a short module description.
- Scripts run once and register nothing: no operators, menu entries or
  handlers. Follow the shared pattern in
  [HANDOVER.md](HANDOVER.md#the-common-script-pattern).
- Commit messages say what changed and how it was verified.

## License of contributions

By contributing you agree that your contribution is licensed under
[GPL-3.0-or-later](LICENSE), like the rest of the project.
