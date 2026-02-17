# Phase 12: Documentation and PyPI Publishing - Research

**Researched:** 2026-02-17
**Domain:** mkdocs-material documentation site, mkdocstrings API reference generation, PyPI publishing with uv_build backend, PEP 561 py.typed verification
**Confidence:** HIGH

## Summary

Phase 12 completes the v1.1 Python SDK milestone by building a documentation site and publishing the `kalshibook` package to PyPI. The SDK is already fully functional (Phases 8-11 complete): it has a `KalshiBook` client class with sync/async methods for all endpoints, typed dataclass response models, auto-paginating iterators, `.to_df()` DataFrame conversion, and comprehensive docstrings in NumPy style.

The documentation site uses mkdocs-material (the de facto standard for Python SDK docs) with mkdocstrings-python for auto-generated API reference from existing docstrings. The SDK already has thorough NumPy-style docstrings on all public methods and models, so API reference generation is mostly configuration rather than content creation. The hand-written content (Getting Started guide, Authentication guide, code examples) is the bulk of the docs work. For PyPI publishing, the SDK already uses `uv_build` as its build backend and has a properly configured `pyproject.toml` with classifiers, MIT license, and py.typed marker. The main work is: (1) adding `[project.urls]` metadata, (2) fixing the version duplication issue (`_http.py` hardcodes `_VERSION = "0.1.0"` separately from `__init__.py`), (3) building with `uv build --package kalshibook`, and (4) publishing with `uv publish`. A GitHub Actions workflow for CI/CD is a natural addition -- publishing on tagged releases via PyPI Trusted Publishers, and deploying docs via `mkdocs gh-deploy`.

**Primary recommendation:** Use mkdocs-material 9.x + mkdocstrings-python 2.x with the gen-files/literate-nav recipe for auto-generated API reference. The docs site lives at `sdk/docs/` with `sdk/mkdocs.yml`. Publish to PyPI using `uv build --package kalshibook && uv publish` triggered by GitHub Actions on tagged releases. Fix the version duplication by having `_http.py` import from `__init__.py`. Add two GitHub Actions workflows: one for docs deployment, one for package publishing.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mkdocs-material | >=9.7 | Documentation site theme and framework | De facto standard for Python SDK docs. Version 9.7.1 is latest. All previously-Insiders features now free. |
| mkdocstrings[python] | >=1.0 | Auto-generated API reference from docstrings | Official mkdocstrings handler for Python. Uses Griffe to parse docstrings. Supports NumPy-style which the SDK uses. |
| mkdocs-gen-files | >=0.5 | Auto-generate API reference pages at build time | Required for the auto-reference recipe. Generates one .md file per module. |
| mkdocs-literate-nav | >=0.6 | Build navigation from generated SUMMARY.md | Pairs with gen-files to create navigation structure automatically. |
| mkdocs-section-index | >=0.3 | Bind __init__ docs to folder index pages | Makes package-level documentation appear at folder level in nav. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pymdown-extensions | (bundled) | Code highlighting, tabbed content, admonitions | Bundled with mkdocs-material. Configure extensions in mkdocs.yml. |
| uv | (existing) | Build and publish package | Already the project's package manager. `uv build` + `uv publish` for PyPI. |
| mypy | >=1.10 | Verify py.typed works in consumer code | Already in SDK dev deps. Run against test consumer script. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| mkdocs-material | Sphinx + furo | Sphinx is more powerful but much more complex to configure. mkdocs-material is simpler, better-looking defaults, and is the modern Python SDK standard (used by FastAPI, httpx, Pydantic, etc.) |
| mkdocstrings auto-gen recipe | Manual API reference pages | Manual pages get stale. The gen-files recipe auto-generates pages from source, always in sync. |
| mkdocs-gen-files + literate-nav | mkdocs-api-autonav | mkdocs-api-autonav is newer and simpler but less battle-tested. The gen-files recipe is the official recommended approach. |
| uv publish | twine | uv publish is the native publishing tool for uv_build projects. twine is older and requires separate installation. |
| GitHub Actions trusted publisher | PyPI API token | Trusted publishers are more secure (no long-lived secrets) and the recommended approach for new projects. |

