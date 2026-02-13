# Testing Patterns

**Analysis Date:** 2026-02-13

## Test Framework

**Runner:**
- Node.js native `test` module (no external framework)
- Import: `const { test, describe, beforeEach, afterEach } = require('node:test');`
- Config: No separate config file needed (uses Node.js built-in)
- Version: Node.js 18+ (when `node:test` became stable)

**Assertion Library:**
- Node.js native `assert` module: `const assert = require('node:assert');`
- Methods used: `assert.ok()`, `assert.strictEqual()`, `assert.deepStrictEqual()`

**Run Commands:**
```bash
node .claude/get-shit-done/bin/gsd-tools.test.js     # Run all tests
npm test                                              # If npm script configured (none detected)
```

**Test Execution:**
- Tests run synchronously in order
- Tests execute as subprocess via `execSync()` to test CLI behavior realistically
- Helper function `runGsdTools()` captures both stdout and stderr

## Test File Organization

**Location:**
- Co-located with implementation: `gsd-tools.js` and `gsd-tools.test.js` in same directory
- Path: `.claude/get-shit-done/bin/gsd-tools.test.js` (2033 lines)

**Naming:**
- Test file: `.test.js` suffix
- Pattern: `<module>.test.js` not `<module>.spec.js`

**Structure:**
```
.claude/get-shit-done/bin/
├── gsd-tools.js         # Implementation (4503 lines)
├── gsd-tools.test.js    # Tests (2033 lines)
└── [other utilities]
```

## Test Structure

**Suite Organization:**
```javascript
describe('history-digest command', () => {
  let tmpDir;

  beforeEach(() => {
    tmpDir = createTempProject();
  });

  afterEach(() => {
    cleanup(tmpDir);
  });

  test('empty phases directory returns valid schema', () => {
    const result = runGsdTools('history-digest', tmpDir);
    assert.ok(result.success, `Command failed: ${result.error}`);
    const digest = JSON.parse(result.output);
    assert.deepStrictEqual(digest.phases, {}, 'phases should be empty object');
  });

  test('nested frontmatter fields extracted correctly', () => {
    // Create test file structure
    const phaseDir = path.join(tmpDir, '.planning', 'phases', '01-foundation');
    fs.mkdirSync(phaseDir, { recursive: true });
    fs.writeFileSync(path.join(phaseDir, '01-01-SUMMARY.md'), summaryContent);

    // Run command and assert
    const result = runGsdTools('history-digest', tmpDir);
    assert.ok(result.success, `Command failed: ${result.error}`);
    const digest = JSON.parse(result.output);
    assert.deepStrictEqual(digest.phases['01'].provides, [...]);
  });
});
```

**Patterns:**

1. **Setup (beforeEach):**
   - Creates temporary project directory structure
   - Calls `createTempProject()` which initializes `.planning/phases/` directory
   - All file system state starts fresh for each test

2. **Teardown (afterEach):**
   - Calls `cleanup(tmpDir)` to recursively delete temp directory
   - Ensures no test artifacts left behind
   - Prevents file descriptor leaks

3. **Assertion Pattern:**
   - Always check `result.success` first: `assert.ok(result.success, \`Command failed: ${result.error}\`)`
   - Error message includes captured stderr from failed command
   - Multiple assertions per test allowed but grouped logically

**Helper Functions (gsd-tools.test.js, lines 13-40):**

```javascript
// Execute gsd-tools command, capture stdout/stderr
function runGsdTools(args, cwd = process.cwd()) {
  try {
    const result = execSync(`node "${TOOLS_PATH}" ${args}`, {
      cwd,
      encoding: 'utf-8',
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    return { success: true, output: result.trim() };
  } catch (err) {
    return {
      success: false,
      output: err.stdout?.toString().trim() || '',
      error: err.stderr?.toString().trim() || err.message,
    };
  }
}

// Create isolated temp project with .planning/phases structure
function createTempProject() {
  const tmpDir = fs.mkdtempSync(path.join(require('os').tmpdir(), 'gsd-test-'));
  fs.mkdirSync(path.join(tmpDir, '.planning', 'phases'), { recursive: true });
  return tmpDir;
}

// Clean up after test
function cleanup(tmpDir) {
  fs.rmSync(tmpDir, { recursive: true, force: true });
}
```

