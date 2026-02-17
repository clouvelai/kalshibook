# Phase 7: v1 Cleanup & Polish - Research

**Researched:** 2026-02-16
**Domain:** Tech debt closure -- client-side validation, dead code removal, documentation traceability
**Confidence:** HIGH

## Summary

Phase 7 is a focused cleanup phase that closes three categories of gaps identified in the v1 Milestone Audit (`v1-MILESTONE-AUDIT.md`). There is no new feature work -- all three work items are well-scoped fixes to existing code and documentation.

The three deliverables are: (1) adding client-side timestamp validation to the API Playground so users get a helpful error instead of a raw 422, (2) removing two pieces of orphaned dead code (the `PaygToggle` component and the `SeriesRecord`/`SeriesResponse` Pydantic models), and (3) updating `REQUIREMENTS.md` to reflect the current state of the project (adding BKTS-01-04, moving STRM-01/02 to v2, noting Phase 6 coverage, and updating all statuses from "Pending" to "Complete").

**Primary recommendation:** Execute as a single plan with three clearly separated task groups. All changes are low-risk, independent, and require no new dependencies.

## Standard Stack

No new libraries or dependencies are needed. All work uses existing project infrastructure.

### Core (already in project)
| Library | Version | Purpose | Relevance |
|---------|---------|---------|-----------|
| Next.js 15 | current | Dashboard framework | Playground lives here |
| React 19 | current | Component library | Form validation UI |
| FastAPI | current | Backend API | Defines `OrderbookRequest` model |
| Pydantic v2 | current | API models | `SeriesRecord`/`SeriesResponse` live here |
| shadcn/ui | current | UI components | Form error display |

### Alternatives Considered
None. No new dependencies needed for this phase.

## Architecture Patterns

### Pattern 1: Client-side Validation Before Send

**What:** Add validation in `usePlayground.sendRequest()` that checks `timestamp` is non-empty before making the API call. Display a validation error inline in the form.

**Current behavior (bug):**
- `playground-form.tsx` line 58: `canSend` only checks `revealedKey` and `marketTicker` -- timestamp is NOT checked
- `use-playground.ts` lines 227-229: `sendRequest()` only adds `timestamp` to body if truthy (`if (timestamp) body.timestamp = timestamp`)
- Backend `OrderbookRequest` model (`src/api/models.py` line 17): `timestamp: datetime = Field(...)` -- this is a **required** field (no default, no Optional)
- Result: submitting without timestamp sends `{"market_ticker": "..."}`, backend returns 422 Unprocessable Entity

**Fix approach:**
```typescript
// In use-playground.ts sendRequest():
if (!timestamp.trim()) {
  setRequestError("Timestamp is required. Enter an ISO 8601 timestamp (e.g., 2025-02-14T18:00:00Z).");
  return;
}
```

Additionally, update the form UI:
- Make the timestamp field visible by default (not hidden under "Additional fields" accordion) since it is required
- Add the required indicator (`*`) to the Timestamp label, matching the Market Ticker pattern
- Display `requestError` in the playground page (currently the state exists but is never rendered)

**Key files:**
- `dashboard/src/components/playground/use-playground.ts` -- add validation in `sendRequest()`
- `dashboard/src/components/playground/playground-form.tsx` -- promote timestamp to required field, show error
- `dashboard/src/app/(dashboard)/playground/page.tsx` -- render `requestError` if not null
- `dashboard/src/types/api.ts` line 74 -- change `timestamp?: string` to `timestamp: string` to match backend

### Pattern 2: Dead Code Removal

**What:** Delete orphaned files and model classes that are not imported or used anywhere.

**PaygToggle component:**
- File: `dashboard/src/components/billing/payg-toggle.tsx`
- Status: **Orphaned dead code** -- never imported anywhere in the project
- The PAYG toggle functionality is fully implemented inline in `dashboard/src/components/billing/usage-bar.tsx` (lines 36-55, 117-131)
- The `UsageBar` component has its own `handlePaygToggle` function that calls `api.billing.togglePayg()` directly
- Safe to delete: no imports reference `payg-toggle.tsx`

**SeriesRecord/SeriesResponse models:**
- Location: `src/api/models.py` lines 401-415
- Status: **Orphaned dead code** -- defined but never imported by any route
- The `series` table exists in the database (migration `20260216000003_create_events_series.sql`)
- The collector writes to the `series` table via `writer.py` line 135
- BUT there is no `/series` API route -- no file in `src/api/routes/` imports these models
- The events route (`src/api/routes/events.py`) supports filtering by `series_ticker` but does not use `SeriesRecord`/`SeriesResponse`
- **Decision:** Remove models. If a `/series` endpoint is added in v2, models can be recreated from the existing table schema.

