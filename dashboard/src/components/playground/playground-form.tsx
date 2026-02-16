"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  Play,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface PlaygroundFormProps {
  keys: Array<{ id: string; key_prefix: string; name: string }>;
  selectedKeyId: string | null;
  marketTicker: string;
  timestamp: string;
  depth: string;
  isLoading: boolean;
  revealedKey: string | null;
  onSelectKey: (keyId: string, keyPrefix: string) => void;
  onSetField: (field: "marketTicker" | "timestamp" | "depth", value: string) => void;
  onSendRequest: () => void;
  onFillExample: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PlaygroundForm({
  keys,
  selectedKeyId,
  marketTicker,
  timestamp,
  depth,
  isLoading,
  revealedKey,
  onSelectKey,
  onSetField,
  onSendRequest,
  onFillExample,
}: PlaygroundFormProps) {
  const [additionalOpen, setAdditionalOpen] = useState(false);

  const canSend = !!revealedKey && !!marketTicker.trim() && !isLoading;

  return (
    <div className="space-y-5">
      {/* API Key selector */}
      <div className="space-y-2">
        <Label htmlFor="api-key-select">API Key</Label>
        <Select
          value={selectedKeyId ?? undefined}
          onValueChange={(value) => {
            const key = keys.find((k) => k.id === value);
            if (key) onSelectKey(key.id, key.key_prefix);
          }}
        >
          <SelectTrigger id="api-key-select" className="w-full">
            <SelectValue placeholder="Select an API key" />
          </SelectTrigger>
          <SelectContent>
            {keys.map((k) => (
              <SelectItem key={k.id} value={k.id}>
                <span className="font-mono text-xs">
                  {k.key_prefix}{"••••••••"}
                </span>
                <span className="ml-2 text-muted-foreground text-xs">
                  ({k.name})
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Market Ticker */}
      <div className="space-y-2">
        <Label htmlFor="market-ticker">
          Market Ticker <span className="text-destructive">*</span>
        </Label>
        <Input
          id="market-ticker"
          value={marketTicker}
          onChange={(e) => onSetField("marketTicker", e.target.value)}
          placeholder="e.g. KXBTC-25FEB14-T96074.99"
          className="text-base md:text-base"
        />
      </div>

      {/* Additional Fields toggle */}
      <div>
        <button
          type="button"
          onClick={() => setAdditionalOpen(!additionalOpen)}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          {additionalOpen ? (
            <ChevronUp className="size-4" />
          ) : (
            <ChevronDown className="size-4" />
          )}
          Additional fields
        </button>

        {additionalOpen && (
          <div className="mt-3 space-y-4 pl-1">
            {/* Timestamp */}
            <div className="space-y-2">
              <Label htmlFor="timestamp">Timestamp (ISO 8601)</Label>
              <Input
                id="timestamp"
                value={timestamp}
                onChange={(e) => onSetField("timestamp", e.target.value)}
                placeholder="e.g. 2025-02-14T18:00:00Z"
              />
            </div>

            {/* Depth */}
            <div className="space-y-2">
              <Label htmlFor="depth">Depth</Label>
              <Input
                id="depth"
                type="number"
                value={depth}
                onChange={(e) => onSetField("depth", e.target.value)}
                placeholder="e.g. 10"
                min={1}
              />
            </div>
          </div>
        )}
      </div>

      {/* Try an example */}
      <button
        type="button"
        onClick={onFillExample}
        className="text-sm text-primary hover:underline"
      >
        Try an example
      </button>

      {/* Send Request */}
      <Button
        className="w-full"
        disabled={!canSend}
        onClick={onSendRequest}
      >
        {isLoading ? (
          <>
            <Loader2 className="size-4 animate-spin" />
            Sending...
          </>
        ) : (
          <>
            <Play className="size-4" />
            Send Request
          </>
        )}
      </Button>
    </div>
  );
}
