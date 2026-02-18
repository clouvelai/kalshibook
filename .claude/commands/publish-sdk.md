# Publish KalshiBook SDK to PyPI

Bump version, verify the build locally, then create a GitHub release which triggers automated publishing to PyPI via trusted publisher (OIDC — no tokens needed).

## Steps

1. **Bump version** in `sdk/src/kalshibook/_version.py`:
   - Read the current version
   - Ask the user what the new version should be (e.g., 0.2.0, 0.1.1)
   - Update `_version.py` with the new version string

2. **Build and verify locally:**
   ```bash
   uv build --package kalshibook
   ```
   Then verify:
   - py.typed is in the wheel: `python -c "import zipfile, glob; whl=glob.glob('dist/*.whl')[0]; z=zipfile.ZipFile(whl); assert any('py.typed' in n for n in z.namelist()); print('py.typed OK')"`
   - Package imports: `uv venv /tmp/kb-verify && uv pip install --python /tmp/kb-verify/bin/python dist/kalshibook-*.whl && /tmp/kb-verify/bin/python -c "from kalshibook import KalshiBook, __version__; print(f'v{__version__} OK')" && rm -rf /tmp/kb-verify`
   - Tests pass: `uv run --package kalshibook pytest sdk/tests/ -x -q`

3. **Commit the version bump:**
   ```bash
   git add sdk/src/kalshibook/_version.py
   git commit -m "chore: bump kalshibook to vX.Y.Z"
   git push origin main
   ```

4. **Create a GitHub release** (this triggers the publish workflow):
   ```bash
   gh release create vX.Y.Z --title "vX.Y.Z" --generate-notes
   ```

5. **Watch the publish workflow:**
   ```bash
   gh run list --workflow publish.yml --limit 1
   gh run watch <run-id>
   ```

6. **Verify on PyPI:**
   ```bash
   uv venv /tmp/kb-verify && uv pip install --python /tmp/kb-verify/bin/python kalshibook && /tmp/kb-verify/bin/python -c "from kalshibook import __version__; print(f'PyPI: v{__version__}')" && rm -rf /tmp/kb-verify
   ```

## How it works

- `publish.yml` triggers on GitHub release creation
- Build job: `uv build --package kalshibook` → uploads wheel as artifact
- Publish job: downloads artifact → publishes to PyPI via OIDC trusted publisher
- No API tokens or secrets needed — PyPI trusts the GitHub Actions workflow directly
- Trusted publisher configured at pypi.org (Owner: clouvelai, Repo: kalshibook, Workflow: publish.yml, Environment: pypi)

## Architecture

```
_version.py  ←── single source of truth
    ↓
__init__.py  ←── re-exports __version__
_http.py     ←── uses in User-Agent header
pyproject.toml ←── reads via setuptools (if dynamic versioning added later)
```
