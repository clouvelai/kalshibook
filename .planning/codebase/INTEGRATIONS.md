# External Integrations

**Analysis Date:** 2026-02-13

## APIs & External Services

**OpenAI:**
- OpenAI API - Used for Supabase AI features in Studio
  - SDK/Client: OpenAI API (configured in supabase/config.toml)
  - Auth: `OPENAI_API_KEY` environment variable (optional for local development)

## Data Storage

**Databases:**
- PostgreSQL 17 (via Supabase)
  - Connection: `SUPABASE_URL` (http://127.0.0.1:54321 locally)
  - Client: Supabase JavaScript/TypeScript client library
  - Port: 54322 (database), 54320 (shadow database for migrations)
  - Pooler: Connection pooling disabled by default (can be enabled on port 54329)

**File Storage:**
- Supabase Storage (S3-compatible)
  - File size limit: 50MiB per file
  - S3 protocol support enabled
  - Access: Via Supabase client library
  - Location: `supabase/config.toml [storage]` section

**Caching:**
- Not detected

## Authentication & Identity

**Auth Provider:**
- Supabase Auth (built-in)
  - Implementation: Local development with email confirmation and OAuth support
  - Email signup enabled
  - Anonymous sign-ins disabled
  - JWT expiry: 3600 seconds (1 hour)
  - Refresh token rotation enabled
  - Manual account linking disabled
  - Rate limiting enforced: 2 emails/hour, 30 SMS/hour, 150 token refreshes per 5 min
  - Minimum password length: 6 characters

**External OAuth Providers (configured but disabled by default):**
- Apple OAuth
- Azure, Bitbucket, Discord, Facebook, GitHub, GitLab, Google
- Keycloak, LinkedIn OIDC, Notion, Twitch, Twitter/X, Slack, Spotify
- WorkOS, Zoom
- Web3 (Solana sign-in)

**Third-party Auth Providers (available but disabled):**
- Firebase Auth
- Auth0
- AWS Cognito/Amplify
- Clerk

**SMS Provider (disabled by default):**
- Twilio support configured (requires `SUPABASE_AUTH_SMS_TWILIO_AUTH_TOKEN`)

## Webhooks & Callbacks

**Incoming:**
- Supabase Auth redirect URLs: `http://127.0.0.1:3000` and `https://127.0.0.1:3000`
- Email confirmation and password reset URLs from Inbucket testing service
- Site URL: `http://127.0.0.1:3000`

**Outgoing:**
- Edge Function hooks available:
  - `auth.hook.before_user_created` - Pre-user creation validation
  - `auth.hook.custom_access_token` - Custom JWT claims injection
- Inbucket email testing (localhost:54324)

## Email Service

**Email Testing:**
- Inbucket (local development only)
  - Port: 54324 (web interface)
  - Emails sent in development are not actually transmitted; they can be viewed in Inbucket UI
  - SMTP and POP3 ports available for configuration

**Production Email (not configured):**
- SMTP configuration template available in `supabase/config.toml`
- Example: SendGrid SMTP support with `SENDGRID_API_KEY` placeholder

## Analytics & Observability

**Analytics:**
- Supabase Analytics enabled (port 54327)
- Backend: PostgreSQL
- Feature: Experimental analytics for ETL jobs (Pro plan feature)

## Realtime Features

**Realtime:**
- Supabase Realtime enabled
- Supports PostgreSQL database changes via WebSocket subscriptions
- IP version: IPv4 (default)
- Max header length: 4096 bytes (default)

## Edge Runtime

**Deno Edge Functions:**
- Deno 2 runtime configured for edge functions
- Inspector port: 8083 (for debugging)
- Policy: `per_worker` (hot reload during development)
- Location: Functions run in edge_runtime environment

## Environment Configuration

**Required env vars:**
- `SUPABASE_URL` - API endpoint
- `SUPABASE_ANON_KEY` - Anonymous/public API key
- `SUPABASE_SERVICE_ROLE_KEY` - Service role (backend operations)
- `APP_ENV` - Application environment (development/production)

**Optional env vars:**
- `OPENAI_API_KEY` - For Supabase AI features in Studio
- `SUPABASE_AUTH_SMS_TWILIO_AUTH_TOKEN` - For SMS authentication
- `SUPABASE_AUTH_EXTERNAL_[PROVIDER]_SECRET` - For OAuth providers
- `S3_HOST`, `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` - For experimental OrioleDB S3 storage

**Secrets location:**
- Environment variables via `.env` file (NOT committed; `.env.example` shows structure)
- Sensitive config: `supabase/config.toml` with `env()` substitution pattern

---

*Integration audit: 2026-02-13*
