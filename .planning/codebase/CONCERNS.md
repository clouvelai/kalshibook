# Codebase Concerns

**Analysis Date:** 2026-02-13

## Early-Stage Project Structure

**Project Status - Early Development:**
- Issue: Project contains only Supabase configuration with zero application code
- Files: `.env.example`, `supabase/config.toml`
- Impact: No functional application yet; all planned features are still in design phase
- Fix approach: Establish application architecture (frontend/backend frameworks, API structure) before scaling feature development

## Configuration & Security

**Weak Password Requirements:**
- Issue: `minimum_password_length = 6` in `supabase/config.toml` is below security best practices
- Files: `supabase/config.toml` (line 149)
- Impact: User accounts are vulnerable to brute force attacks; does not meet OWASP minimum guidelines
- Recommendations: Increase to minimum 8 characters, consider implementing complexity requirements

**MFA Not Enabled:**
- Issue: Multi-factor authentication is disabled (`[auth.mfa.totp] enroll_enabled = false`, `verify_enabled = false`)
- Files: `supabase/config.toml` (lines 172-174)
- Impact: No protection against credential compromise; critical for security in production
- Recommendations: Enable TOTP (Time-based One-Time Password) MFA for at least admin accounts before production launch

**Email Confirmations Disabled:**
- Issue: `enable_confirmations = false` in auth email configuration
- Files: `supabase/config.toml` (line 159)
- Impact: Users can register with invalid email addresses; enables spam and impersonation attacks
- Recommendations: Enable email confirmations before production deployment

**No SMTP Server Configured:**
- Issue: Email functionality uses Inbucket (test/development only); no production SMTP configured
- Files: `supabase/config.toml` (lines 154-160 commented out)
- Impact: Cannot send transactional emails (password resets, confirmations) in production
- Recommendations: Configure production SMTP before launching; set up email templates and sender verification

**Missing Environment Secrets:**
- Issue: No signing keys configured for JWT authentication
- Files: `supabase/config.toml` (line 145 commented out: `# signing_keys_path = "./signing_keys.json"`)
- Impact: JWT tokens are not cryptographically signed; critical authentication vulnerability
- Recommendations: Generate and configure signing keys before production; never commit to git

## Database

**No Migrations or Schema Defined:**
- Issue: Database has zero migrations; `schema_paths = []` is empty
- Files: `supabase/config.toml` (line 70)
- Impact: No schema versioning; database structure is undefined; no way to reproduce environment
- Fix approach: Create migration files in `supabase/migrations/` using `.sql` format before any data operations

**No Seed Data Structure:**
- Issue: Seed configuration references `./seed.sql` but file does not exist
- Files: `supabase/config.toml` (line 73)
- Impact: Cannot reproduce development data; development environment setup is manual and error-prone
- Fix approach: Create `supabase/seed.sql` with initial data structure and test data

**Connection Pooler Disabled:**
- Issue: `[db.pooler] enabled = false`
- Files: `supabase/config.toml` (line 36)
- Impact: No connection pooling in development; will cause connection exhaustion as load increases
- Recommendations: Enable pooler before production or implement application-level pooling

## API Configuration

**Overly Permissive Row Limits:**
- Issue: `max_rows = 1000` allows large data transfers per request
- Files: `supabase/config.toml` (line 20)
- Impact: Risk of accidental or malicious bulk data extraction; bandwidth abuse
- Recommendations: Reduce to 100-200 rows and paginate; implement rate limiting

**No Row-Level Security (RLS) Schema:**
- Issue: No database schema to define RLS policies
- Impact: All authenticated users can access all data; no multi-tenant isolation
- Fix approach: Define RLS policies in migration files; test thoroughly before production

## Testing & Validation

**No Application Code to Test:**
- Issue: Zero TypeScript/JavaScript application code exists
- Files: No `.ts`, `.tsx`, `.js` files outside `.claude/` directory
- Impact: Cannot validate any functionality; testing framework not yet selected
- Fix approach: Establish testing framework (Jest, Vitest, etc.) alongside application development