## Mocking

**Framework:** None. Tests use real file system with isolated temp directories.

**Patterns:**
- File system mocking: Uses `fs.mkdtempSync()` to create isolated temp directories per test
- No `fs` or `child_process` mocks - executes `gsd-tools` as actual subprocess
- Avoids mocking to test realistic CLI behavior and integration paths

**What to Mock:**
- Not applicable - isolation via temporary directories and subprocess execution
- Only actual file I/O tested, not stubbed

**What NOT to Mock:**
- File system operations (always real, isolated)
- subprocess execution via `execSync()` (always real)
- Git commands (always real via subprocess, test responsibility to initialize git repo if needed)

**Test Data Creation:**
- File content written directly via `fs.writeFileSync()`
- Directory structures created via `fs.mkdirSync()`
- SUMMARY.md frontmatter written as multi-line strings

## Fixtures and Factories

**Test Data:**

Test fixtures created inline using template strings. Example from gsd-tools.test.js (lines 69-91):

```javascript
const summaryContent = `---
phase: "01"
name: "Foundation Setup"
dependency-graph:
  provides:
    - "Database schema"
    - "Auth system"
  affects:
    - "API layer"
tech-stack:
  added:
    - "prisma"
    - "jose"
patterns-established:
  - "Repository pattern"
  - "JWT auth flow"
key-decisions:
  - "Use Prisma over Drizzle"
  - "JWT in httpOnly cookies"
---

# Summary content here
`;

fs.writeFileSync(path.join(phaseDir, '01-01-SUMMARY.md'), summaryContent);
```

**Multiple Phase Fixtures (lines 137-175):**

Creates separate phase directories with distinct content:
```javascript
// Create phase 01
const phase01Dir = path.join(tmpDir, '.planning', 'phases', '01-foundation');
fs.mkdirSync(phase01Dir, { recursive: true });
fs.writeFileSync(path.join(phase01Dir, '01-01-SUMMARY.md'), `---
phase: "01"
name: "Foundation"
provides: ["Database"]
---`);

// Create phase 02
const phase02Dir = path.join(tmpDir, '.planning', 'phases', '02-api');
fs.mkdirSync(phase02Dir, { recursive: true });
fs.writeFileSync(path.join(phase02Dir, '02-01-SUMMARY.md'), `---
phase: "02"
name: "API"
provides: ["REST endpoints"]
tech-stack:
  added: ["zod"]
---`);
```

**Location:**
- Fixtures created inline within test functions
- No separate fixtures directory (kept with related tests)
- Temp directories are test-scoped and cleaned up after

## Coverage

**Requirements:** No coverage requirements enforced (no configuration found)

**View Coverage:** Not configured - no coverage tool setup detected

**Approach:** Test most command paths with explicit test cases per command function

## Test Types

**Unit Tests:**
- Testing frontmatter extraction/reconstruction logic
- Testing phase number normalization
- Testing slug generation
- Testing config loading with defaults
- Scope: Single functions in isolation via CLI subprocess

**Integration Tests:**
- Testing full command execution: `history-digest`, `phases list`, `roadmap get-phase`, `phase next-decimal`
- Testing file system state changes: Creating phases, writing SUMMARY.md, reading ROADMAP.md
- Testing nested frontmatter parsing from real YAML-like syntax
- Scope: Full command flow including file I/O

**E2E Tests:**
- Not explicitly separated; tests execute actual CLI commands via subprocess
- Every test is semi-E2E because it runs the real tool
- Tests verify both command output and filesystem side effects

**Test Suite Organization (from gsd-tools.test.js):**

