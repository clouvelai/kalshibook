# Coding Conventions

**Analysis Date:** 2026-02-13

## Naming Patterns

**Files:**
- Kebab-case for executable scripts and test files: `gsd-tools.js`, `gsd-tools.test.js`, `gsd-check-update.js`, `gsd-statusline.js`
- Matches shell command naming conventions for direct CLI tools
- Test files use `.test.js` suffix (not `.spec.js`)

**Functions:**
- camelCase for all function names: `parseIncludeFlag()`, `loadConfig()`, `isGitIgnored()`, `normalizePhaseName()`
- Descriptive, action-oriented names: `execGit()`, `extractFrontmatter()`, `reconstructFrontmatter()`, `spliceFrontmatter()`
- Helper functions prefixed with descriptive verb: `safeReadFile()`, `stateExtractField()`, `stateReplaceField()`

**Variables:**
- camelCase for all variables and constants: `frontmatter`, `currentStatus`, `phaseDir`, `tmpDir`
- SCREAMING_SNAKE_CASE for module-level constants: `MODEL_PROFILES`, `TOOLS_PATH`
- Single-letter loop variables acceptable in tight scopes: `a` in map/filter callbacks, `e` in catch blocks

**Types & Data Structures:**
- Object keys use snake_case for YAML/frontmatter: `dependency-graph`, `tech-stack`, `patterns-established`, `key-decisions`, `update_available`
- Model profile keys use snake_case: `model_profile`, `commit_docs`, `branching_strategy`, `phase_branch_template`
- JSON config files consistently use snake_case across all sections

## Code Style

**Formatting:**
- No formatter detected (no Prettier/ESLint config found)
- 2-space indentation (standard for Node.js)
- Semicolons required (except in catches: `} catch {}`)
- String quotes: Single quotes preferred in most code (`'utf-8'`, `'../path'`)
- Template literals used for string interpolation: `` `Error: ${message}` ``

**Linting:**
- No ESLint configuration detected
- No explicit linting rules enforced
- Code follows consistent Node.js patterns by convention

**Line Length:**
- Typical lines stay under 100 characters
- Function documentation comments wrap to logical boundaries
- Long string replacements stay on single line when reasonable

## Import Organization

**Order:**
1. Node built-in modules (`fs`, `path`, `child_process`)
2. Third-party modules (none in core codebase)
3. Local imports (not used; scripts are monolithic)

**Examples from `gsd-tools.js` (lines 117-119):**
```javascript
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
```

**Examples from `gsd-tools.test.js` (lines 5-9):**
```javascript
const { test, describe, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
```

**Path Aliases:**
- No alias system used (CommonJS require with relative/absolute paths)
- Paths resolved via `path.join()` for cross-platform compatibility

## Error Handling

**Patterns:**
- Catch-and-return pattern for recoverable errors: `try/catch` returning `null` or default value
- Catch-and-exit pattern for fatal errors: `error()` function writes to stderr and calls `process.exit(1)`
- Silent catch blocks for non-critical operations: `catch {}` or `catch (e) {}` when error is not logged
- Graceful degradation: Malformed files skipped, partial results returned

**Examples:**
```javascript
// Recoverable - returns null on failure
function safeReadFile(filePath) {
  try {
    return fs.readFileSync(filePath, 'utf-8');
  } catch {
    return null;
  }
}

// Fatal - exits with error
function error(message) {
  process.stderr.write('Error: ' + message + '\n');
  process.exit(1);
}

// Non-critical - silent fail
try {
  // operation
} catch {}
```

**Error Messages:**
- Use `Error: ` prefix for CLI errors (not thrown Error objects)
- Messages describe what went wrong and sometimes suggest fix: `Error: text required for slug generation`
- Exit code 1 for all errors (no error code differentiation)

## Logging

**Framework:** None. No `console.*` usage detected.

**Output Pattern:**
- Single `output()` function (line 462) handles all CLI output
- `process.stdout.write()` for normal output
- `process.stderr.write()` for errors
- JSON output for structured data, raw mode for text output

