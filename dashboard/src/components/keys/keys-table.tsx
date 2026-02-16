"use client";

import { useState } from "react";
import Link from "next/link";
import { Copy, Eye, EyeOff, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { KeyUsageItem } from "@/types/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EditKeyDialog } from "@/components/keys/edit-key-dialog";
import { RevokeKeyDialog } from "@/components/keys/revoke-key-dialog";

interface KeysTableProps {
  keys: KeyUsageItem[];
  onRefresh: () => void;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/** Mask the key: show prefix + asterisks to simulate full key length */
function maskKey(prefix: string): string {
  return `${prefix}${"*".repeat(25)}`;
}

function KeyRow({ keyItem, onRefresh }: { keyItem: KeyUsageItem; onRefresh: () => void }) {
  const [revealed, setRevealed] = useState(false);
  const [fullKey, setFullKey] = useState<string | null>(null);
  const [revealing, setRevealing] = useState(false);

  const handleReveal = async () => {
    if (revealed) {
      setRevealed(false);
      return;
    }

    if (fullKey) {
      setRevealed(true);
      return;
    }

    setRevealing(true);
    try {
      const response = await api.keys.reveal(keyItem.id);
      setFullKey(response.data.key);
      setRevealed(true);
    } catch {
      toast.error("Unable to reveal key");
    } finally {
      setRevealing(false);
    }
  };

  const handleCopy = async () => {
    const keyToCopy = fullKey || keyItem.key_prefix;
    try {
      await navigator.clipboard.writeText(keyToCopy);
      toast.success(fullKey ? "API key copied to clipboard" : "Key prefix copied to clipboard");
    } catch {
      toast.error("Failed to copy to clipboard");
    }
  };

  const displayKey = revealed && fullKey ? fullKey : maskKey(keyItem.key_prefix);

  return (
    <TableRow>
      <TableCell className="font-medium">{keyItem.name}</TableCell>
      <TableCell>
        <Badge variant={keyItem.key_type === "prod" ? "secondary" : "outline"}>
          {keyItem.key_type}
        </Badge>
      </TableCell>
      <TableCell className="text-right tabular-nums">
        {keyItem.credits_used.toLocaleString()}
      </TableCell>
      <TableCell>
        <button
          onClick={handleCopy}
          className="inline-flex items-center rounded-md border bg-muted/50 px-3 py-1.5 font-mono text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground cursor-pointer"
          title="Click to copy"
        >
          {displayKey}
        </button>
      </TableCell>
      <TableCell className="text-muted-foreground">
        {formatDate(keyItem.last_used_at)}
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon-xs"
            title={revealed ? "Hide key" : "Reveal key"}
            className="cursor-pointer text-muted-foreground hover:text-foreground"
            onClick={handleReveal}
            disabled={revealing}
          >
            {revealed ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
          </Button>
          <Button
            variant="ghost"
            size="icon-xs"
            title="Copy key"
            className="cursor-pointer text-muted-foreground hover:text-foreground"
            onClick={handleCopy}
          >
            <Copy className="size-3.5" />
          </Button>
          <EditKeyDialog
            keyId={keyItem.id}
            currentName={keyItem.name}
            currentType={keyItem.key_type}
            onUpdated={onRefresh}
          >
            <Button
              variant="ghost"
              size="icon-xs"
              title="Edit key"
              className="cursor-pointer text-muted-foreground hover:text-foreground"
            >
              <Pencil className="size-3.5" />
            </Button>
          </EditKeyDialog>
          <RevokeKeyDialog
            keyName={keyItem.name}
            keyId={keyItem.id}
            onRevoked={onRefresh}
          >
            <Button
              variant="ghost"
              size="icon-xs"
              title="Revoke key"
              className="cursor-pointer text-muted-foreground hover:text-destructive"
            >
              <Trash2 className="size-3.5" />
            </Button>
          </RevokeKeyDialog>
        </div>
      </TableCell>
    </TableRow>
  );
}

export function KeysTable({ keys, onRefresh }: KeysTableProps) {
  if (keys.length === 0) {
    return (
      <div className="rounded-md border p-6 text-center">
        <p className="text-sm text-muted-foreground">
          No API keys found.{" "}
          <Link href="/keys" className="text-primary underline">
            Create one
          </Link>
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead className="text-right">Usage</TableHead>
            <TableHead>Key</TableHead>
            <TableHead>Last Used</TableHead>
            <TableHead className="w-[120px]">Options</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {keys.map((key) => (
            <KeyRow key={key.id} keyItem={key} onRefresh={onRefresh} />
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
