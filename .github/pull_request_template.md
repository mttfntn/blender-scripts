## What this changes

<!-- Which script(s), and what users will notice. Link the issue if there is one. -->

## How it was verified

- [ ] Tests pass in Blender 5.3:
      `blender -b --factory-startup --python-exit-code 1 --python tests/run_tests.py`
- [ ] For a bug fix: a check was added to `tests/run_tests.py` that failed before the fix
- [ ] For a refactor: `tests/compare.py` shows no differences against `main` (see HANDOVER.md, "Running the tests")
- [ ] Ran the script once in a real Blender 5.3 (Text Editor › Run Script)

## Checklist

- [ ] Each script is still one self-contained file with its SPDX line and module description
- [ ] Operator docstrings stay one-line tooltips
- [ ] README scripts table and HANDOVER.md updated if behaviour or options changed
