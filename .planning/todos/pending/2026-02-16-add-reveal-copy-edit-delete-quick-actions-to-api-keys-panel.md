---
created: 2026-02-16T13:19:42.734Z
title: Add reveal, copy, edit, delete quick actions to API keys panel
area: ui
files:
  - dashboard/src/app/(dashboard)/keys/page.tsx
---

## Problem

The API keys table on the dashboard /keys page uses a dropdown menu for actions (revoke). The user wants inline icon-based quick actions similar to other API key management UIs (e.g., Tavily): reveal (eye icon), copy (clipboard icon), edit (pencil icon), and delete (trash icon) displayed directly in an OPTIONS column for each key row.

## Solution

Replace the current dropdown-based actions with inline icon buttons in the keys table:
- Reveal: toggle masked/unmasked key display (eye/eye-off icon)
- Copy: copy key prefix or masked value to clipboard with toast confirmation
- Edit: rename key or change key_type (dev/prod) inline or via dialog
- Delete: revoke key with confirmation dialog (existing flow)
