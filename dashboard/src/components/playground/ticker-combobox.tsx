"use client";

import { useState, useEffect, useRef } from "react";
import { ChevronsUpDown, Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { PlaygroundMarket } from "@/types/api";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface TickerComboboxProps {
  value: string;
  onSelect: (market: PlaygroundMarket) => void;
  onChange: (value: string) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function TickerCombobox({ value, onSelect, onChange }: TickerComboboxProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PlaygroundMarket[]>([]);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    if (query.length < 2) {
      setResults([]);
      return;
    }

    setLoading(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await api.playground.markets(query);
        setResults(res.data);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 200);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [query]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between font-mono text-sm"
        >
          {value || "Search markets..."}
          <ChevronsUpDown className="ml-2 size-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Type to search markets..."
            value={query}
            onValueChange={(v) => {
              setQuery(v);
              onChange(v);
            }}
          />
          <CommandList>
            {query.length < 2 ? (
              <div className="py-6 text-center text-sm text-muted-foreground">
                Type 2+ characters to search...
              </div>
            ) : loading ? (
              <div className="py-6 text-center text-sm text-muted-foreground">
                Searching...
              </div>
            ) : (
              <>
                <CommandEmpty>No markets found</CommandEmpty>
                <CommandGroup>
                  {results.map((market) => (
                    <CommandItem
                      key={market.ticker}
                      value={market.ticker}
                      onSelect={() => {
                        onSelect(market);
                        setOpen(false);
                      }}
                    >
                      <Check
                        className={cn(
                          "mr-2 size-4",
                          value === market.ticker ? "opacity-100" : "opacity-0"
                        )}
                      />
                      <div className="flex flex-col gap-0.5 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm">{market.ticker}</span>
                          {market.status === "settled" && (
                            <Badge variant="secondary" className="text-[10px] px-1 py-0">
                              settled
                            </Badge>
                          )}
                        </div>
                        {market.title && (
                          <span className="text-xs text-muted-foreground truncate">
                            {market.title}
                          </span>
                        )}
                      </div>
                    </CommandItem>
                  ))}
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
