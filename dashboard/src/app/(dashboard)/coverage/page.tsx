"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { CoverageStatsResponse } from "@/types/api";
import { CoverageSummaryCards } from "@/components/coverage/coverage-summary-cards";
import { CoverageSearch } from "@/components/coverage/coverage-search";
import { CoverageTable } from "@/components/coverage/coverage-table";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const PAGE_SIZE = 20;

export default function CoveragePage() {
  const [data, setData] = useState<CoverageStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [filtering, setFiltering] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [page, setPage] = useState(1);

  const fetchData = useCallback(
    async (isFilter = false) => {
      if (isFilter) {
        setFiltering(true);
      } else {
        setLoading(true);
      }
      setError(null);

      try {
        const result = await api.coverage.stats({
          search: search || undefined,
          status: status === "all" ? undefined : status,
          page,
          page_size: PAGE_SIZE,
        });
        setData(result);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load coverage data"
        );
      } finally {
        setLoading(false);
        setFiltering(false);
      }
    },
    [search, status, page]
  );

  useEffect(() => {
    // Initial load vs filter update
    const isFilter = data !== null;
    fetchData(isFilter);
  }, [fetchData]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setPage(1);
  };

  const handleStatusChange = (value: string) => {
    setStatus(value);
    setPage(1);
  };

  const clearFilters = () => {
    setSearch("");
    setStatus("all");
    setPage(1);
  };

  const totalPages = data
    ? Math.max(1, Math.ceil(data.total_events / PAGE_SIZE))
    : 1;

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Coverage</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Discover which markets have data and where the gaps are
          </p>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-10">
            <p className="text-sm text-destructive">{error}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchData(false)}
            >
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
          <h1 className="text-2xl font-semibold tracking-tight">Coverage</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Discover which markets have data and where the gaps are
          </p>
        </div>
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Skeleton className="h-[80px] w-full rounded-xl" />
          <Skeleton className="h-[80px] w-full rounded-xl" />
          <Skeleton className="h-[80px] w-full rounded-xl" />
          <Skeleton className="h-[80px] w-full rounded-xl" />
        </div>
        <Skeleton className="h-[40px] w-full rounded-lg" />
        <Skeleton className="h-[300px] w-full rounded-lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Coverage</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Discover which markets have data and where the gaps are
        </p>
      </div>

      {data && <CoverageSummaryCards summary={data.summary} />}

      <CoverageSearch
        search={search}
        onSearchChange={handleSearchChange}
        status={status}
        onStatusChange={handleStatusChange}
      />

      <div className={filtering ? "opacity-60 transition-opacity" : ""}>
        {data && (
          <CoverageTable
            events={data.events}
            summary={data.summary}
            onClearFilters={clearFilters}
          />
        )}
      </div>

      {data && totalPages > 1 && (
        <div className="flex items-center justify-center gap-4">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