**Installation (docs dev deps):**

```bash
# In sdk/pyproject.toml [dependency-groups]
docs = [
    "mkdocs-material>=9.7",
    "mkdocstrings[python]>=1.0",
    "mkdocs-gen-files>=0.5",
    "mkdocs-literate-nav>=0.6",
    "mkdocs-section-index>=0.3",
]
```

## Architecture Patterns

### Recommended Project Structure (Phase 12 additions)

```
sdk/
+-- pyproject.toml          # ADD: [project.urls], docs dep group
+-- mkdocs.yml              # NEW: mkdocs-material configuration
+-- docs/                   # NEW: hand-written documentation
|   +-- index.md            # Home page / overview
|   +-- getting-started.md  # DOCS-01: Getting Started guide
|   +-- authentication.md   # DOCS-02: Authentication guide
|   +-- examples/           # DOCS-04: Code examples
|   |   +-- orderbook.md    # Orderbook reconstruction examples
|   |   +-- markets.md      # Market listing and detail examples
|   |   +-- candles.md      # OHLCV candle examples
|   |   +-- events.md       # Event hierarchy examples
|   |   +-- deltas.md       # Orderbook delta pagination examples
|   |   +-- trades.md       # Trade pagination examples
|   |   +-- settlements.md  # Settlement query examples
|   |   +-- dataframes.md   # DataFrame conversion examples
|   +-- reference/           # DOCS-03: auto-generated (by gen-files)
+-- scripts/
|   +-- gen_ref_pages.py    # NEW: auto-generate API reference pages
+-- src/kalshibook/
|   +-- __init__.py         # MODIFY: version is single source of truth
|   +-- _http.py            # MODIFY: import version from __init__
|   +-- (rest unchanged)
```

Root-level additions:
```
.github/
+-- workflows/
    +-- docs.yml            # NEW: deploy docs to GitHub Pages on push to main
    +-- publish.yml         # NEW: publish to PyPI on tagged release
```

### Pattern 1: mkdocs.yml Configuration for SDK Documentation

**What:** Complete mkdocs.yml configuration that ties together material theme, mkdocstrings, gen-files, and literate-nav.

**Key configuration:**

```yaml
# sdk/mkdocs.yml
site_name: KalshiBook Python SDK
site_url: https://kalshibook.github.io/kalshibook/  # or custom domain
site_description: Python SDK for KalshiBook L2 orderbook data API

repo_url: https://github.com/kalshibook/kalshibook
repo_name: kalshibook/kalshibook

theme:
  name: material
  palette:
    - scheme: default
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - scheme: slate
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
  features:
    - content.code.copy
    - content.code.annotate
    - navigation.tabs
    - navigation.sections
    - navigation.top
    - search.suggest
    - search.highlight

plugins:
  - search
  - gen-files:
      scripts:
        - scripts/gen_ref_pages.py
  - literate-nav:
      nav_file: SUMMARY.md
  - section-index
  - mkdocstrings:
      handlers:
        python:
          paths: [src]
          options:
            docstring_style: numpy
            docstring_section_style: table
            show_root_heading: true
            show_source: false
            separate_signature: true
            show_signature_annotations: true
            merge_init_into_class: true
            members_order: source

markdown_extensions:
  - pymdownx.highlight:
      anchor_linenums: true
      pygments_lang_class: true
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.snippets
  - pymdownx.inlinehilite
  - admonition
  - pymdownx.details
  - attr_list
  - md_in_html
  - toc:
      permalink: true

nav:
  - Home: index.md
  - Getting Started: getting-started.md
  - Authentication: authentication.md
  - Examples:
    - examples/orderbook.md
    - examples/markets.md
    - examples/candles.md
    - examples/events.md
    - examples/deltas.md
    - examples/trades.md
    - examples/settlements.md
    - examples/dataframes.md
  - API Reference: reference/
```

### Pattern 2: gen_ref_pages.py Script for Auto-Generated API Reference

