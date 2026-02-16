"use client";

import { Terminal, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { CodeBlock } from "@/components/playground/code-block";
import { OrderbookPreview } from "@/components/playground/orderbook-preview";
import type { PlaygroundResult } from "@/lib/playground";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ResponsePanelProps {
  response: PlaygroundResult | null;
  isLoading: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function statusVariant(status: number): "secondary" | "destructive" {
  return status >= 200 && status < 300 ? "secondary" : "destructive";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ResponsePanel({ response, isLoading }: ResponsePanelProps) {
  // -------------------------------------------------------------------------
  // Empty state
  // -------------------------------------------------------------------------
  if (!response && !isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[300px] gap-3">
        <Terminal className="size-10 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          Send a request to see the response
        </p>
        <p className="text-xs text-muted-foreground/70">
          Configure your request on the left and click Send Request
        </p>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Loading state
  // -------------------------------------------------------------------------
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[300px] gap-3">
        <Loader2 className="size-8 text-muted-foreground animate-spin" />
        <p className="text-sm text-muted-foreground">Executing request...</p>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Response state (response is guaranteed non-null here)
  // -------------------------------------------------------------------------
  const { data, status, responseTime, creditsDeducted } = response!;

  return (
    <div>
      {/* Metadata bar */}
      <div className="flex items-center gap-4 px-4 py-2 border-b bg-muted/50 text-sm">
        <Badge variant={statusVariant(status)}>{status}</Badge>
        <span className="text-muted-foreground">{responseTime.toFixed(0)}ms</span>
        {creditsDeducted !== null && (
          <span className="text-muted-foreground">
            {creditsDeducted} credit{creditsDeducted !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* JSON | Preview sub-tabs */}
      <Tabs defaultValue="json" className="w-full">
        <div className="px-4 pt-3">
          <TabsList>
            <TabsTrigger value="json">JSON</TabsTrigger>
            <TabsTrigger value="preview">Preview</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="json" className="px-4 pb-4 pt-2">
          <CodeBlock
            code={JSON.stringify(data, null, 2)}
            language="json"
          />
        </TabsContent>

        <TabsContent value="preview" className="pb-4">
          <OrderbookPreview data={data} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