| Test Group | Tests | Focus |
|-----------|-------|-------|
| history-digest | 6 | Frontmatter parsing, aggregation, malformed file handling |
| phases list | 5 | Phase directory discovery, filtering, sorting |
| roadmap get-phase | 5 | Phase section extraction from ROADMAP.md |
| phase next-decimal | 5 | Decimal phase number calculation |
| phase-plan-index | 5 | Plan indexing, wave grouping, status detection |
| state-snapshot | 4 | STATE.md parsing and field extraction |

## Common Patterns

**Async Testing:**
- Not used - all tests are synchronous
- `execSync()` blocks on subprocess completion, no Promise/await

**Error Testing:**

Testing error conditions and graceful degradation:

```javascript
test('malformed SUMMARY.md skipped gracefully', () => {
  // Create temp directory with valid AND invalid files
  const phaseDir = path.join(tmpDir, '.planning', 'phases', '01-test');
  fs.mkdirSync(phaseDir, { recursive: true });

  // Valid summary
  fs.writeFileSync(path.join(phaseDir, '01-01-SUMMARY.md'), `---
phase: "01"
provides: ["Valid feature"]
---`);

  // Malformed summary (no frontmatter)
  fs.writeFileSync(path.join(phaseDir, '01-02-SUMMARY.md'), `# Just a heading
No frontmatter here`);

  // Malformed summary (broken YAML)
  fs.writeFileSync(path.join(phaseDir, '01-03-SUMMARY.md'), `---
broken: [unclosed
---`);

  // Run command - should still succeed
  const result = runGsdTools('history-digest', tmpDir);
  assert.ok(result.success, `Command should succeed despite malformed files: ${result.error}`);

  // Verify valid data extracted despite invalid files
  const digest = JSON.parse(result.output);
  assert.ok(digest.phases['01'], 'Phase 01 should exist');
  assert.ok(digest.phases['01'].provides.includes('Valid feature'), 'Valid feature extracted');
});
```

**Backward Compatibility Testing:**

```javascript
test('flat provides field still works (backward compatibility)', () => {
  const phaseDir = path.join(tmpDir, '.planning', 'phases', '01-test');
  fs.mkdirSync(phaseDir, { recursive: true });

  // Old format: flat provides array
  fs.writeFileSync(path.join(phaseDir, '01-01-SUMMARY.md'), `---
phase: "01"
provides:
  - "Direct provides"
---`);

  const result = runGsdTools('history-digest', tmpDir);
  assert.ok(result.success, `Command failed: ${result.error}`);
  const digest = JSON.parse(result.output);
  assert.deepStrictEqual(digest.phases['01'].provides, ['Direct provides'], 'Direct provides should work');
});
```

**Inline Array Syntax Testing:**

```javascript
test('inline array syntax supported', () => {
  const phaseDir = path.join(tmpDir, '.planning', 'phases', '01-test');
  fs.mkdirSync(phaseDir, { recursive: true });

  // Inline array format
  fs.writeFileSync(path.join(phaseDir, '01-01-SUMMARY.md'), `---
phase: "01"
provides: [Feature A, Feature B]
patterns-established: ["Pattern X", "Pattern Y"]
---`);

  const result = runGsdTools('history-digest', tmpDir);
  assert.ok(result.success);
  const digest = JSON.parse(result.output);
  assert.deepStrictEqual(digest.phases['01'].provides.sort(), ['Feature A', 'Feature B']);
  assert.deepStrictEqual(digest.phases['01'].patterns.sort(), ['Pattern X', 'Pattern Y']);
});
```

## Test Characteristics

**Isolation:**
- Each test gets fresh temp directory via `beforeEach`
- No shared state between tests
- Cleanup via `afterEach` ensures no filesystem pollution

**Reproducibility:**
- Tests create all required file structures
- No external dependencies or environment variables required
- Same test run multiple times produces identical results

**Clarity:**
- Assertion messages included with test name
- Error output includes captured command stderr
- Test describes specific behavior (e.g., "nested frontmatter fields extracted correctly")

**Maintainability:**
- Fixtures created inline (easy to see what test data looks like)
- Helper functions (`runGsdTools`, `createTempProject`, `cleanup`) reduce boilerplate
- Test groups organized by command being tested

---

*Testing analysis: 2026-02-13*
