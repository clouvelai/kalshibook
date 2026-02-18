"use client";

import { useEffect, useRef, useState } from "react";
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface CoverageSearchProps {
  search: string;
  onSearchChange: (value: string) => void;
  status: string;
  onStatusChange: (value: string) => void;
}

function DebouncedInput({
  value,
  onChange,
  debounce = 300,
  ...props
}: {
  value: string;
  onChange: (value: string) => void;
  debounce?: number;
} & Omit<React.ComponentProps<"input">, "onChange">) {
  const [internal, setInternal] = useState(value);
  const firstRender = useRef(true);

  useEffect(() => {
    setInternal(value);
  }, [value]);

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    const timer = setTimeout(() => {
      onChange(internal);
    }, debounce);
    return () => clearTimeout(timer);
  }, [internal, debounce, onChange]);

  return (
    <Input
      {...props}
      value={internal}
      onChange={(e) => setInternal(e.target.value)}
    />
  );
}

export function CoverageSearch({
  search,
  onSearchChange,
  status,
  onStatusChange,
}: CoverageSearchProps) {
  const hasFilters = search !== "" || status !== "all";

  return (
    <div className="flex items-center gap-3">
      <div className="relative max-w-sm flex-1">
        <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <DebouncedInput
          value={search}
          onChange={onSearchChange}
          placeholder="Search markets..."
          className="pl-8"
        />
      </div>

      <Select value={status} onValueChange={onStatusChange}>
        <SelectTrigger className="w-[130px]">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All</SelectItem>
          <SelectItem value="active">Active</SelectItem>
          <SelectItem value="settled">Settled</SelectItem>
        </SelectContent>
      </Select>

      {hasFilters && (
        <button
          type="button"
          onClick={() => {
            onSearchChange("");
            onStatusChange("all");
          }}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <X className="size-3" />
          Clear filters
        </button>
      )}
    </div>
  );
}
