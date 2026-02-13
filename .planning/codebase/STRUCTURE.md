# Codebase Structure

**Analysis Date:** 2026-02-13

## Directory Layout

```
kalshibook/
├── .claude/                        # GSD framework and development orchestration
│   ├── agents/                    # AI agent definitions for different tasks
│   ├── commands/                  # GSD command handlers
│   ├── get-shit-done/             # Core framework (bin, templates, workflows, references)
│   ├── hooks/                     # Git and IDE integration hooks
│   ├── gsd-file-manifest.json    # Framework file registry
│   └── settings.json              # IDE and hook configuration
├── supabase/                       # Backend infrastructure configuration
│   ├── config.toml                # Supabase local dev configuration
│   └── .temp/                     # Temporary files (generated, not committed)
├── .planning/                      # GSD planning and documentation
│   └── codebase/                  # Codebase analysis documents (this location)
├── .env.example                    # Environment variable template
├── .gitignore                      # Git ignore rules
└── [future app code - not yet created]
```

## Directory Purposes

**.claude/**
- Purpose: Development workflow automation and AI agent orchestration
- Contains: Agent definitions, command implementations, workflow templates, configuration
- Key files: `.claude/settings.json`, `.claude/gsd-file-manifest.json`
- Special: Framework directories (agents/, commands/, get-shit-done/, hooks/)

**supabase/**
- Purpose: Backend infrastructure definition and local development environment
- Contains: Supabase project configuration, seed data, local dev scripts
- Key files: `supabase/config.toml` (database, auth, storage, API configuration)
- Special: `.temp/` directory generated during `supabase start` (not committed)

**.planning/codebase/**
- Purpose: Architecture and design documentation
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, STACK.md, INTEGRATIONS.md, CONCERNS.md
- Key files: This document (STRUCTURE.md) and companion analysis documents

**Root Level**
- `.env.example`: Template for environment configuration (Supabase connection, app environment)
- `.gitignore`: Excludes node_modules, .env files, build outputs, IDE files, OS files
- No application code yet - will be added during development phases

## Key File Locations

**Entry Points:**
- `.claude/hooks/gsd-statusline.js`: IDE status line updates
- `.claude/hooks/gsd-check-update.js`: Framework version checking
- `supabase/config.toml`: Supabase local environment initialization

**Configuration:**
- `.env.example`: Environment template (must be copied to `.env` for local development)
- `supabase/config.toml`: Complete Supabase configuration (ports, auth, storage, databases)
- `.claude/settings.json`: IDE integration settings
- `.gitignore`: Git exclusion rules

**Framework:**
- `.claude/agents/`: Agent definitions (gsd-planner.md, gsd-executor.md, gsd-debugger.md, etc.)
- `.claude/commands/`: Command handlers (gsd/map-codebase.md, gsd/plan-phase.md, gsd/execute-phase.md, etc.)
- `.claude/get-shit-done/`: Core framework (bin/gsd-tools.js with ~4500 LOC, templates/, workflows/)

**Documentation:**
- `.claude/get-shit-done/templates/`: Project templates (project.md, milestone.md, phase-prompt.md, etc.)
- `.claude/get-shit-done/references/`: Implementation guides (git-integration.md, verification-patterns.md, etc.)

## Naming Conventions

**Files:**
- GSD framework files: `gsd-*.md` or `gsd-*.js` (e.g., `gsd-planner.md`, `gsd-tools.js`)
- Configuration files: `config.*` or `*.toml` (e.g., `config.toml`, `settings.json`)
- Documentation: `*.md` (Markdown format for human-readable documentation)
- Templates: `*.md` in `templates/` directory

**Directories:**
- Functional groups: snake_case (e.g., `get-shit-done`, `gsd-file-manifest.json`)
- Feature domains: lowercase with hyphens for clarity (future: `src/`, `tests/`, `services/`)
- Hidden directories: leading dot for system/IDE config (`.claude/`, `.planning/`, `.vscode/`, `.idea/`)

**Environment Variables:**
- Supabase: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- Application: `APP_ENV` (development/production)
- Optional: `OPENAI_API_KEY` (for Supabase AI features in Studio)

## Where to Add New Code

**New Feature Implementation:**
- Primary code: Will be determined by application type (TBD)
  - If web app: `src/components/`, `src/pages/`, `src/services/`, `src/utils/`
  - If API: `src/api/`, `src/handlers/`, `src/models/`
  - If CLI: `src/commands/`, `src/handlers/`
- Tests: Parallel to source code in `tests/` or co-located with features
- Example: Feature "User Profile" → `src/features/profile/Profile.tsx` + `src/features/profile/Profile.test.ts`

**New Component/Module:**
- Implementation: Create in appropriate subdirectory of `src/`
- Types: `src/types/` or co-located `types.ts` in feature directory
- Hooks (React): `src/hooks/`
- Utils: `src/utils/` for shared utilities

**Database Changes:**
- Schema migrations: `supabase/migrations/` (TBD - create when needed)
- Seed data: `supabase/seed.sql` (currently placeholder)
- Documentation: Add comments in migration files explaining purpose

**Utilities and Shared Code:**
- Shared helpers: `src/utils/`
- Constants: `src/constants/` or inline in modules
- API clients: `src/lib/api.ts`
- Database clients: `src/lib/db.ts`

## Special Directories

**`.claude/` Directory:**
- Purpose: Development workflow orchestration
- Generated: No, committed to git
- Committed: Yes, required for GSD framework
- Note: Do not modify agent/command files unless extending GSD framework

**`.planning/codebase/` Directory:**
- Purpose: Codebase analysis and architectural documentation
- Generated: Yes, created by `/gsd:map-codebase` command
- Committed: Yes, for project memory
- Note: Updated regularly as architecture evolves

**`supabase/.temp/` Directory:**
- Purpose: Local development temporary files
- Generated: Yes, created by `supabase start`
- Committed: No (excluded in .gitignore)
- Note: Contains PID files, temp databases, logs

**`node_modules/` Directory (future):**
- Purpose: JavaScript dependencies
- Generated: Yes, created by `npm install`
- Committed: No (excluded in .gitignore)
- Note: Lock file will be committed (package-lock.json or yarn.lock)

**`dist/`, `build/`, `.next/` Directories (future):**
- Purpose: Build output and compiled code
- Generated: Yes, created by build process
- Committed: No (excluded in .gitignore)
- Note: Build artifacts should never be committed

## Recommended Next Steps for New Code

1. **Create application entry point** (e.g., `src/index.ts` or `src/app.tsx`)
2. **Set up package.json** with dependencies (React, Express, or other framework)
3. **Create src/ directory structure** following conventions above
4. **Initialize test setup** (Jest, Vitest, etc.) with example test
5. **Create .env from .env.example** for local development
6. **Document architecture** as features are added (update ARCHITECTURE.md with layers)

---

*Structure analysis: 2026-02-13*
