"use client";

import { usePlayground } from "@/components/playground/use-playground";
import { PlaygroundForm } from "@/components/playground/playground-form";
import { CodePanel } from "@/components/playground/code-panel";

export default function PlaygroundPage() {
  const playground = usePlayground();

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
        <p className="text-xs text-muted-foreground mt-1">
          Requests from the playground use your API credits
        </p>
      </div>

      {/* Split-panel layout */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Left panel: form */}
        <div className="w-full lg:w-[400px] lg:shrink-0">
          <PlaygroundForm
            keys={playground.keys}
            selectedKeyId={playground.selectedKeyId}
            marketTicker={playground.marketTicker}
            timestamp={playground.timestamp}
            depth={playground.depth}
            isLoading={playground.isLoading}
            revealedKey={playground.revealedKey}
            onSelectKey={playground.selectKey}
            onSetField={playground.setField}
            onSendRequest={playground.sendRequest}
            onFillExample={playground.fillExample}
          />
        </div>

        {/* Right panel: code/response */}
        <div className="flex-1 min-w-0">
          <CodePanel
            curlCommand={playground.curlCommand}
            response={playground.response}
            isLoading={playground.isLoading}
            activeTab={playground.activeTab}
            onTabChange={playground.setActiveTab}
          />
        </div>
      </div>
    </div>
  );
}
