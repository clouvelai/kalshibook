"use client";

import { useState } from "react";
import { CreditCard, ExternalLink, Loader2, Zap } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";

interface PlanCardProps {
  tier: string;
  creditsTotal: number;
  creditsUsed: number;
  creditsRemaining: number;
  payg_enabled: boolean;
  billingCycleStart: string;
}

export function PlanCard({
  tier,
  creditsTotal,
  creditsUsed,
  creditsRemaining,
  payg_enabled,
  billingCycleStart,
}: PlanCardProps) {
  const [portalLoading, setPortalLoading] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(false);

  const usagePercent = creditsTotal > 0
    ? Math.min((creditsUsed / creditsTotal) * 100, 100)
    : 0;

  const tierDisplay = tier.charAt(0).toUpperCase() + tier.slice(1);

  // Calculate next billing date: billing_cycle_start + 1 month
  const nextBillingDate = (() => {
    try {
      const start = new Date(billingCycleStart);
      const next = new Date(start);
      next.setMonth(next.getMonth() + 1);
      return next.toLocaleDateString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return "N/A";
    }
  })();

  const handleManageInStripe = async () => {
    setPortalLoading(true);
    try {
      const response = await api.billing.createPortal();
      window.location.href = response.portal_url;
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to open billing portal"
      );
      setPortalLoading(false);
    }
  };

  const handleUpgrade = async () => {
    setCheckoutLoading(true);
    try {
      const response = await api.billing.createCheckout();
      window.location.href = response.checkout_url;
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to start checkout"
      );
      setCheckoutLoading(false);
    }
  };

  // Free tier without PAYG has no Stripe customer
  const hasStripeCustomer = tier !== "free" || payg_enabled;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="size-5" />
              Current Plan
            </CardTitle>
            <CardDescription>
              Manage your subscription and usage
            </CardDescription>
          </div>
          <Badge variant={tier === "free" ? "outline" : "secondary"}>
            {tierDisplay}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Credit Usage */}
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">Credits</span>
            <span className="text-muted-foreground">
              {creditsUsed.toLocaleString()} / {creditsTotal.toLocaleString()} used
            </span>
          </div>
          <Progress value={usagePercent} />
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{creditsUsed.toLocaleString()} used</span>
            <span>{creditsRemaining.toLocaleString()} remaining</span>
          </div>
        </div>

        <Separator />

        {/* Billing Details */}
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Next billing date</span>
            <span className="font-medium">{nextBillingDate}</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Pay-As-You-Go</span>
            <Badge variant={payg_enabled ? "default" : "outline"}>
              {payg_enabled ? "Enabled" : "Disabled"}
            </Badge>
          </div>
        </div>

        <Separator />

        {/* Actions */}
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button
            variant="outline"
            className="flex-1"
            onClick={handleManageInStripe}
            disabled={!hasStripeCustomer || portalLoading}
          >
            {portalLoading ? (
              <Loader2 className="animate-spin" />
            ) : (
              <ExternalLink className="size-4" />
            )}
            Manage in Stripe
          </Button>
          {tier === "free" && (
            <Button
              className="flex-1"
              onClick={handleUpgrade}
              disabled={checkoutLoading}
            >
              {checkoutLoading ? (
                <Loader2 className="animate-spin" />
              ) : (
                <Zap className="size-4" />
              )}
              Upgrade to Project Plan — $30/mo
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