**What:** Script that runs at build time to generate one markdown file per public module, each containing a `::: kalshibook.module` directive that mkdocstrings expands into full API docs.

**Key design decisions:**
- Only generate pages for public modules (exclude `_http.py`, `_parsing.py`, `_pagination.py` internals unless they export public types like `PageIterator`)
- The `__init__.py` page becomes the package index, showing all re-exported symbols
- Filter out `__pycache__`, `__main__`, and test files

```python
"""Generate the code reference pages and navigation."""
from pathlib import Path
import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()
root = Path(__file__).parent.parent
src = root / "src"

for path in sorted(src.rglob("*.py")):
    module_path = path.relative_to(src).with_suffix("")
    doc_path = path.relative_to(src).with_suffix(".md")
    full_doc_path = Path("reference", doc_path)

    parts = tuple(module_path.parts)

    if parts[-1] == "__init__":
        parts = parts[:-1]
        doc_path = doc_path.with_name("index.md")
        full_doc_path = full_doc_path.with_name("index.md")
    elif parts[-1].startswith("_"):
        # Skip private modules (_http, _parsing, _pagination)
        # PageIterator is re-exported via __init__.py
        continue

    nav[parts] = doc_path.as_posix()

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        ident = ".".join(parts)
        fd.write(f"::: {ident}")

    mkdocs_gen_files.set_edit_path(full_doc_path, path.relative_to(root))

with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
```

**Important nuance:** The SDK has private modules (`_http.py`, `_parsing.py`, `_pagination.py`) that contain implementation details. However, `PageIterator` from `_pagination.py` IS a public type (exported in `__init__.py`). The gen_ref_pages.py script should skip private modules -- `PageIterator` will appear in the `kalshibook` package-level reference page since it is re-exported via `__init__.py`. An alternative approach is to include `_pagination.py` in the reference but filter to only show `PageIterator`. The simpler approach (skip private, rely on re-exports) is recommended.

### Pattern 3: PyPI Publishing with uv_build

**What:** Build the SDK package and publish to PyPI using uv's native build and publish commands.

**Build command (from workspace root):**
```bash
uv build --package kalshibook
```

This uses the `uv_build` backend declared in `sdk/pyproject.toml` and outputs to `sdk/dist/`:
- `kalshibook-0.1.0.tar.gz` (sdist)
- `kalshibook-0.1.0-py3-none-any.whl` (wheel)

**Publish command:**
```bash
uv publish sdk/dist/*
```

**Key requirement:** The `--package kalshibook` flag tells uv to build only the SDK workspace member, not the root `kalshibook-server` package.

### Pattern 4: GitHub Actions for Docs Deployment

**What:** GitHub Actions workflow that builds and deploys docs to GitHub Pages on push to main.

```yaml
# .github/workflows/docs.yml
name: Deploy Docs
on:
  push:
    branches: [main]
    paths:
      - 'sdk/docs/**'
      - 'sdk/mkdocs.yml'
      - 'sdk/src/**'
      - 'sdk/scripts/**'
permissions:
  contents: write
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Configure Git Credentials
        run: |
          git config user.name github-actions[bot]
          git config user.email 41898282+github-actions[bot]@users.noreply.github.com
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install mkdocs-material mkdocstrings[python] mkdocs-gen-files mkdocs-literate-nav mkdocs-section-index
      - run: cd sdk && mkdocs gh-deploy --force
```

### Pattern 5: GitHub Actions for PyPI Publishing (Trusted Publisher)

**What:** GitHub Actions workflow that builds and publishes to PyPI when a GitHub release is created.

```yaml
# .github/workflows/publish.yml
name: Publish to PyPI
on:
  release:
    types: [published]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv build --package kalshibook
      - uses: actions/upload-artifact@v5
        with:
          name: dist
          path: sdk/dist/
  publish:
    needs: build
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/download-artifact@v5
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
```

