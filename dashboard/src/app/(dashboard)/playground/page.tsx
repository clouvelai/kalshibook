"use client";

import { usePlayground } from "@/components/playground/use-playground";
import { Card, CardContent } from "@/components/ui/card";

export default function PlaygroundPage() {
  // Wire the hook -- child components (Plan 02/03) will consume the state
  const playground = usePlayground();

  // Suppress unused-var warning in scaffold phase
  void playground;

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          API Playground
        </h1>
        <p className="text-sm text-muted-foreground">
          Test API endpoints and see generated code
        </p>
      </div>

      {/* Split-panel layout */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Left panel: form (Plan 02) */}
        <div className="w-full lg:w-[400px] lg:shrink-0 space-y-6">
          <Card>
            <CardContent className="py-10 text-center text-sm text-muted-foreground">
              Form panel (Plan 02)
            </CardContent>
          </Card>
        </div>

        {/* Right panel: code/response (Plan 02-03) */}
        <div className="flex-1 min-w-0">
          <Card>
            <CardContent className="py-10 text-center text-sm text-muted-foreground">
              Code/Response panel (Plan 02-03)
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
