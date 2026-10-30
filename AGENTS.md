# Project instructions

## Python environment

- Use the Conda environment named `py37` for all Python commands in this project.
- Before running scripts, tests, linters, or inspection commands, activate it with `conda activate py37`, or use the explicit equivalent `conda run -n py37 python ...`.
- Do not use the system Python, another Conda environment, `.venv`, or `venv` for this project.
- When checking installed packages, use `conda run -n py37 python -m pip ...` or `conda run -n py37 python -c ...` so the check targets `py37`.
- The `py37` environment already contains the project dependencies. Do not install or upgrade packages unless the user explicitly asks for it.
- If `py37` is unavailable, report that fact instead of silently switching environments.

## Common commands

```powershell
conda activate py37
python scan_top.py
python plot_scan.py <csv-file>
python -m compileall .
```

For commands that should not depend on shell activation:

```powershell
conda run -n py37 python scan_top.py
conda run -n py37 python plot_scan.py <csv-file>
conda run -n py37 python -m compileall .
```
