# Phase 8: SDK Scaffolding - Research

**Researched:** 2026-02-17
**Domain:** Python package scaffolding, uv workspaces, pyproject.toml, PEP 561
**Confidence:** HIGH

## Summary

Phase 8 creates the `sdk/` directory as a uv workspace member with its own `pyproject.toml`, module structure, and build system. The SDK publishes to PyPI as `kalshibook` and installs as `from kalshibook import KalshiBook`. No client logic, models, or HTTP transport -- just the empty package skeleton that future phases fill in.

The primary technical challenge is the naming conflict: the root `pyproject.toml` already declares `name = "kalshibook"`. Two packages in the same uv workspace cannot share a project name because uv uses the name for dependency resolution and the lockfile. The solution is to rename the root project to `kalshibook-server` (a non-publishable virtual project) and let the SDK own the `kalshibook` name for PyPI. This is safe because the root has no `[build-system]` and is never published -- it exists only for local development dependency management. The server code imports as `from src.api...`, not `from kalshibook...`, so no import paths change.

The second consideration is `requires-python`. The root uses `>=3.12` (server-side), while the SDK targets `>=3.10` (to support broader user environments where `dataclasses(slots=True)` is available). uv workspaces take the intersection of all members' `requires-python` values for the shared lockfile, resulting in `>=3.12` for development. This is fine: the lockfile governs local dev only; the SDK's `pyproject.toml` independently declares `>=3.10` for PyPI consumers.

**Primary recommendation:** Rename root project to `kalshibook-server`, create `sdk/` with `uv_build` backend, flat `kalshibook` module under `sdk/src/kalshibook/`, empty `KalshiBook` class stub, `py.typed` marker, and verify all five success criteria pass.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Hand-written SDK (no code generation)
- httpx + stdlib dataclasses (no Pydantic -- avoids version conflicts)
- Single `KalshiBook` class with `sync=True` flag (not separate AsyncKalshiBook)
- Replay abstractions deferred to v1.2

### Claude's Discretion
User trusts Claude to design the SDK foundation correctly. All scaffolding decisions are at Claude's discretion, guided by:

**Locked decisions from prior research:**
- Hand-written SDK (no code generation)
- httpx + stdlib dataclasses (no Pydantic -- avoids version conflicts)
- Single `KalshiBook` class with `sync=True` flag (not separate AsyncKalshiBook)
- Replay abstractions deferred to v1.2

