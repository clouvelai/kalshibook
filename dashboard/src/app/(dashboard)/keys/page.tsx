"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, Key } from "lucide-react";
import { api } from "@/lib/api";
import type { KeyUsageItem } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CreateKeyDialog } from "@/components/keys/create-key-dialog";
import { KeysManagementTable } from "@/components/keys/keys-management-table";

export default function KeysPage() {
  const [keys, setKeys] = useState<KeyUsageItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchKeys = useCallback(async () => {
    try {
      setError(null);
      const response = await api.keys.usage();
      setKeys(response.data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load API keys"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  const handleRefresh = () => {
    setLoading(true);
    fetchKeys();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">API Keys</h1>
          <p className="text-sm text-muted-foreground">
            Manage your API keys for accessing KalshiBook data endpoints.
          </p>
        </div>
        <CreateKeyDialog onKeyCreated={handleRefresh}>
          <Button>
            <Plus className="size-4" />
            Create Key
          </Button>
        </CreateKeyDialog>
      </div>

      {loading ? (
        <Card>
          <CardContent className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-5 w-12" />
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-6 w-28" />
                <Skeleton className="ml-auto h-8 w-8" />
              </div>
            ))}
          </CardContent>
        </Card>
      ) : error ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-8">
            <p className="text-sm text-destructive">{error}</p>
            <Button variant="outline" size="sm" onClick={handleRefresh}>
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : keys.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <div className="flex size-12 items-center justify-center rounded-full bg-muted">
              <Key className="size-6 text-muted-foreground" />
            </div>
            <div className="text-center">
              <p className="font-medium">No API keys yet</p>
              <p className="text-sm text-muted-foreground">
                Create your first key to start using the KalshiBook API.
              </p>
            </div>
            <CreateKeyDialog onKeyCreated={handleRefresh}>
              <Button>
                <Plus className="size-4" />
                Create your first key
              </Button>
            </CreateKeyDialog>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <KeysManagementTable keys={keys} onRefresh={handleRefresh} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