**PyPI Trusted Publisher setup required:**
- Register the GitHub repository as a trusted publisher at pypi.org
- Configure the workflow filename, repository owner/name, and environment name (`pypi`)
- The `id-token: write` permission is mandatory for OIDC-based authentication

### Pattern 6: Version Single Source of Truth

**What:** Fix the version duplication between `__init__.py` and `_http.py`.

**Current state (problem):**
- `sdk/src/kalshibook/__init__.py`: `__version__ = "0.1.0"`
- `sdk/src/kalshibook/_http.py`: `_VERSION = "0.1.0"` (separate copy, comment says "Phase 12 can refactor")
- `sdk/pyproject.toml`: `version = "0.1.0"` (third copy)

**Fix:** Have `_http.py` import from `__init__.py`:
```python
# _http.py
from kalshibook import __version__
# ...
"User-Agent": f"kalshibook-python/{__version__}",
```

**Note on circular imports:** `__init__.py` imports from `client.py` which imports from `_http.py`. If `_http.py` imports from `__init__.py`, this creates a circular dependency. Two solutions:
1. Move `__version__` to a separate `_version.py` module: `__version__ = "0.1.0"`. Both `__init__.py` and `_http.py` import from `_version.py`.
2. Use `importlib.metadata.version("kalshibook")` in `_http.py` -- but this fails during editable installs and is slow.

**Recommendation:** Use a `_version.py` module as the single source of truth. This is the standard pattern (used by setuptools-scm, hatch-vcs, etc.).

```python
# sdk/src/kalshibook/_version.py
__version__ = "0.1.0"
```

```python
# sdk/src/kalshibook/__init__.py
from kalshibook._version import __version__
```

```python
# sdk/src/kalshibook/_http.py
from kalshibook._version import __version__
# ...
"User-Agent": f"kalshibook-python/{__version__}",
```

For the `pyproject.toml` version, use dynamic version sourcing if uv_build supports it, or accept the duplication in pyproject.toml (bumped manually with version bumps).

### Anti-Patterns to Avoid