**Areas where Claude decides:**
- Module layout (flat vs nested subpackages, how to organize client/models/exceptions/transport)
- Top-level exports (what's importable from `kalshibook` directly)
- Package metadata (description, classifiers, license)
- Minimum Python version (success criteria says 3.10+)
- SDK directory location within the monorepo
- Development tooling (test runner, linting config for SDK)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

## Standard Stack

### Core

| Library/Tool | Version | Purpose | Why Standard |
|-------------|---------|---------|--------------|
| uv_build | >=0.10.3,<0.11.0 | Build backend for SDK package | Official uv build backend. Zero-config for pure Python src layout. Already using uv in project. |
| uv workspaces | (uv CLI) | Monorepo with shared lockfile | Keeps SDK and API in atomic sync. Single `uv.lock` for consistency. |

### Supporting (installed as SDK dependencies for future phases)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | >=0.27 | HTTP transport (sync + async) | Only runtime dependency. Listed in Phase 8 but not used until Phase 9. |
| pandas | >=2.0 (optional) | DataFrame conversion | Optional extra: `pip install kalshibook[pandas]`. Not used until Phase 11. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| uv_build | hatchling, setuptools | uv_build is native to the uv ecosystem already in use; hatchling adds another tool; setuptools is legacy |
| Flat module layout | Nested subpackages | Flat is appropriate for ~10 endpoints and ~15 models; nested adds import complexity for no benefit at this scale |
| src layout | Flat layout (module at root) | src layout prevents accidental imports of uninstalled package; is uv_build's default; is Python packaging best practice |

**Installation (future users):**
```bash
pip install kalshibook          # core only
pip install kalshibook[pandas]  # with DataFrame support
pip install -e ./sdk            # editable from monorepo
```

## Architecture Patterns

### Recommended Project Structure

```
kalshibook/                          # Repository root
├── pyproject.toml                   # Root: renamed to kalshibook-server, adds [tool.uv.workspace]
├── uv.lock                         # Shared lockfile
├── src/                             # Server code (unchanged)
│   ├── api/
│   ├── collector/
│   └── shared/
├── sdk/                             # NEW -- SDK workspace member
│   ├── pyproject.toml               # name = "kalshibook", build-system = uv_build
│   └── src/
│       └── kalshibook/              # Importable package
│           ├── __init__.py          # Version, KalshiBook stub, __all__
│           ├── py.typed             # PEP 561 marker (empty file)
│           ├── client.py            # KalshiBook class stub (empty for Phase 8)
│           ├── models.py            # Model stubs (empty for Phase 8)
│           ├── exceptions.py        # Exception stubs (empty for Phase 8)
│           ├── _http.py             # HTTP transport stub (empty for Phase 8)
│           └── _pagination.py       # Pagination stub (empty for Phase 8)
├── tests/                           # Server tests (existing)
├── dashboard/                       # Dashboard (existing)
└── scripts/                         # Scripts (existing)
```

### Pattern 1: Root Project Renaming

**What:** Rename root `[project] name` from `kalshibook` to `kalshibook-server` to avoid workspace name collision with the SDK.

**Why necessary:** uv uses `[project] name` for dependency resolution. Two workspace members cannot share a name. The root project is a virtual package (no `[build-system]`) used only for local development. It is never published to PyPI. The server code imports as `from src.api...` not `from kalshibook...`, so no code changes are needed.

**What changes:**
```toml
# Root pyproject.toml
[project]
name = "kalshibook-server"   # was: "kalshibook"
```

**What does NOT change:**
- All `from src.api...` imports remain the same
- The `uv.lock` will regenerate with the new name
- No server code files change
- The repository directory name remains `kalshibook/`

### Pattern 2: uv Workspace Configuration

**What:** Add `[tool.uv.workspace]` to root `pyproject.toml` pointing to the `sdk/` member.

**Configuration:**
```toml
# Root pyproject.toml (additions)
[tool.uv.workspace]
members = ["sdk"]
```

The root is automatically a workspace member. The SDK at `sdk/` becomes the second member. Both share `uv.lock`.

### Pattern 3: SDK pyproject.toml with uv_build

**What:** The SDK's `pyproject.toml` declares package metadata, dependencies, and build system.

**Configuration:**
```toml
[project]
name = "kalshibook"
version = "0.1.0"
description = "Python SDK for the KalshiBook L2 orderbook data API"
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
authors = [{ name = "KalshiBook" }]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Intended Audience :: Financial and Insurance Industry",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Typing :: Typed",
]
dependencies = [
    "httpx>=0.27",
]

[project.optional-dependencies]
pandas = ["pandas>=2.0"]

[build-system]
requires = ["uv_build>=0.10.3,<0.11.0"]
build-backend = "uv_build"

[dependency-groups]
dev = [
    "pytest>=9.0",
    "pytest-asyncio>=1.0",
    "pytest-httpx>=0.35",
    "mypy>=1.10",
    "ruff>=0.15",
]
```

**Key decisions in this config:**
- `requires-python = ">=3.10"`: Minimum for `dataclasses(slots=True)`. Broader than server's 3.12+.
- `httpx>=0.27`: Broad lower bound. httpx 0.27+ has the stable async/sync API. No upper bound -- let pip resolve.
- `pandas>=2.0` as optional extra: Users who need `.to_df()` install `kalshibook[pandas]`.
- `uv_build` backend: Native to the uv ecosystem. Expects src layout by default (`sdk/src/kalshibook/`).
- MIT license: Standard for data/finance SDKs (Polygon, Tavily, Alpaca all use MIT or Apache-2.0).
- `Typing :: Typed` classifier: Signals PEP 561 compliance on PyPI.

### Pattern 4: Module __init__.py with Public API

**What:** The `__init__.py` defines version and public exports. For Phase 8, only the empty `KalshiBook` class stub.

**Example:**
```python
"""KalshiBook Python SDK -- L2 orderbook data for Kalshi prediction markets."""

from __future__ import annotations

__version__ = "0.1.0"

from kalshibook.client import KalshiBook

__all__ = ["KalshiBook", "__version__"]
```

**Rationale:**
- `__version__` exposed at top level for `kalshibook.__version__` access
- `KalshiBook` imported at package level so `from kalshibook import KalshiBook` works
- `__all__` controls `from kalshibook import *` behavior (explicit is better)
- Future phases add exceptions, models to `__all__` as they're implemented
- `from __future__ import annotations` for PEP 604 union syntax on Python 3.10

### Pattern 5: Empty KalshiBook Class Stub

**What:** Minimal class in `client.py` that can be imported. No logic.

**Example:**
```python
"""KalshiBook client -- query L2 orderbook data for Kalshi prediction markets."""

from __future__ import annotations


class KalshiBook:
    """Client for the KalshiBook API.

    Provides sync and async access to historical orderbook data,
    trades, candles, events, and settlements for Kalshi prediction markets.

    Usage::

        from kalshibook import KalshiBook

        client = KalshiBook(api_key="kb-...")

    Parameters
    ----------
    api_key : str, optional
        KalshiBook API key. If not provided, reads from KALSHIBOOK_API_KEY env var.
    sync : bool, optional
        If True, use synchronous HTTP transport. Default False (async).
    """

    pass
```

### Pattern 6: PEP 561 py.typed Marker

**What:** An empty file at `sdk/src/kalshibook/py.typed` signals to mypy and other type checkers that this package includes inline type annotations.

**Requirements:**
- File must be named exactly `py.typed`
- File must be empty (or contain just a newline)
- File must be inside the package directory (alongside `__init__.py`)
- uv_build automatically includes it in the wheel/sdist when using src layout

### Anti-Patterns to Avoid

- **Root and SDK sharing the same project name:** uv cannot resolve two workspace members with identical `[project] name`. Rename root to `kalshibook-server`.
- **Flat layout (module at project root):** uv_build defaults to src layout. Using flat layout requires `module-root = ""` override and risks accidental imports of the uninstalled source tree during testing.
- **Over-pinning dependencies:** `httpx>=0.27,<0.29` would break when httpx 0.29 releases. Use `httpx>=0.27` with no upper bound. Let users' pip resolver handle compatibility.
- **Adding Pydantic as a dependency:** Even for the SDK's own config, avoid Pydantic. It adds 2MB+ and creates pydantic-core version conflicts. Use stdlib dataclasses.
- **Creating a nested package structure:** `kalshibook.resources.orderbook.client` is over-engineering for 10 endpoints. Keep flat.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Build system | Custom setup.py / setuptools config | uv_build | Zero-config for src layout, native to uv |
| Package discovery | Manual MANIFEST.in / package_data | uv_build auto-discovery | uv_build discovers packages in src/ layout automatically |
| Workspace dependency resolution | Manual pip install -e across packages | uv workspaces | Shared lockfile, automatic editable installs |
| Type stub distribution | Separate -stubs package | py.typed marker + inline annotations | PEP 561 inline typing is the modern standard for packages with type hints |

**Key insight:** The build tooling (uv_build + uv workspaces) handles the complexity of monorepo packaging. The SDK's job is to define correct metadata in `pyproject.toml` and correct module structure in `src/kalshibook/`. Everything else is automatic.

## Common Pitfalls

### Pitfall 1: Workspace Name Collision

**What goes wrong:** Adding `sdk/pyproject.toml` with `name = "kalshibook"` while root also has `name = "kalshibook"` causes uv to fail during resolution -- it cannot distinguish two packages with the same name.
**Why it happens:** The root was named "kalshibook" before the SDK existed. No one anticipated the namespace split.
**How to avoid:** Rename root project to `kalshibook-server` before creating the SDK member. This is a metadata-only change (no code changes, no import path changes).
**Warning signs:** `uv sync` errors mentioning duplicate package names or resolution conflicts.

### Pitfall 2: Wrong Module Path for uv_build

**What goes wrong:** uv_build cannot find the package module, producing an empty wheel with no Python files.
**Why it happens:** uv_build expects `sdk/src/kalshibook/__init__.py` by default (src layout, normalized project name). If the directory is named differently (e.g., `sdk/kalshibook/` without `src/`), the build silently produces an empty package.
**How to avoid:** Use exact path `sdk/src/kalshibook/__init__.py`. The project name "kalshibook" normalizes to directory name "kalshibook". The src layout is uv_build's default.
**Warning signs:** `uv build` succeeds but the wheel contains no `.py` files. Verify with `unzip -l dist/*.whl`.

### Pitfall 3: requires-python Intersection Surprise

**What goes wrong:** SDK declares `>=3.10` but `uv sync` at workspace root resolves dependencies for `>=3.12` (the root's constraint), causing some SDK-compatible but Python-3.10-only dependencies to be excluded from the lockfile.
**Why it happens:** uv workspaces take the intersection of all members' `requires-python`. The intersection of `>=3.12` and `>=3.10` is `>=3.12`.
**How to avoid:** This is expected behavior. The lockfile governs local development only (which uses 3.12+). The published SDK's `pyproject.toml` independently declares `>=3.10` for PyPI consumers. Test SDK compatibility on Python 3.10 in CI using a separate virtual environment, not the workspace lockfile.
**Warning signs:** CI tests on Python 3.10 fail with missing dependencies. Use `uv pip install` in a fresh 3.10 venv for CI testing.

### Pitfall 4: Server Code Leaking into SDK Distribution

**What goes wrong:** The published SDK wheel contains server files (`src/api/`, `src/collector/`, `src/shared/`).
**Why it happens:** Misconfigured package discovery or build system includes files outside `sdk/src/kalshibook/`.
**How to avoid:** uv_build with src layout only includes `sdk/src/kalshibook/`. The root `src/` is completely separate -- it's not even under the SDK's directory tree. Verify after build: `unzip -l dist/*.whl | grep -v kalshibook` should show only metadata files.
**Warning signs:** Large wheel size (server code adds significant weight), import errors from server-only dependencies (asyncpg, fastapi).

### Pitfall 5: Missing py.typed in Distribution

**What goes wrong:** mypy users get "error: Skipping analyzing 'kalshibook': module is installed, but missing library stubs or py.typed marker."
**Why it happens:** `py.typed` file created but not included in the wheel. Some build backends require explicit `package_data` configuration.
**How to avoid:** uv_build automatically includes all files in the package directory, including `py.typed`. No explicit configuration needed. Verify: `unzip -l dist/*.whl | grep py.typed` should show the marker file.
**Warning signs:** mypy warnings about missing stubs when importing `kalshibook` in consumer projects.

## Code Examples

### Root pyproject.toml Changes

```toml
# Changes to existing root pyproject.toml:

[project]
name = "kalshibook-server"  # CHANGED from "kalshibook"
# ... rest unchanged ...

# NEW section:
[tool.uv.workspace]
members = ["sdk"]
```

### SDK pyproject.toml (Complete)

```toml
[project]
name = "kalshibook"
version = "0.1.0"
description = "Python SDK for the KalshiBook L2 orderbook data API"
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
authors = [{ name = "KalshiBook" }]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Intended Audience :: Financial and Insurance Industry",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Typing :: Typed",
]
dependencies = [
    "httpx>=0.27",
]

[project.optional-dependencies]
pandas = ["pandas>=2.0"]

[build-system]
requires = ["uv_build>=0.10.3,<0.11.0"]
build-backend = "uv_build"

[dependency-groups]
dev = [
    "pytest>=9.0",
    "pytest-asyncio>=1.0",
    "pytest-httpx>=0.35",
    "mypy>=1.10",
    "ruff>=0.15",
]

[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.mypy]
python_version = "3.10"
strict = true
```

### SDK __init__.py

```python
"""KalshiBook Python SDK -- L2 orderbook data for Kalshi prediction markets."""

from __future__ import annotations

__version__ = "0.1.0"

from kalshibook.client import KalshiBook

__all__ = ["KalshiBook", "__version__"]
```

### SDK client.py (Stub)

```python
"""KalshiBook client -- query L2 orderbook data for Kalshi prediction markets."""

from __future__ import annotations


class KalshiBook:
    """Client for the KalshiBook API.

    Provides sync and async access to historical orderbook data,
    trades, candles, events, and settlements for Kalshi prediction markets.

    Usage::

        from kalshibook import KalshiBook

        client = KalshiBook(api_key="kb-...")

    Parameters
    ----------
    api_key : str, optional
        KalshiBook API key. If not provided, reads from KALSHIBOOK_API_KEY env var.
    sync : bool, optional
        If True, use synchronous HTTP transport. Default False (async).
    """

    pass
```

### Verification Script

```bash
#!/bin/bash
# Verify all Phase 8 success criteria

set -e

echo "1. pip install -e ./sdk"
pip install -e ./sdk

echo "2. Import test"
python3 -c "from kalshibook import KalshiBook; print('OK:', KalshiBook)"

echo "3. uv sync"
uv sync

echo "4. Check no server code in distribution"
cd sdk && uv build
unzip -l dist/*.whl | grep -v kalshibook | grep -v '\.dist-info' | grep '\.py$' && echo "FAIL: non-SDK files found" || echo "OK: clean distribution"
cd ..

echo "5. py.typed marker"
python3 -c "
import importlib.resources
import kalshibook
path = importlib.resources.files(kalshibook) / 'py.typed'
assert path.is_file(), 'py.typed not found'
print('OK: py.typed present')
"

echo "All checks passed!"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| setuptools + setup.py | pyproject.toml + uv_build | 2024-2025 | uv_build is zero-config for src layout; no setup.py/setup.cfg needed |
| MANIFEST.in for file inclusion | Automatic discovery by uv_build | 2024-2025 | No manual file listing; all files under package dir included |
| pip + virtualenv + twine | uv (single tool) | 2024-2025 | uv handles venv, install, build, publish in one binary |
| Separate repos for API + SDK | Monorepo with uv workspaces | 2024-2025 | Atomic changes, shared lockfile, test SDK against API directly |
| type stubs in separate packages | py.typed + inline annotations (PEP 561) | 2019+ | No separate -stubs package needed for first-party typed code |

**Deprecated/outdated:**
- `setup.py` / `setup.cfg`: Replaced by `pyproject.toml`. Still works but no reason to use for new projects.
- `MANIFEST.in`: Not needed with uv_build (automatic file discovery).
- `twine upload`: Replaced by `uv publish` with PyPI Trusted Publishing.

## Open Questions

1. **SDK README.md content**
   - What we know: PyPI displays README.md. The SDK needs its own README separate from the root.
   - What's unclear: How much to include in Phase 8 vs Phase 12 (documentation phase).
   - Recommendation: Create a minimal `sdk/README.md` with package name, one-line description, and "coming soon" note. Full content in Phase 12.

2. **SDK test directory structure**
   - What we know: SDK tests live at `sdk/tests/`. Root server tests are at `tests/`.
   - What's unclear: Whether to create test stubs in Phase 8 or wait for Phase 9 when there's logic to test.
   - Recommendation: Create `sdk/tests/__init__.py` and one smoke test (`test_import.py`) that verifies `from kalshibook import KalshiBook` works. More tests come in Phase 9+.

3. **License file location**
   - What we know: `pyproject.toml` declares `license = "MIT"`. PyPI expects a LICENSE file.
   - What's unclear: Whether the SDK uses a separate LICENSE or references the root.
   - Recommendation: Create `sdk/LICENSE` with standard MIT text. The SDK ships independently; it needs its own license file in the wheel.

## Sources

### Primary (HIGH confidence)
- [uv Workspaces Documentation](https://docs.astral.sh/uv/concepts/projects/workspaces/) -- workspace configuration, members, shared lockfile, requires-python intersection
- [uv Build Backend Documentation](https://docs.astral.sh/uv/concepts/build-backend/) -- uv_build configuration, src layout, package discovery
- [uv Project Configuration](https://docs.astral.sh/uv/concepts/projects/config/) -- pyproject.toml options, optional dependencies, dev groups
- [PEP 561 / Python Typing Spec](https://typing.python.org/en/latest/spec/distributing.html) -- py.typed marker requirements
- [Python dataclasses documentation](https://docs.python.org/3/library/dataclasses.html) -- slots=True requires Python 3.10+
- KalshiBook root `pyproject.toml` (direct inspection) -- confirmed no `[build-system]`, name is "kalshibook", server imports via `from src.api...`
- KalshiBook `uv.lock` (direct inspection) -- confirmed root is `source = { virtual = "." }`, not a built package
- KalshiBook server source code (direct inspection) -- all imports use `from src.api...` / `from src.shared...` / `from src.collector...`, not `from kalshibook...`

### Secondary (MEDIUM confidence)
- [httpx PyPI page](https://pypi.org/project/httpx/) -- version 0.28.1, requires Python >=3.8
- Prior project research at `.planning/research/ARCHITECTURE.md` -- SDK module layout, monorepo structure rationale
- Prior project research at `.planning/research/SUMMARY.md` -- stack decisions, feature scope, pitfalls

### Tertiary (LOW confidence)
- None. All findings verified with primary sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- uv_build and uv workspaces are thoroughly documented with clear examples
- Architecture: HIGH -- module structure verified against uv_build defaults and successful Python SDKs (Polygon, Tavily)
- Pitfalls: HIGH -- naming collision verified by inspecting current pyproject.toml and uv.lock; requires-python intersection documented in official uv docs

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (stable tooling, 30-day window appropriate)