**Usage Pattern:**
```javascript
function output(result, raw, rawValue) {
  if (raw && rawValue !== undefined) {
    process.stdout.write(String(rawValue));
  } else {
    process.stdout.write(JSON.stringify(result, null, 2));
  }
  process.exit(0);
}
```

**Logging Philosophy:**
- Commands output only final results (JSON or text)
- No intermediate logging or debug output
- All errors written to stderr before exit
- Supports `--raw` flag for shell-friendly output

## Comments

**When to Comment:**
- Block comments explaining complex algorithms: YAML frontmatter parser (lines 248-321)
- Inline comments for non-obvious logic: Stack management in nested object parsing
- Section headers with dashes for major code blocks: `// ─── Commands ─────────────────────────────`
- No comments for self-evident code

**JSDoc Usage:**
- Not used in this codebase
- Single-line block comments used for complex functions
- All function signatures assumed self-documenting via name

**Example Block Comment (lines 256-257):**
```javascript
  // Stack to track nested objects: [{obj, key, indent}]
  // obj = object to write to, key = current key collecting array items, indent = indentation level
```

## Function Design

**Size:**
- Functions range 5-150 lines typically
- Larger functions (200+ lines) are command implementations that deserve their size
- Helper functions kept focused and small
- `extractFrontmatter()` at 72 lines (complex parser, warranted)
- `cmdHistoryDigest()` at ~80 lines (orchestrates multiple file operations)

**Parameters:**
- Typically 1-3 parameters maximum
- Command functions follow pattern: `cmd<Name>(cwd, arg1, arg2, ..., raw)`
- `cwd` always first parameter (working directory context)
- `raw` always last parameter (output format flag)
- Options passed as single object when multiple flags needed

**Return Values:**
- No explicit returns in command functions (use `output()` for result)
- Helper functions return data structures or null
- No Promise usage (synchronous only)

**Examples:**
```javascript
// Command pattern - no return, calls output()
function cmdGenerateSlug(text, raw) {
  const slug = text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  const result = { slug };
  output(result, raw, slug);
}

// Helper pattern - returns data
function loadConfig(cwd) {
  // ...
  return {
    model_profile: get('model_profile') ?? defaults.model_profile,
    // ...
  };
}
```

## Module Design

**Exports:**
- No module.exports used (CLI entry point only)
- Functions called via dispatch in `main()` function (line 4503)
- All commands accessible via command-line arguments parsed at entry point

**Barrel Files:**
- Not applicable (monolithic script approach)

**Organization Pattern:**
```
1. Imports (lines 117-119)
2. Constants (lines 123-135)
3. Helper functions (lines 139-460)
4. Command functions (lines 478+)
5. Main dispatch switch (lines 4000+)
6. Entry point (line 4503)
```

**Module-Level Constants:**
```javascript
const MODEL_PROFILES = {
  'gsd-planner': { quality: 'opus', balanced: 'opus', budget: 'sonnet' },
  'gsd-codebase-mapper': { quality: 'sonnet', balanced: 'haiku', budget: 'haiku' },
  // ...
};
```

## String Handling

**Quote Style:**
- Single quotes preferred for simple strings
- Template literals for interpolation: `` require(`path/to/${file}`) ``
- Double quotes used in JSON output to maintain validity

**YAML String Handling:**
- Automatic quote removal in frontmatter parser: `.replace(/^["']|["']$/g, '')`
- Automatic quote addition for YAML values containing colons or hashes
- Preserves quoted strings in arrays

## Error Recovery

**Malformed Input Handling:**
- Gracefully skips invalid SUMMARY.md files in phase directories
- Empty directory returns empty result (not error)
- Missing config files use sensible defaults
- Partial results returned rather than complete failure

**Example (gsd-tools.test.js, line 193):**
```javascript
test('malformed SUMMARY.md skipped gracefully', () => {
  // Valid and invalid files in same phase
  // Result: valid features extracted, invalid skipped
  assert.ok(result.success, `Command should succeed despite malformed files`);
});
```

---

*Convention analysis: 2026-02-13*