- **Generating docs for private modules (_http, _parsing):** Users should see the public API only. Internal modules clutter the reference and expose implementation details.
- **Using Sphinx instead of mkdocs:** The rest of the ecosystem (httpx, the SDK's sole dependency) uses mkdocs-material. Consistency matters.
- **Publishing without `--package` flag:** In a workspace, `uv build` without `--package` may build the wrong package or fail.
- **Hardcoding PyPI token in workflow:** Use trusted publishers (OIDC) instead of long-lived API tokens.
- **Skipping TestPyPI validation:** Always publish to TestPyPI first to verify metadata, README rendering, and package installability before the real publish.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| API reference documentation | Manual markdown per class/method | mkdocstrings auto-generation from docstrings | Docstrings already exist and are comprehensive. Auto-gen stays in sync with code. |
| Documentation site styling | Custom CSS/HTML | mkdocs-material theme | Professional, responsive, dark mode, search, code copy -- all built in. |
| Package build pipeline | Custom build scripts | `uv build --package kalshibook` | uv_build is already configured as the backend. One command builds sdist + wheel. |
| PyPI publishing auth | Manual token management | Trusted Publishers (OIDC) | More secure, no secrets to rotate, recommended by PyPI. |
| Navigation for API reference | Manual nav entries per module | gen-files + literate-nav auto-generation | Automatically discovers all modules and creates navigation tree. |

**Key insight:** The SDK already has excellent docstrings. The documentation phase is primarily about configuring tools to render what already exists, plus writing 3-4 hand-crafted guide pages.

## Common Pitfalls

### Pitfall 1: mkdocstrings Can't Find Package

**What goes wrong:** `mkdocs build` fails with "Module 'kalshibook' not found" error.
**Why it happens:** mkdocstrings needs the package importable. If building docs without installing the SDK first, Griffe cannot find the source.
**How to avoid:** Set `paths: [src]` in the mkdocstrings handler configuration. This tells Griffe to look in `sdk/src/` for the package source. Alternatively, install the package in editable mode (`uv pip install -e sdk/`) before building docs.
**Warning signs:** Build errors mentioning missing modules.

### Pitfall 2: NumPy Docstring Parsing Issues

**What goes wrong:** mkdocstrings-python's NumPy-style parser has partial support. Some sections may not render correctly.
**Why it happens:** Griffe's NumPy parser is less mature than its Google-style parser. The mkdocstrings-python docs explicitly call this a "work in progress."
**How to avoid:** The SDK uses standard NumPy sections (Parameters, Returns, Raises, Examples) which ARE supported. Avoid `Methods` section in class docstrings (known issue). Set `docstring_style: numpy` explicitly in mkdocs.yml. Test the docs build locally and inspect rendered output before committing.
**Warning signs:** Missing parameter descriptions, malformed return type rendering.

### Pitfall 3: Circular Import with Version Refactoring

**What goes wrong:** Moving version to be importable from `_http.py` creates circular imports: `__init__.py` -> `client.py` -> `_http.py` -> `__init__.py`.
**Why it happens:** The import chain is: `__init__.py` imports `KalshiBook` from `client.py`, `client.py` imports `HttpTransport` from `_http.py`. If `_http.py` imports `__version__` from `__init__.py`, the cycle is complete.
**How to avoid:** Use a `_version.py` module that contains only the version string. Both `__init__.py` and `_http.py` import from `_version.py`. No circular dependency.
**Warning signs:** `ImportError: cannot import name '__version__' from partially initialized module`.

### Pitfall 4: Building Wrong Package in Workspace

**What goes wrong:** `uv build` without `--package` flag builds the root `kalshibook-server` package instead of the SDK.
**Why it happens:** The monorepo has two packages: `kalshibook-server` (root) and `kalshibook` (sdk/ workspace member). Without specifying the package, uv may default to the root.
**How to avoid:** Always use `uv build --package kalshibook` from the workspace root, or `cd sdk && uv build` from the SDK directory.
**Warning signs:** Built wheel contains server code instead of SDK code.

### Pitfall 5: README Not Rendering on PyPI

**What goes wrong:** The SDK's `README.md` shows as raw markdown or is missing on PyPI.
**Why it happens:** PyPI renders README from the `readme` field in `pyproject.toml`. The current `readme = "README.md"` is correct, but the content is minimal. PyPI also requires the README file to be included in the sdist.
**How to avoid:** Ensure `README.md` is included in the build (uv_build includes it by default when `readme` is set). Expand the README with install instructions, quick start, and links to docs. Test on TestPyPI first.
**Warning signs:** Empty or broken README on PyPI project page.

### Pitfall 6: py.typed Not Included in Wheel

**What goes wrong:** Consumer code runs `mypy --strict` and gets "missing library stubs or py.typed marker" error even though `py.typed` exists in the source tree.
**Why it happens:** The build backend must explicitly include `py.typed` in the wheel distribution. Some build backends exclude marker files.
**How to avoid:** `uv_build` includes `py.typed` by default when it is inside the package directory (`src/kalshibook/py.typed`). Verify after building: `unzip -l sdk/dist/kalshibook-0.1.0-py3-none-any.whl | grep py.typed` should show the file.
**Warning signs:** File missing from wheel contents.

### Pitfall 7: Missing [project.urls] Metadata

**What goes wrong:** PyPI project page has no links to documentation, source code, or issue tracker.
**Why it happens:** `[project.urls]` is not set in `sdk/pyproject.toml`.
**How to avoid:** Add `[project.urls]` section:
```toml
[project.urls]
Documentation = "https://kalshibook.github.io/kalshibook/"
Repository = "https://github.com/kalshibook/kalshibook"
Issues = "https://github.com/kalshibook/kalshibook/issues"
Changelog = "https://github.com/kalshibook/kalshibook/releases"
```
**Warning signs:** Bare PyPI page with no sidebar links.

## Code Examples

### Verified: mkdocs-material Minimal Configuration

Source: https://squidfunk.github.io/mkdocs-material/creating-your-site/

```yaml
site_name: My site
site_url: https://mydomain.org/mysite
theme:
  name: material
```

### Verified: mkdocstrings Python Handler Configuration

Source: https://mkdocstrings.github.io/python/usage/configuration/docstrings/

```yaml
plugins:
  - mkdocstrings:
      handlers:
        python:
          paths: [src]
          options:
            docstring_style: numpy
            docstring_section_style: table
            show_root_heading: true
            separate_signature: true
            show_signature_annotations: true
```

### Verified: Autodoc Injection in Markdown

Source: https://mkdocstrings.github.io/python/usage/

```markdown
# KalshiBook Client

::: kalshibook.KalshiBook
    options:
      show_root_heading: true
      members:
        - get_orderbook
        - list_markets
        - get_market
```

### Verified: uv Build and Publish Commands

Source: https://docs.astral.sh/uv/guides/package/

```bash
# Build from workspace root
uv build --package kalshibook

# Publish to TestPyPI first
uv publish --index testpypi sdk/dist/*

# Publish to PyPI
uv publish sdk/dist/*
```

### Verified: py.typed Verification Script

```bash
# Build the package
uv build --package kalshibook

# Verify py.typed is in the wheel
python -c "
import zipfile, glob
whl = glob.glob('sdk/dist/*.whl')[0]
with zipfile.ZipFile(whl) as z:
    names = z.namelist()
    assert any('py.typed' in n for n in names), 'py.typed missing from wheel!'
    print('py.typed found in wheel')
"

# Verify mypy recognizes types in consumer code
cat > /tmp/test_typing.py << 'EOF'
from kalshibook import KalshiBook, KalshiBookError, PageIterator

client: KalshiBook = KalshiBook(api_key="kb-test")
reveal_type(client)  # should show KalshiBook
EOF

mypy --strict /tmp/test_typing.py
```

## Inventory of Public API Surface (What Docs Must Cover)

### Client Methods (from client.py -- all have NumPy docstrings)

| Method | Sync | Async | Category |
|--------|------|-------|----------|
| `KalshiBook.__init__()` | - | - | Constructor |
| `KalshiBook.from_env()` | - | - | Factory |
| `get_orderbook()` | Yes | `aget_orderbook()` | Orderbook |
| `list_markets()` | Yes | `alist_markets()` | Markets |
| `get_market()` | Yes | `aget_market()` | Markets |
| `get_candles()` | Yes | `aget_candles()` | Candles |
| `list_events()` | Yes | `alist_events()` | Events |
| `get_event()` | Yes | `aget_event()` | Events |
| `list_settlements()` | Yes | `alist_settlements()` | Settlements |
| `get_settlement()` | Yes | `aget_settlement()` | Settlements |
| `list_deltas()` | Yes | `alist_deltas()` | Deltas (paginated) |
| `list_trades()` | Yes | `alist_trades()` | Trades (paginated) |
| `close()` / `aclose()` | Yes | Yes | Lifecycle |

### Models (from models.py -- all are frozen dataclasses)

| Model | Category | Has `.to_df()` |
|-------|----------|----------------|
| `ResponseMeta` | Metadata | No |
| `OrderbookLevel` | Orderbook | No |
| `OrderbookResponse` | Orderbook | No |
| `DeltaRecord` | Deltas | No (iterated via PageIterator) |
| `TradeRecord` | Trades | No (iterated via PageIterator) |
| `MarketSummary` | Markets | No |
| `MarketDetail` | Markets | No |
| `MarketsResponse` | Markets | Yes |
| `MarketDetailResponse` | Markets | No |
| `CandleRecord` | Candles | No |
| `CandlesResponse` | Candles | Yes |
| `EventSummary` | Events | No |
| `EventDetail` | Events | No |
| `EventsResponse` | Events | Yes |
| `EventDetailResponse` | Events | No |
| `SettlementRecord` | Settlements | No |
| `SettlementResponse` | Settlements | No |
| `SettlementsResponse` | Settlements | Yes |
| `BillingStatus` | Billing | No |

### Exceptions (from exceptions.py)

| Exception | HTTP Status | Description |
|-----------|-------------|-------------|
| `KalshiBookError` | (base) | Base for all SDK errors |
| `AuthenticationError` | 401 | Invalid/missing API key |
| `RateLimitError` | 429 | Rate limit exceeded (auto-retried) |
| `CreditsExhaustedError` | 429 | Monthly credits exhausted |
| `MarketNotFoundError` | 404 | Market/event/settlement not found |
| `ValidationError` | 422 | Invalid request parameters |

### Other Public Types

| Type | Module | Purpose |
|------|--------|---------|
| `PageIterator[T]` | `_pagination` (re-exported) | Auto-paginating iterator with `.to_df()` |
| `__version__` | `__init__` | Package version string |

## Docs Content Outline

### Getting Started Guide (DOCS-01)

1. Installation (`pip install kalshibook` / `pip install kalshibook[pandas]`)
2. Get an API key (link to kalshibook.io dashboard)
3. First query: reconstruct an orderbook
4. List available markets
5. Convert to DataFrame

### Authentication Guide (DOCS-02)

1. API key format (`kb-...`)
2. Direct key: `KalshiBook("kb-your-key")`
3. Environment variable: `KalshiBook.from_env()` with `KALSHIBOOK_API_KEY`
4. Context manager usage for cleanup
5. Sync vs async mode
6. Error handling (AuthenticationError, CreditsExhaustedError)

### Code Examples (DOCS-04)

One page per endpoint category with complete, runnable examples:
- Orderbook reconstruction
- Market listing and detail
- OHLCV candles
- Event hierarchy
- Orderbook deltas (pagination)
- Trade history (pagination)
- Settlement data
- DataFrame conversion patterns

## pyproject.toml Additions Needed

```toml
[project.urls]
Documentation = "https://kalshibook.github.io/kalshibook/"
Repository = "https://github.com/kalshibook/kalshibook"
Issues = "https://github.com/kalshibook/kalshibook/issues"
Changelog = "https://github.com/kalshibook/kalshibook/releases"

[dependency-groups]
docs = [
    "mkdocs-material>=9.7",
    "mkdocstrings[python]>=1.0",
    "mkdocs-gen-files>=0.5",
    "mkdocs-literate-nav>=0.6",
    "mkdocs-section-index>=0.3",
]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sphinx + ReadTheDocs | mkdocs-material + GitHub Pages | 2022+ (accelerated 2024-2025) | Simpler config, faster builds, modern UI. Used by httpx, FastAPI, Pydantic, Polars. |
| Manual API reference pages | mkdocstrings auto-generation from docstrings | 2020+ (mkdocstrings 0.13+) | API docs always in sync with source code. |
| twine + PyPI API tokens | uv publish + Trusted Publishers (OIDC) | 2024 (PyPI OIDC support) | No secrets to manage; more secure CI/CD. |
| setup.py + setuptools | pyproject.toml + uv_build | 2024+ | Faster builds, standardized metadata, workspace support. |
| Sphinx autodoc | mkdocstrings + Griffe | 2021+ | Better handling of modern Python (dataclasses, type hints, `from __future__` imports). |
| mkdocs-material Insiders (paid) | mkdocs-material 9.7 (all features free) | 2025-11 | All Insiders features now available in the free version. |

**Deprecated/outdated:**
- `setup.py` / `setup.cfg`: Replaced by `pyproject.toml` (PEP 621)
- `twine upload`: Replaced by `uv publish` for uv_build projects
- PyPI password authentication: Removed by PyPI. Use tokens or trusted publishers.
- Sphinx for SDK docs: Not deprecated, but mkdocs-material is the modern standard for Python SDK documentation

## Open Questions

1. **What domain/URL will the docs site be hosted at?**
   - What we know: GitHub Pages is the simplest option (`kalshibook.github.io/kalshibook/`). A custom domain (e.g., `docs.kalshibook.io`) requires DNS configuration.
   - Recommendation: Start with GitHub Pages. Custom domain can be added later with a CNAME file.

2. **Should the README.md be expanded or replaced?**
   - What we know: Current README is minimal (10 lines). PyPI renders it as the project description. Good READMEs increase adoption.
   - Recommendation: Expand the README significantly to serve as a mini-getting-started guide with install, quickstart, and link to full docs. The README should stand alone for users who find the package on PyPI.

3. **Should we set up TestPyPI first?**
   - What we know: TestPyPI lets you verify package metadata, README rendering, and installability before the real publish.
   - Recommendation: Yes, always publish to TestPyPI first. Add a manual GitHub Actions workflow for TestPyPI, and an automatic one for production PyPI on tagged releases.

4. **Version pinning strategy for pyproject.toml?**
   - What we know: `pyproject.toml` has `version = "0.1.0"` as a static string. `_version.py` also has it. Two places to update on release.
   - Recommendation: Accept the duplication for now. Dynamic version sourcing with uv_build is not yet well-established. Document the bump procedure: update both `_version.py` and `pyproject.toml`.

5. **Should docs include the async API prominently or treat it as secondary?**
   - What we know: The SDK has sync methods (primary) and async methods (prefixed with `a`). Most users will use sync mode.
   - Recommendation: Lead with sync examples in all guides. Add tabbed sync/async examples where it adds value (Getting Started, Authentication). The API reference will show both automatically via mkdocstrings.

## Sources

### Primary (HIGH confidence)
- SDK source code (`sdk/src/kalshibook/`) -- all modules read directly, docstring styles verified, public API surface catalogued
- SDK pyproject.toml (`sdk/pyproject.toml`) -- build backend, dependencies, classifiers, metadata verified
- mkdocs-material official docs (https://squidfunk.github.io/mkdocs-material/) -- installation, configuration, publishing, GitHub Actions workflow
- mkdocstrings official docs (https://mkdocstrings.github.io/python/usage/) -- handler configuration, docstring styles, NumPy support status
- mkdocstrings recipes (https://mkdocstrings.github.io/recipes/) -- gen-files/literate-nav auto-generation recipe with full script
- uv official docs (https://docs.astral.sh/uv/guides/package/) -- build and publish commands, workspace package flag
- Python Packaging User Guide (https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/) -- trusted publisher workflow, pypa/gh-action-pypi-publish action
- PEP 561 (https://peps.python.org/pep-0561/) -- py.typed marker specification
- Griffe docstring docs (https://mkdocstrings.github.io/griffe/guide/users/recommendations/docstrings/) -- NumPy section support confirmed

### Secondary (MEDIUM confidence)
- mkdocs-material PyPI page (https://pypi.org/project/mkdocs-material/) -- version 9.7.1 confirmed as latest
- mkdocstrings-python PyPI page (https://pypi.org/project/mkdocstrings-python/) -- version 2.0.2 confirmed, released 2026-02-09
- PyPI Trusted Publishers docs (https://docs.pypi.org/trusted-publishers/) -- setup instructions for GitHub Actions
- pypa/gh-action-pypi-publish (https://github.com/pypa/gh-action-pypi-publish) -- v1.11.0+ auto-generates PEP 740 attestations
- mkdocstrings NumPy support page (https://mkdocstrings.github.io/python/usage/docstrings/numpy/) -- "work in progress" note, Methods section known issue

### Tertiary (LOW confidence)
- None. All findings verified from official documentation or direct source inspection.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- mkdocs-material + mkdocstrings is the standard Python SDK docs stack. All libraries actively maintained with recent releases (Feb 2026).
- Architecture: HIGH -- gen-files/literate-nav recipe is the official mkdocstrings recommendation. uv build/publish workflow verified from official docs. GitHub Actions patterns from PyPI and mkdocs-material official guides.
- Pitfalls: HIGH -- circular import issue identified from direct source analysis. NumPy docstring limitations verified from official mkdocstrings docs. Workspace build gotcha verified from uv docs.
- Docs content: HIGH -- complete inventory of public API surface derived from direct source reading. All methods have existing NumPy docstrings.

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (stable patterns, no expected breaking changes in mkdocs-material 9.x or uv_build 0.10.x)
