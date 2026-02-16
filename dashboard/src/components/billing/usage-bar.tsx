"use client";

import { useState } from "react";
import { ExternalLink, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

interface UsageBarProps {
  creditsUsed: number;
  creditsTotal: number;
  tier: string;
  paygEnabled: boolean;
}

export function UsageBar({
  creditsUsed,
  creditsTotal,
  tier,
  paygEnabled: initialPayg,
}: UsageBarProps) {
  const [paygEnabled, setPaygEnabled] = useState(initialPayg);
  const [paygLoading, setPaygLoading] = useState(false);
  const [portalLoading, setPortalLoading] = useState(false);

  const percentage =
    creditsTotal > 0 ? Math.min((creditsUsed / creditsTotal) * 100, 100) : 0;

  const tierDisplay = tier.charAt(0).toUpperCase() + tier.slice(1);
  const hasStripeCustomer = tier !== "free" || paygEnabled;

  const handlePaygToggle = async (checked: boolean) => {
    setPaygLoading(true);
    try {
      const result = await api.billing.togglePayg(checked);
      setPaygEnabled(result.payg_enabled);
      toast.success(
        result.payg_enabled
          ? "Pay-As-You-Go enabled"
          : "Pay-As-You-Go disabled"
      );
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : "Failed to update Pay-As-You-Go"
      );
    } finally {
      setPaygLoading(false);
    }
  };

  const handleManagePlan = async () => {
    if (!hasStripeCustomer) return;
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

  return (
    <div className="relative overflow-hidden rounded-xl border bg-gradient-to-br from-slate-50 via-white to-teal-50 dark:from-slate-900 dark:via-slate-900 dark:to-teal-950">
      {/* Decorative background element */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-teal-100/40 via-transparent to-transparent dark:from-teal-800/20" />

      <div className="relative space-y-5 p-6">
        {/* Header row: badge + manage button */}
        <div className="flex items-center justify-between">
          <Badge variant="outline" className="text-xs font-medium uppercase tracking-wider">
            Current Plan
          </Badge>
          {hasStripeCustomer && (
            <Button
              variant="outline"
              size="sm"
              className="h-8 gap-1.5 bg-white/80 text-xs backdrop-blur-sm dark:bg-slate-900/80"
              onClick={handleManagePlan}
              disabled={portalLoading}
            >
              {portalLoading ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <ExternalLink className="size-3.5" />
              )}
              Manage Plan
            </Button>
          )}
        </div>

        {/* Plan name */}
        <h2 className="text-2xl font-bold tracking-tight">{tierDisplay}</h2>

        {/* Usage section */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-muted-foreground">API Usage</span>
            <span className="tabular-nums text-muted-foreground">
              {creditsUsed.toLocaleString()} / {creditsTotal.toLocaleString()} Credits
            </span>
          </div>
          <Progress value={percentage} className="h-2" />
        </div>

        {/* PAYG toggle */}
        <div className="flex items-center gap-3">
          <Switch
            id="payg-toggle"
            checked={paygEnabled}
            onCheckedChange={handlePaygToggle}
            disabled={paygLoading}
            className="scale-90"
          />
          <Label
            htmlFor="payg-toggle"
            className="text-sm text-muted-foreground cursor-pointer"
          >
            Pay as you go
          </Label>
        </div>
      </div>
    </div>
  );
}