**Files to delete:**
- `dashboard/src/components/billing/payg-toggle.tsx` (entire file)

**Code to remove from existing file:**
- `src/api/models.py` lines 401-415 (`SeriesRecord` and `SeriesResponse` classes)

### Pattern 3: REQUIREMENTS.md Traceability Update

**What:** Update `REQUIREMENTS.md` to reflect the current state of all requirements after 6 completed phases.

**Current problems (from audit):**
1. BKTS-01 through BKTS-04 are used in the roadmap (Phase 4) but never added to REQUIREMENTS.md
2. STRM-01/02 are already in the v2 section, and the coverage note says "STRM-01/02 moved to v2" -- but the traceability table still has them nowhere (they were never in the traceability table)
3. Phase 6 (API Playground) requirements are not tracked at all
4. All statuses in the traceability table say "Pending" -- none are marked "Complete"
5. The "Last updated" date is 2026-02-13

**Required changes to REQUIREMENTS.md:**

1. **Add Backtesting section under v1 Requirements:**
```markdown
### Backtesting

- [x] **BKTS-01**: Collector captures public trade executions and trade history is queryable via API
- [x] **BKTS-02**: Settlement/resolution data normalized and queryable
- [x] **BKTS-03**: Candlestick data available at 1m, 1h, 1d intervals
- [x] **BKTS-04**: Event/market hierarchy exposed via API
```

2. **Add Playground section under v1 Requirements (Phase 6 coverage):**
   Phase 6 delivered the API Playground but was added after the initial requirements. The playground is a DEVX feature, not a separately tracked requirement. Optionally note Phase 6 in the existing DEVX section or add a brief note.

3. **Update traceability table:**
   - Add BKTS-01-04 mapped to Phase 4, status Complete
   - Update all existing requirement statuses from "Pending" to "Complete"
   - Add note about Phase 6 (playground) coverage
   - Update coverage count: 34 requirements total (30 original + 4 BKTS), 32 v1 Complete, 2 in v2

4. **Update the "Last updated" date**

### Anti-Patterns to Avoid

- **Over-engineering the validation:** Do not add a form validation library (zod, react-hook-form) for a single required field check. A simple string emptiness check in the hook is sufficient.
- **Moving timestamp to a different UI position AND changing behavior:** The fix should be minimal -- make the field visible and required. Do not redesign the form layout.
- **Removing PaygToggleResponse type:** The `PaygToggleResponse` type in `dashboard/src/types/api.ts` (line 64) and the `api.billing.togglePayg()` function in `dashboard/src/lib/api.ts` are **NOT dead code** -- they are actively used by `UsageBar`. Only the component file is dead.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Form validation | Validation library | Simple string check in hook | Single field, not worth the dependency |
| ISO 8601 validation | Custom regex parser | Check non-empty + let backend validate format | Backend already validates datetime parsing; client just needs to ensure field is present |
| Error display | Custom error component | Existing pattern with conditional `<p>` and `text-destructive` | Matches project style |

**Key insight:** This phase is about removing complexity, not adding it. Every change should make the codebase simpler.

## Common Pitfalls

### Pitfall 1: Forgetting the TypeScript Type Update
**What goes wrong:** Fix the runtime validation but leave `timestamp?: string` (optional) in `types/api.ts`, creating a type-level inconsistency.
**Why it happens:** The type file is separate from the component files being edited.
**How to avoid:** Update `OrderbookRequest.timestamp` from optional to required in `dashboard/src/types/api.ts` line 74.
**Warning signs:** TypeScript compiler won't catch this because the type is only used for documentation, not enforced at the call site.

### Pitfall 2: Removing PaygToggleResponse Along with PaygToggle
**What goes wrong:** Delete the `PaygToggleResponse` interface thinking it's part of the dead code.
**Why it happens:** The name is similar to `PaygToggle`.
**How to avoid:** `PaygToggleResponse` in `types/api.ts` is imported and used by `api.billing.togglePayg()` in `lib/api.ts`. Only delete `payg-toggle.tsx`.
**Warning signs:** TypeScript build error after deletion.

### Pitfall 3: Incomplete REQUIREMENTS.md Update
**What goes wrong:** Add BKTS entries but forget to update the coverage count, status values, or last-updated date.
**Why it happens:** The file has multiple interconnected sections.
**How to avoid:** Checklist approach: (1) add BKTS section, (2) add to traceability table, (3) update all statuses, (4) update coverage count, (5) update date.

### Pitfall 4: Breaking the "Try Example" Flow
**What goes wrong:** Adding timestamp validation breaks the "Try an example" button because it fills all fields including timestamp.
**Why it happens:** Not testing the happy path after adding validation.
**How to avoid:** The `fillExample()` function already sets timestamp (`"2025-02-14T18:00:00Z"`) -- this path should still work. Verify it.

