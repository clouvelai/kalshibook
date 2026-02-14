"""Billing routes — Stripe Checkout, Customer Portal, webhooks, PAYG toggle, billing status.

All billing endpoints (except the webhook) require a Supabase JWT
(from POST /auth/login), NOT an API key.
"""

from __future__ import annotations

import stripe
import structlog
from fastapi import APIRouter, Depends, Request

from src.api.deps import get_authenticated_user, get_db_pool
from src.api.errors import KalshiBookError, generate_request_id
from src.api.models import (
    BillingStatusResponse,
    CheckoutResponse,
    PaygToggleRequest,
    PaygToggleResponse,
    PortalResponse,
)
from src.api.services.billing import (
    ensure_billing_account,
    get_billing_status,
    handle_payment_failed,
    handle_subscription_canceled,
    sync_subscription_state,
    toggle_payg,
    update_stripe_customer_id,
)
from src.shared.config import get_settings

logger = structlog.get_logger("api.billing")

router = APIRouter(tags=["Billing"])


# ---------------------------------------------------------------------------
# GET /billing/status
# ---------------------------------------------------------------------------


@router.get("/billing/status", response_model=BillingStatusResponse)
async def billing_status(
    request: Request,
    user: dict = Depends(get_authenticated_user),
    pool=Depends(get_db_pool),
):
    """Return the current billing status for the authenticated user."""
    account = await get_billing_status(pool, user["user_id"])

    if account is None:
        account = await ensure_billing_account(pool, user["user_id"])

    credits_remaining = max(0, account["credits_total"] - account["credits_used"])

    return BillingStatusResponse(
        tier=account["tier"],
        credits_total=account["credits_total"],
        credits_used=account["credits_used"],
        credits_remaining=credits_remaining,
        payg_enabled=account["payg_enabled"],
        billing_cycle_start=account["billing_cycle_start"].isoformat(),
        request_id=getattr(request.state, "request_id", generate_request_id()),
    )


# ---------------------------------------------------------------------------
# POST /billing/checkout
# ---------------------------------------------------------------------------


@router.post("/billing/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: Request,
    user: dict = Depends(get_authenticated_user),
    pool=Depends(get_db_pool),
):
    """Create a Stripe Checkout Session for upgrading to the Project plan."""
    settings = get_settings()

    # Ensure billing account exists
    account = await ensure_billing_account(pool, user["user_id"])

    # Create or reuse Stripe customer
    stripe_customer_id = account.get("stripe_customer_id")
    if not stripe_customer_id:
        customer = await stripe.Customer.create_async(
            email=user["email"],
            metadata={"kalshibook_user_id": str(user["user_id"])},
        )
        stripe_customer_id = customer.id
        await update_stripe_customer_id(pool, user["user_id"], stripe_customer_id)

    # Create Checkout Session
    session = await stripe.checkout.Session.create_async(
        customer=stripe_customer_id,
        line_items=[{"price": settings.stripe_project_price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{settings.app_url}/billing?success=true",
        cancel_url=f"{settings.app_url}/billing?canceled=true",
    )

    return CheckoutResponse(
        checkout_url=session.url,
        request_id=getattr(request.state, "request_id", generate_request_id()),
    )


# ---------------------------------------------------------------------------
# POST /billing/portal
# ---------------------------------------------------------------------------


@router.post("/billing/portal", response_model=PortalResponse)
async def create_portal(
    request: Request,
    user: dict = Depends(get_authenticated_user),
    pool=Depends(get_db_pool),
):
    """Create a Stripe Customer Portal Session for subscription management."""
    settings = get_settings()

    account = await get_billing_status(pool, user["user_id"])

    if account is None or not account.get("stripe_customer_id"):
        raise KalshiBookError(
            code="no_billing_account",
            message="No billing account found. Subscribe first via POST /billing/checkout.",
            status=400,
        )

    session = await stripe.billing_portal.Session.create_async(
        customer=account["stripe_customer_id"],
        return_url=f"{settings.app_url}/billing",
    )

    return PortalResponse(
        portal_url=session.url,
        request_id=getattr(request.state, "request_id", generate_request_id()),
    )


# ---------------------------------------------------------------------------
# POST /billing/payg
# ---------------------------------------------------------------------------


@router.post("/billing/payg", response_model=PaygToggleResponse)
async def payg_toggle(
    request: Request,
    body: PaygToggleRequest,
    user: dict = Depends(get_authenticated_user),
    pool=Depends(get_db_pool),
):
    """Enable or disable Pay-As-You-Go billing."""
    # Ensure billing account exists
    account = await ensure_billing_account(pool, user["user_id"])

    # If enabling PAYG, ensure Stripe customer exists
    if body.enable:
        stripe_customer_id = account.get("stripe_customer_id")
        if not stripe_customer_id:
            customer = await stripe.Customer.create_async(
                email=user["email"],
                metadata={"kalshibook_user_id": str(user["user_id"])},
            )
            stripe_customer_id = customer.id
            await update_stripe_customer_id(pool, user["user_id"], stripe_customer_id)

    updated = await toggle_payg(pool, user["user_id"], body.enable)

    message = (
        "Pay-As-You-Go enabled. Overage credits will be billed at $0.008/credit."
        if body.enable
        else "Pay-As-You-Go disabled. API access will stop when credits are exhausted."
    )

    return PaygToggleResponse(
        payg_enabled=updated["payg_enabled"],
        message=message,
        request_id=getattr(request.state, "request_id", generate_request_id()),
    )


# ---------------------------------------------------------------------------
# POST /billing/webhook
# ---------------------------------------------------------------------------


@router.post("/billing/webhook")
async def stripe_webhook(request: Request, pool=Depends(get_db_pool)):
    """Handle Stripe webhook events for subscription lifecycle.

    This endpoint does NOT use get_authenticated_user — it verifies
    the Stripe webhook signature instead.
    """
    settings = get_settings()

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise KalshiBookError(
            code="invalid_payload",
            message="Invalid webhook payload.",
            status=400,
        )
    except stripe.SignatureVerificationError:
        raise KalshiBookError(
            code="invalid_signature",
            message="Invalid Stripe webhook signature.",
            status=400,
        )

    event_type = event["type"]
    event_data = event["data"]["object"]

    if event_type in ("customer.subscription.created", "customer.subscription.updated"):
        await sync_subscription_state(pool, event_data)
    elif event_type == "customer.subscription.deleted":
        await handle_subscription_canceled(pool, event_data)
    elif event_type == "invoice.payment_failed":
        await handle_payment_failed(pool, event_data)
    else:
        logger.info("webhook_unhandled_event", event_type=event_type)

    return {"received": True}
