"use client";

import { useState } from "react";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";

interface PaygToggleProps {
  initialEnabled: boolean;
}

export function PaygToggle({ initialEnabled }: PaygToggleProps) {
  const [enabled, setEnabled] = useState(initialEnabled);
  const [loading, setLoading] = useState(false);

  const handleToggle = async (checked: boolean) => {
    setLoading(true);
    try {
      const result = await api.billing.togglePayg(checked);
      setEnabled(result.payg_enabled);
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
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Pay-As-You-Go
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <Label htmlFor="payg-toggle" className="text-sm font-medium">
              {enabled ? "Enabled" : "Disabled"}
            </Label>
            <p className="text-sm text-muted-foreground">
              Continue using the API after credits run out ($0.008/credit).
            </p>
          </div>
          <Switch
            id="payg-toggle"
            checked={enabled}
            onCheckedChange={handleToggle}
            disabled={loading}
          />
        </div>
      </CardContent>
    </Card>
  );
}
