"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface UsageBarProps {
  creditsUsed: number;
  creditsTotal: number;
  tier: string;
}

export function UsageBar({ creditsUsed, creditsTotal, tier }: UsageBarProps) {
  const percentage = creditsTotal > 0
    ? Math.min((creditsUsed / creditsTotal) * 100, 100)
    : 0;
  const remaining = Math.max(creditsTotal - creditsUsed, 0);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          API Usage — {tier} Plan
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <Progress value={percentage} className="h-2" />
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>{creditsUsed.toLocaleString()} credits used</span>
          <span>{remaining.toLocaleString()} remaining</span>
        </div>
      </CardContent>
    </Card>
  );
}