## Code Examples

### Timestamp Validation in sendRequest
```typescript
// In use-playground.ts, inside sendRequest():
const sendRequest = useCallback(async () => {
  if (!revealedKey) {
    setRequestError("No API key available. Select or create a key first.");
    return;
  }
  if (!timestamp.trim()) {
    setRequestError("Timestamp is required. Enter an ISO 8601 timestamp (e.g., 2025-02-14T18:00:00Z).");
    return;
  }

  setIsLoading(true);
  setRequestError(null);
  // ... rest of existing logic
}, [revealedKey, marketTicker, timestamp, depth]);
```

### Updated canSend Guard in PlaygroundForm
```typescript
// In playground-form.tsx:
const canSend = !!revealedKey && !!marketTicker.trim() && !!timestamp.trim() && !isLoading;
```

### Promoting Timestamp to Visible Required Field
```tsx
// In playground-form.tsx, move timestamp out of the "Additional fields" accordion
// and add the required indicator:
<div className="space-y-2">
  <Label htmlFor="timestamp">
    Timestamp (ISO 8601) <span className="text-destructive">*</span>
  </Label>
  <Input
    id="timestamp"
    value={timestamp}
    onChange={(e) => onSetField("timestamp", e.target.value)}
    placeholder="e.g. 2025-02-14T18:00:00Z"
  />
</div>
```

### Error Display in Playground Page
```tsx
// In page.tsx, render requestError:
{playground.requestError && (
  <p className="text-sm text-destructive">{playground.requestError}</p>
)}
```

### Dead Code to Remove
```python
# Remove from src/api/models.py (lines 401-415):
class SeriesRecord(BaseModel):
    """Summary info for a series."""
    ticker: str = Field(description="Unique series ticker")
    title: str | None = Field(default=None, description="Series title")
    frequency: str | None = Field(default=None, description="Release frequency")
    category: str | None = Field(default=None, description="Series category")

class SeriesResponse(BaseModel):
    """List of series."""
    data: list[SeriesRecord]
    request_id: str
    response_time: float = Field(description="Server-side processing time in seconds")
```

```
# Delete entire file:
dashboard/src/components/billing/payg-toggle.tsx
```

## State of the Art

Not applicable -- this phase is pure cleanup with no new technology decisions.

## Open Questions

1. **Should the "Additional fields" accordion remain for the `depth` field?**
   - What we know: Timestamp is being promoted out of it. Depth is the only remaining optional field.
   - What's unclear: Is an accordion for a single optional field worth the visual complexity?
   - Recommendation: Keep the accordion for depth. It reduces visual noise for the common case and is a minor UI decision the planner can make.

2. **Should requestError clear when the user starts typing?**
   - What we know: Currently `requestError` is set by `sendRequest()` and cleared at the start of the next `sendRequest()` call.
   - What's unclear: Whether the error should also clear on field input changes.
   - Recommendation: Clear `requestError` when `setField` is called. This is standard form UX and prevents stale error messages.

## Sources

### Primary (HIGH confidence)
- `src/api/models.py` -- Backend `OrderbookRequest` model confirms timestamp is required (line 17: `timestamp: datetime = Field(...)`)
- `dashboard/src/components/playground/use-playground.ts` -- Hook source showing missing validation
- `dashboard/src/components/playground/playground-form.tsx` -- Form source showing timestamp hidden under accordion
- `dashboard/src/components/billing/payg-toggle.tsx` -- Orphaned component file (no imports found)
- `dashboard/src/components/billing/usage-bar.tsx` -- Contains inline PAYG toggle (replacement)
- `src/api/routes/events.py` -- Confirms no import of SeriesRecord/SeriesResponse
- `src/api/routes/*.py` (all 11 files) -- Confirmed no route imports SeriesRecord or SeriesResponse
- `.planning/v1-MILESTONE-AUDIT.md` -- Defines all gaps being closed
- `.planning/REQUIREMENTS.md` -- Current state of traceability (stale, needs update)
- `.planning/ROADMAP.md` -- Phase 4 references BKTS-01-04

### Secondary (MEDIUM confidence)
- `dashboard/src/types/api.ts` -- Frontend OrderbookRequest has timestamp as optional (line 74: `timestamp?: string`)

## Metadata

**Confidence breakdown:**
- Playground validation: HIGH -- traced the exact bug from form to hook to backend model; fix is straightforward
- Dead code removal: HIGH -- verified zero imports of PaygToggle; verified zero route imports of SeriesRecord/SeriesResponse
- Requirements traceability: HIGH -- diffed current REQUIREMENTS.md against audit report; all gaps are clearly defined

**Research date:** 2026-02-16
**Valid until:** N/A (cleanup of known items, not library research)
