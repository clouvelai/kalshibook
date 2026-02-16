---
created: 2026-02-16T13:30:00.000Z
title: Chrome browser verification for milestone UAT
area: planning
files:
  - .claude/get-shit-done/workflows/verify-work.md
  - .claude/get-shit-done/workflows/execute-phase.md
---

## Problem

When `--chrome` is available, GSD's human verification checkpoints (05-05 style plans) and `/gsd:verify-work` UAT could be performed automatically via browser automation instead of requiring the user to manually click through and report results. Phase 5 proved this works: Claude navigated the dashboard, created/revoked API keys, verified billing, tested sign out/login — all through the Chrome MCP tools.

Currently this capability is ad-hoc. It should be documented as a pattern and optionally integrated into the GSD verification workflow so checkpoint plans and UAT steps can be browser-automated when the Chrome extension is connected.

## Solution

1. **Document the pattern** in a GSD reference file (e.g., `references/browser-verification.md`):
   - When to use browser verification vs manual (UI-heavy phases only)
   - How to structure checkpoint plans for browser-automatable steps
   - Limitations: can't enter passwords/create accounts, safety constraints
   - Pattern for capturing screenshots as evidence

2. **Integrate with verify-work workflow**: When `--chrome` flag is detected or Chrome MCP tools are available, the `/gsd:verify-work` workflow could automatically execute UAT steps that involve navigating pages, clicking elements, and verifying visual state — falling back to human verification for auth flows and sensitive actions.

3. **Checkpoint plan template update**: Add a `browser_verifiable: true` frontmatter field to checkpoint tasks that can be automated, so the executor knows to use Chrome tools instead of prompting the user.
