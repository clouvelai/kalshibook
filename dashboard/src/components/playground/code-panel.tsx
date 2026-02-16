"use client";

import { CodeBlock } from "@/components/playground/code-block";
import { Card } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { PlaygroundResult } from "@/lib/playground";
import type { ActiveTab } from "@/components/playground/use-playground";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface CodePanelProps {
  curlCommand: string;
  response: PlaygroundResult | null;
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
}

// ---------------------------------------------------------------------------
// Language sub-tabs for code view
// ---------------------------------------------------------------------------

const LANGUAGES = [
  { id: "shell", label: "Shell", enabled: true },
  { id: "python", label: "Python", enabled: false },
  { id: "javascript", label: "JavaScript", enabled: false },
] as const;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function CodePanel({
  curlCommand,
  response,
  activeTab,
  onTabChange,
}: CodePanelProps) {
  return (
    <Card className="overflow-hidden py-0">
      {/* Top section: Response | Code toggle */}
      <div className="flex items-center justify-between border-b px-4 py-3">
        <span className="text-sm font-medium">Output</span>
        <Tabs
          value={activeTab}
          onValueChange={(v) => onTabChange(v as ActiveTab)}
        >
          <TabsList>
            <TabsTrigger value="response">Response</TabsTrigger>
            <TabsTrigger value="code">Code</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Code tab content */}
      {activeTab === "code" && (
        <div>
          {/* Language sub-tabs */}
          <div className="flex items-center gap-1 px-4 pt-3 pb-2">
            <TooltipProvider>
              {LANGUAGES.map((lang) =>
                lang.enabled ? (
                  <button
                    key={lang.id}
                    type="button"
                    className="rounded-md px-3 py-1 text-xs font-medium bg-primary text-primary-foreground"
                  >
                    {lang.label}
                  </button>
                ) : (
                  <Tooltip key={lang.id}>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        className="rounded-md px-3 py-1 text-xs font-medium text-muted-foreground opacity-50 cursor-not-allowed"
                        disabled
                      >
                        {lang.label}
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>Coming soon</TooltipContent>
                  </Tooltip>
                )
              )}
            </TooltipProvider>
          </div>

          {/* Code display */}
          <div className="px-4 pb-4">
            <CodeBlock code={curlCommand} language="bash" />
          </div>
        </div>
      )}

      {/* Response tab content */}
      {activeTab === "response" && (
        <div className="px-4 py-4">
          {response ? (
            <CodeBlock
              code={JSON.stringify(response.data, null, 2)}
              language="json"
            />
          ) : (
            <div className="flex items-center justify-center py-16 text-sm text-muted-foreground">
              Send a request to see the response
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
