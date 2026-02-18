# Publish KalshiBook SDK to PyPI

Build, verify, and publish the SDK package. Requires `UV_PUBLISH_TOKEN` env var (PyPI API token).

## Steps

1. **Build** the package:
   ```bash
   uv build --package kalshibook
   ```

2. **Verify** the wheel:
   - py.typed is included
   - Package installs and imports in a temp venv
   - Version string is correct

3. **Publish** to PyPI:
   ```bash
   uv publish sdk/dist/* --token "$UV_PUBLISH_TOKEN"
   ```

4. **Verify** the published package:
   ```bash
   pip install --upgrade kalshibook
   python -c "from kalshibook import KalshiBook, __version__; print(f'kalshibook {__version__} installed from PyPI')"
   ```

## First-time setup

If `UV_PUBLISH_TOKEN` is not set:
1. Tell the user to create a PyPI API token at https://pypi.org/manage/account/token/
2. Add `UV_PUBLISH_TOKEN=pypi-...` to their shell profile or `.env`
3. Re-run this command

## Version bumps

Before publishing a new version, update `sdk/src/kalshibook/_version.py` with the new version string. The version flows to `__init__.py`, `_http.py` User-Agent, and `pyproject.toml` (via dynamic version) automatically.
