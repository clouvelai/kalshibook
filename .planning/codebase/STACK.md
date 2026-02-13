# Technology Stack

**Analysis Date:** 2026-02-13

## Languages

**Primary:**
- JavaScript/TypeScript (inferred from .gitignore tracking node_modules and next/ directory)
- Python (inferred from .gitignore tracking __pycache__, *.pyc, and .venv/venv directories)

**Secondary:**
- SQL (PostgreSQL via Supabase)

## Runtime

**Environment:**
- Node.js (inferred from node_modules in .gitignore)
- Python 3.x (inferred from venv support in .gitignore)

**Package Manager:**
- npm/yarn (Node.js package management)
- pip (Python package management)
- Lockfile: Not yet present in repository

## Frameworks

**Core:**
- Next.js (inferred from .next/ directory in .gitignore) - Frontend/Full-stack framework

**Backend:**
- Supabase (PostgreSQL-based backend-as-a-service)

**Edge Runtime:**
- Deno 2 - Edge function execution (configured in supabase/config.toml)

## Key Dependencies

**Critical:**
- Supabase client libraries (JavaScript/TypeScript) - Backend API integration
- PostgreSQL 17 - Database engine (running locally via Supabase CLI)

**Infrastructure:**
- Supabase CLI - Local development and database management tools

## Configuration

**Environment:**
- `.env.example` present with structure: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `APP_ENV`
- Configuration uses environment variable substitution for secrets
- Local development URL: `http://127.0.0.1:54321`
- Development app port: `3000`

**Build:**
- Supabase configuration: `supabase/config.toml`
- Next.js implied by .next/ in .gitignore (nextjs config not yet committed)

## Platform Requirements

**Development:**
- Supabase CLI (for local development stack)
- PostgreSQL 17 compatible database
- Node.js runtime
- Python runtime (optional, likely for backend services)

**Production:**
- Supabase hosted platform (or self-hosted Supabase instance)
- Node.js 18+ (recommended for Next.js)

**Local Development Stack:**
- API server: localhost:54321
- PostgreSQL: localhost:54322 (shadow: 54320)
- Supabase Studio: localhost:54323
- Email testing (Inbucket): localhost:54324
- S3-compatible storage enabled via Supabase storage API

---

*Stack analysis: 2026-02-13*
