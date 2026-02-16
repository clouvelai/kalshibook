"use client";

import Link from "next/link";
import { Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
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

export function KeysTable({ keys, onRefresh }: KeysTableProps) {
  const handleCopyPrefix = async (prefix: string) => {
    try {
      await navigator.clipboard.writeText(prefix);
      toast.success("Key prefix copied to clipboard");
    } catch {
      toast.error("Failed to copy to clipboard");
    }
  };

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
            <TableHead className="w-[80px]">Options</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {keys.map((key) => (
            <TableRow key={key.id}>
              <TableCell className="font-medium">{key.name}</TableCell>
              <TableCell>
                <Badge
                  variant={key.key_type === "prod" ? "secondary" : "outline"}
                >
                  {key.key_type}
                </Badge>
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {key.credits_used.toLocaleString()}
              </TableCell>
              <TableCell>
                <button
                  onClick={() => handleCopyPrefix(key.key_prefix)}
                  className="inline-flex items-center rounded-md border bg-muted/50 px-3 py-1.5 font-mono text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground cursor-pointer"
                  title="Click to copy"
                >
                  {maskKey(key.key_prefix)}
                </button>
              </TableCell>
              <TableCell className="text-muted-foreground">
                {formatDate(key.last_used_at)}
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-1">
                  <EditKeyDialog
                    keyId={key.id}
                    currentName={key.name}
                    currentType={key.key_type}
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
                    keyName={key.name}
                    keyId={key.id}
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
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
