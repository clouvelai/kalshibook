-- Billing accounts for credit metering and Stripe integration.
-- Each user gets a free-tier account (1000 credits/month) lazily on first API request.
-- Tier upgrades and PAYG are managed via Stripe webhooks (Phase 3 Plan 2).

CREATE TABLE IF NOT EXISTS billing_accounts (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    stripe_customer_id TEXT UNIQUE,
    tier TEXT NOT NULL DEFAULT 'free' CHECK (tier IN ('free', 'payg', 'project')),
    payg_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    credits_total INT NOT NULL DEFAULT 1000,
    credits_used INT NOT NULL DEFAULT 0 CHECK (credits_used >= 0),
    billing_cycle_start TIMESTAMPTZ NOT NULL DEFAULT date_trunc('month', now()),
    stripe_subscription_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_billing_accounts_stripe ON billing_accounts (stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;