**No Type Definitions:**
- Issue: No TypeScript configuration (`tsconfig.json` missing)
- Impact: Cannot enforce type safety in application code
- Fix approach: Add `tsconfig.json` with strict mode enabled; generate Supabase types from schema

## Development Environment

**Supabase CLI Version Not Pinned:**
- Issue: `.supabase/cli-latest` file exists but no `.supabase-cli-version` or lock file
- Files: `supabase/.temp/cli-latest`
- Impact: Team members may use different CLI versions; inconsistent behavior
- Recommendations: Pin CLI version in `.supabase-cli-version` or document in README

**No Documentation:**
- Issue: No README, contribution guidelines, or setup instructions
- Impact: New developers cannot understand project structure or setup process
- Fix approach: Create `README.md` with: project overview, local development setup, database schema explanation, testing instructions

**Environment Configuration Incomplete:**
- Issue: `.env.example` references `OPENAI_API_KEY` in Supabase config but no clear project purpose
- Files: `.env.example`, `supabase/config.toml` (line 121)
- Impact: Unclear what external services project will integrate with; may be vestigial config
- Recommendations: Either remove OpenAI config or document intended AI features

## Scalability & Performance

**S3 Storage Configuration Present but Unconfigured:**
- Issue: S3 protocol enabled (`[storage.s3_protocol] enabled = true`) but AWS credentials not configured
- Files: `supabase/config.toml` (lines 100-102)
- Impact: Storage will fail in production; file size limit set to 50MiB may be insufficient
- Fix approach: Configure S3 credentials or switch to Supabase-managed storage

**Analytics Backend Not Ready:**
- Issue: Analytics enabled with Postgres backend; no data pipeline configured
- Files: `supabase/config.toml` (lines 185-188)
- Impact: Analytics will accumulate but not be queryable; may impact query performance
- Recommendations: Either disable analytics or configure proper ETL pipeline

**Realtime Enabled Without Rate Limiting:**
- Issue: `[realtime] enabled = true` with no connection limits configured
- Files: `supabase/config.toml` (line 106)
- Impact: Realtime connections can exhaust server resources; no abuse protection
- Recommendations: Implement rate limiting for realtime channels; set max_connections limit

## Edge Functions

**Edge Runtime Set to Deno 2:**
- Issue: `deno_version = 2` in `[edge_runtime]`
- Files: `supabase/config.toml` (line 193)
- Impact: Very new runtime; breaking changes possible; limited third-party package support
- Recommendations: Document Deno version compatibility; test edge functions thoroughly before production

**No Edge Function Implementation Yet:**
- Issue: Edge runtime enabled but no edge functions exist
- Impact: Infrastructure in place but no clear use cases defined
- Fix approach: Document which features require edge functions; implement with proper testing

## Third-Party Integrations

**OAuth Providers All Disabled:**
- Issue: All OAuth providers (Apple, Google, GitHub, etc.) are disabled with empty credentials
- Files: `supabase/config.toml` (lines 141-157)
- Impact: Cannot determine authentication strategy; config bloated with disabled options
- Recommendations: Document which auth providers are planned; remove unused configurations; configure before production

**No Webhook Configuration:**
- Issue: No incoming or outgoing webhook system configured
- Impact: Cannot integrate with external services or notify users of events
- Fix approach: Define webhook requirements in early architecture planning

## Code Quality

**No Linting or Formatting Configuration:**
- Issue: No `.eslintrc`, `.prettierrc`, or similar configuration files
- Impact: Code style is undefined; no automated checks; inconsistent commits
- Fix approach: Add ESLint and Prettier configuration as soon as application code starts

**No CI/CD Pipeline:**
- Issue: No GitHub Actions, GitLab CI, or similar automation
- Impact: No automated testing, linting, or deployment; manual release process error-prone
- Fix approach: Add GitHub Actions workflow for: lint, test, build, deploy-to-staging

**No Git Hooks Configuration:**
- Issue: No `.husky` or `pre-commit` hooks configured
- Impact: Developers can commit without running tests or linting
- Fix approach: Add Husky for pre-commit hooks; enforce linting and type checking before commits

---

*Concerns audit: 2026-02-13*
