"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { api } from "@/lib/api";
import type { BillingStatus, KeyUsageItem } from "@/types/api";
import { UsageBar } from "@/components/billing/usage-bar";
import { KeysTable } from "@/components/keys/keys-table";
import { CreateKeyDialog } from "@/components/keys/create-key-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function OverviewPage() {
  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [keys, setKeys] = useState<KeyUsageItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [billingRes, keysRes] = await Promise.all([
        api.billing.status(),
        api.keys.usage(),
      ]);

      setBilling(billingRes);

      // Lazy init: if no keys exist (e.g., Google OAuth user), create a default one
      let keysData = keysRes.data;
      if (keysData.length === 0) {
        await api.keys.create("default", "dev");
        const refreshed = await api.keys.usage();
        keysData = refreshed.data;
      }

      setKeys(keysData);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load dashboard data"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Your API usage at a glance
          </p>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-10">
            <p className="text-sm text-destructive">{error}</p>
            <Button variant="outline" size="sm" onClick={fetchData}>
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Your API usage at a glance
          </p>
        </div>
        <Skeleton className="h-[200px] w-full rounded-xl" />
        <Skeleton className="h-[200px] w-full rounded-lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Your API usage at a glance
        </p>
      </div>

      {billing && (
        <UsageBar
          creditsUsed={billing.credits_used}
          creditsTotal={billing.credits_total}
          tier={billing.tier}
          paygEnabled={billing.payg_enabled}
        />
      )}

      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold tracking-tight">API Keys</h2>
          <CreateKeyDialog onKeyCreated={fetchData}>
            <Button
              variant="ghost"
              size="icon-xs"
              title="Create key"
              className="cursor-pointer text-muted-foreground hover:text-foreground"
            >
              <Plus className="size-3.5" />
            </Button>
          </CreateKeyDialog>
        </div>
        {keys && <KeysTable keys={keys} onRefresh={fetchData} />}
      </div>
    </div>
  );
}
