# pdfscrub

Python CLI project managed with `uv`. The package is installed in editable mode via `uv sync`.

## After code changes

Run `uv sync --reinstall-package pdfscrub` after any change that affects the installed package (CLI entry points, new modules, pyproject.toml changes). Without this, `uv run pdfscrub` will still execute the old installed version.

Plain `uv sync` is not enough — it skips reinstalling packages that appear unchanged on disk.
