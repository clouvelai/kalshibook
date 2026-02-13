# Architecture

**Analysis Date:** 2026-02-13

## Pattern Overview

**Overall:** Early-stage project initialization with GSD framework scaffolding and Supabase backend configuration. No application code deployed yet.

**Key Characteristics:**
- Supabase-first architecture (PostgreSQL database with realtime, auth, storage)
- Get-Shit-Done (GSD) framework for AI-assisted development workflow
- Backend-first setup with database-driven approach
- Development environment configured but application layer not yet initialized

## Layers

**Framework/Orchestration:**
- Purpose: AI-assisted development workflow management
- Location: `.claude/` directory
- Contains: Agent definitions, command handlers, workflows, templates
- Depends on: Node.js runtime, git integration
- Used by: Development process automation

**Backend Infrastructure:**
- Purpose: Persistent data storage, authentication, real-time subscriptions, file storage
- Location: `supabase/` directory
- Contains: Database configuration, Supabase local development setup
- Depends on: PostgreSQL 17, Supabase local development environment
- Used by: Future application services (not yet deployed)

**Application Code:**
- Purpose: Business logic (not yet created)
- Location: Will be at project root or `src/` directory
- Contains: To be determined
- Depends on: Backend infrastructure
- Used by: End-users and services

## Data Flow

**No active data flows currently.** Architecture is prepared for:

1. User Authentication → Supabase Auth (configured at `supabase/config.toml`)
2. API Requests → Supabase REST/GraphQL API (configured at ports 54321)
3. Database Operations → PostgreSQL (configured at port 54322)
4. Real-time Updates → Supabase Realtime (enabled in config)
5. File Storage → Supabase Storage (configured with 50MiB limit)

**State Management:** Not implemented. Future implementation will likely use Supabase as single source of truth for application state.

## Key Abstractions

**Supabase Project:**
- Purpose: Backend-as-a-service providing database, authentication, storage, realtime
- Examples: `supabase/config.toml`
- Pattern: Configuration-driven infrastructure setup

**GSD Framework:**
- Purpose: Orchestrate AI-assisted development phases and tasks
- Examples: `.claude/agents/`, `.claude/commands/`, `.claude/get-shit-done/`
- Pattern: Agent/command/workflow architecture for development lifecycle

## Entry Points

**Development Start:**
- Location: `.claude/hooks/gsd-check-update.js` and `.claude/hooks/gsd-statusline.js`
- Triggers: Claude Code session initialization
- Responsibilities: Version checking, status reporting

**Supabase Local Dev:**
- Location: `supabase/config.toml`
- Triggers: `supabase start` command
- Responsibilities: Initialize local Supabase environment on ports 54320-54327

**Future Application Entry Points:**
- Will be at project root (e.g., `index.js`, `main.ts`, `app.tsx`) once application code is added

## Error Handling

**Strategy:** Not yet implemented. Supabase provides built-in error handling for database operations, authentication failures, and API errors.

**Patterns:**
- Framework will follow GSD agent error recovery patterns (see `.claude/agents/`)
- Application will inherit Supabase error responses and HTTP status codes

## Cross-Cutting Concerns

**Logging:**
- GSD framework logs to console and GSD state management
- Supabase logs available via `supabase logs` CLI command

**Validation:**
- Database schema validation via Supabase migrations
- Authentication validation via Supabase Auth policies
- API request validation via Supabase API specification

**Authentication:**
- Supabase Auth with email signup enabled
- JWT tokens (3600s expiry, refresh token rotation enabled)
- Support for OAuth providers (currently disabled)

---

*Architecture analysis: 2026-02-13*
