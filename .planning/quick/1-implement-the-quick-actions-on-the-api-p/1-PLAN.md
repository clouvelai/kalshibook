---
phase: quick
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - src/api/models.py
  - src/api/services/auth.py
  - src/api/routes/keys.py
  - dashboard/src/lib/api.ts
  - dashboard/src/types/api.ts
  - dashboard/src/components/keys/edit-key-dialog.tsx
  - dashboard/src/components/keys/keys-table.tsx
  - dashboard/src/app/(dashboard)/page.tsx
autonomous: true
must_haves:
  truths:
    - "User can copy a key prefix to clipboard from the overview table"
    - "User can edit a key's name and type via a dialog from the overview table"
    - "User can revoke/delete a key with confirmation from the overview table"
    - "Overview table refreshes after edit or delete mutations"
  artifacts:
    - path: "src/api/routes/keys.py"
      provides: "PATCH /keys/{key_id} endpoint"
      contains: "patch"
    - path: "src/api/services/auth.py"
      provides: "update_api_key database function"
      contains: "update_api_key"
    - path: "src/api/models.py"
      provides: "ApiKeyUpdate request model"
      contains: "ApiKeyUpdate"
    - path: "dashboard/src/lib/api.ts"
      provides: "api.keys.update() client method"
      contains: "update"
    - path: "dashboard/src/components/keys/edit-key-dialog.tsx"
      provides: "Edit key dialog component"
      exports: ["EditKeyDialog"]
    - path: "dashboard/src/components/keys/keys-table.tsx"
      provides: "Keys table with inline action buttons"
      contains: "Copy"
  key_links:
    - from: "dashboard/src/components/keys/keys-table.tsx"
      to: "dashboard/src/lib/api.ts"
      via: "api.keys.update() call in EditKeyDialog"
      pattern: "api\\.keys\\.update"
    - from: "dashboard/src/components/keys/keys-table.tsx"
      to: "dashboard/src/components/keys/revoke-key-dialog.tsx"
      via: "RevokeKeyDialog wrapping delete button"
      pattern: "RevokeKeyDialog"
    - from: "dashboard/src/app/(dashboard)/page.tsx"
      to: "dashboard/src/components/keys/keys-table.tsx"
      via: "onRefresh prop passing fetchData"
      pattern: "onRefresh"
---

<objective>
Add inline quick-action icon buttons (copy prefix, edit, delete) to the API keys table on the overview page.

Purpose: Users currently must navigate to /keys to manage their keys. Quick actions on the overview page let them copy prefixes, rename keys, change key type, and revoke keys without leaving the dashboard.

Output: Working PATCH endpoint for key updates, EditKeyDialog component, and updated KeysTable with inline icon buttons.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-plan.md
@./.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@dashboard/src/components/keys/keys-table.tsx
@dashboard/src/components/keys/keys-management-table.tsx (pattern reference for copy/revoke)
@dashboard/src/components/keys/revoke-key-dialog.tsx (reuse for delete action)
@dashboard/src/app/(dashboard)/page.tsx
@dashboard/src/lib/api.ts
@dashboard/src/types/api.ts
@src/api/models.py
@src/api/services/auth.py
@src/api/routes/keys.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add PATCH /keys/{key_id} backend endpoint</name>
  <files>
    src/api/models.py
    src/api/services/auth.py
    src/api/routes/keys.py
  </files>
  <action>
    1. In `src/api/models.py`, add an `ApiKeyUpdate` model after the existing `ApiKeyCreate` model:
       ```python
       class ApiKeyUpdate(BaseModel):
           """Request to update an existing API key."""
           name: str | None = Field(default=None, max_length=100)
           key_type: str | None = Field(default=None, description="Key type: 'dev' or 'prod'")
       ```
       Both fields optional so partial updates work.

    2. In `src/api/services/auth.py`, add an `update_api_key` function after `revoke_api_key`:
       - Accepts `pool`, `key_id`, `user_id`, `name` (optional), `key_type` (optional).
       - Builds a dynamic UPDATE query that only sets provided fields.
       - Validates `key_type` is either "dev" or "prod" if provided (raise ValueError otherwise).
       - WHERE clause: `id = $1 AND user_id = $2 AND revoked_at IS NULL` (same ownership check as revoke).
       - Returns the updated row dict `{id, name, key_prefix, key_type, created_at, last_used_at}` or None if not found.
       - Log with structlog: `api_key_updated`.

    3. In `src/api/routes/keys.py`:
       - Import `ApiKeyUpdate` from models and `update_api_key` from services.
       - Add `@router.patch("/keys/{key_id}")` endpoint:
         - Accepts `key_id: str` path param and `body: ApiKeyUpdate`.
         - If neither name nor key_type provided, raise KalshiBookError (400, "no_fields", "No fields to update").
         - Call `update_api_key(pool, key_id, user["user_id"], body.name, body.key_type)`.
         - If result is None, raise KalshiBookError (404, "key_not_found", "API key not found or already revoked.").
         - Return `{"data": result, "request_id": request_id}`.
       - Update the module docstring to mention PATCH.
  </action>
  <verify>
    Run `cd /Users/samuelclark/Desktop/kalshibook && python -c "from src.api.routes.keys import router; from src.api.models import ApiKeyUpdate; from src.api.services.auth import update_api_key; print('imports ok')"` to verify no import errors.
  </verify>
  <done>PATCH /keys/{key_id} endpoint exists, accepts optional name and key_type fields, validates ownership, returns updated key data.</done>
</task>

<task type="auto">
  <name>Task 2: Add api.keys.update() client method and EditKeyDialog component</name>
  <files>
    dashboard/src/lib/api.ts
    dashboard/src/types/api.ts
    dashboard/src/components/keys/edit-key-dialog.tsx
  </files>
  <action>
    1. In `dashboard/src/lib/api.ts`, add `update` method to `api.keys`:
       ```typescript
       update: (keyId: string, data: { name?: string; key_type?: string }) =>
         fetchAPI<ApiResponse<ApiKeyInfo>>(`/keys/${keyId}`, {
           method: "PATCH",
           body: JSON.stringify(data),
         }),
       ```

    2. In `dashboard/src/types/api.ts`, no changes needed — `ApiKeyInfo` already covers the update response shape.

    3. Create `dashboard/src/components/keys/edit-key-dialog.tsx`:
       - A controlled dialog component that edits a key's name and type.
       - Props: `keyId: string`, `currentName: string`, `currentType: string`, `onUpdated: () => void`, `children: React.ReactNode` (trigger element).
       - State: `open`, `name` (string, initialized from `currentName`), `keyType` (string, initialized from `currentType`), `isSaving` (boolean).
       - Reset form state when dialog opens (useEffect on `open` to sync `name`/`keyType` from props).
       - Form layout:
         - Name: `<Input>` with `<Label>` ("Name"), value bound to `name` state.
         - Type: `<Select>` with `<Label>` ("Type"), value bound to `keyType` state, options: `<SelectItem value="dev">dev</SelectItem>` and `<SelectItem value="prod">prod</SelectItem>`.
       - Save button: calls `api.keys.update(keyId, { name, key_type: keyType })`, shows `<Loader2 className="animate-spin" />` while saving.
       - On success: `toast.success("API key updated")`, close dialog, call `onUpdated()`.
       - On error: `toast.error(error.message || "Failed to update API key")`.
       - Use `Dialog`, `DialogTrigger`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription`, `DialogFooter` from `@/components/ui/dialog`.
       - Use `Button` from `@/components/ui/button`.
       - Use `Input` from `@/components/ui/input`.
       - Use `Label` from `@/components/ui/label`.
       - Use `Select`, `SelectContent`, `SelectItem`, `SelectTrigger`, `SelectValue` from `@/components/ui/select`.
       - Import `Loader2` from `lucide-react`.
       - Import `toast` from `sonner`.
       - Import `api` from `@/lib/api`.
       - Mark as `"use client"`.
  </action>
  <verify>
    Run `cd /Users/samuelclark/Desktop/kalshibook/dashboard && npx tsc --noEmit --pretty 2>&1 | head -30` to verify no TypeScript errors in the new/modified files.
  </verify>
  <done>api.keys.update() method exists. EditKeyDialog component renders a form dialog with name input and type select, calls PATCH endpoint, shows toast feedback, and triggers refresh callback on success.</done>
</task>

<task type="auto">
  <name>Task 3: Add inline quick-action buttons to KeysTable and wire onRefresh</name>
  <files>
    dashboard/src/components/keys/keys-table.tsx
    dashboard/src/app/(dashboard)/page.tsx
  </files>
  <action>
    1. Update `dashboard/src/components/keys/keys-table.tsx`:
       - Add `onRefresh: () => void` to the `KeysTableProps` interface.
       - Add new imports:
         - `{ Copy, Pencil, Trash2 }` from `lucide-react`
         - `{ toast }` from `sonner`
         - `{ Button }` from `@/components/ui/button`
         - `{ Tooltip, TooltipContent, TooltipProvider, TooltipTrigger }` from `@/components/ui/tooltip`
         - `{ RevokeKeyDialog }` from `@/components/keys/revoke-key-dialog`
         - `{ EditKeyDialog }` from `@/components/keys/edit-key-dialog`
       - Add `handleCopyPrefix` async function (same pattern as keys-management-table.tsx):
         ```typescript
         const handleCopyPrefix = async (prefix: string) => {
           try {
             await navigator.clipboard.writeText(prefix);
             toast.success("Key prefix copied to clipboard");
           } catch {
             toast.error("Failed to copy to clipboard");
           }
         };
         ```
       - Add an "Actions" column header after "Last Used": `<TableHead className="w-[100px]">Actions</TableHead>`.
       - Add an actions cell at the end of each row with three inline icon buttons wrapped in a `<TooltipProvider delayDuration={300}>`:
         - **Copy prefix**: `<Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon-xs" onClick={() => handleCopyPrefix(key.key_prefix)}><Copy className="size-3" /></Button></TooltipTrigger><TooltipContent>Copy prefix</TooltipContent></Tooltip>`
         - **Edit**: `<EditKeyDialog keyId={key.id} currentName={key.name} currentType={key.key_type} onUpdated={onRefresh}><Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon-xs"><Pencil className="size-3" /></Button></TooltipTrigger><TooltipContent>Edit key</TooltipContent></Tooltip></EditKeyDialog>` — Note: The EditKeyDialog uses `DialogTrigger asChild` wrapping, so the Tooltip+Button becomes the trigger. If tooltip inside dialog trigger causes issues, wrap it the other way: put Tooltip outside EditKeyDialog's children prop, or simplify by just using `title` attribute on the button instead of Tooltip. Test and adjust.
         - **Delete**: `<RevokeKeyDialog keyName={key.name} keyId={key.id} onRevoked={onRefresh}><Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon-xs" className="text-muted-foreground hover:text-destructive"><Trash2 className="size-3" /></Button></TooltipTrigger><TooltipContent>Revoke key</TooltipContent></Tooltip></RevokeKeyDialog>`
       - The actions cell should use `<TableCell><div className="flex items-center gap-0.5">...</div></TableCell>` to keep the buttons inline and tight.

    2. Update `dashboard/src/app/(dashboard)/page.tsx`:
       - Change `<KeysTable keys={keys} />` to `<KeysTable keys={keys} onRefresh={fetchData} />`.
       - No other changes needed — `fetchData` is already defined and re-fetches both billing and keys.

    After writing both files, verify the build compiles. If tooltips inside dialog/alert-dialog triggers cause nesting issues, simplify by removing Tooltip wrappers and using `title` attribute on the Button elements instead (e.g., `<Button title="Copy prefix" ...>`). The key requirement is that the icon buttons are self-explanatory — tooltips are nice-to-have, not essential.
  </action>
  <verify>
    Run `cd /Users/samuelclark/Desktop/kalshibook/dashboard && npx tsc --noEmit --pretty 2>&1 | head -30` to verify no TypeScript errors. Then run `cd /Users/samuelclark/Desktop/kalshibook/dashboard && npm run build 2>&1 | tail -20` to confirm the production build succeeds.
  </verify>
  <done>KeysTable renders three inline icon buttons (copy, edit, delete) in an Actions column. Copy writes prefix to clipboard with toast. Edit opens EditKeyDialog. Delete opens RevokeKeyDialog. Both edit and delete trigger onRefresh callback after mutation. Overview page passes fetchData as onRefresh. Build compiles without errors.</done>
</task>

</tasks>

<verification>
1. `python -c "from src.api.routes.keys import router"` -- backend imports clean
2. `cd dashboard && npx tsc --noEmit` -- no TypeScript errors
3. `cd dashboard && npm run build` -- production build succeeds
4. Manual test: overview page shows Actions column with copy/edit/delete icon buttons per row
5. Manual test: clicking copy shows "Key prefix copied" toast
6. Manual test: clicking edit opens dialog with current name/type, saving updates and refreshes table
7. Manual test: clicking delete opens revoke confirmation, confirming revokes and refreshes table
</verification>

<success_criteria>
- PATCH /keys/{key_id} endpoint accepts optional name and key_type, validates ownership, returns updated key
- api.keys.update() client method calls PATCH endpoint
- EditKeyDialog component renders name input + type select, saves via API, shows toast feedback
- KeysTable has Actions column with three inline icon buttons per row
- Overview page passes onRefresh to KeysTable for post-mutation refresh
- Full dashboard build compiles without errors
</success_criteria>

<output>
After completion, create `.planning/quick/1-implement-the-quick-actions-on-the-api-p/1-SUMMARY.md`
</output>
