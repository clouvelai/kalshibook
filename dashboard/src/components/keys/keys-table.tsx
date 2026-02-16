"use client";

import Link from "next/link";
import { Copy, Pencil, Trash2 } from "lucide-react";
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
            <TableHead className="w-[100px]">Actions</TableHead>
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
              <TableCell className="font-mono text-muted-foreground">
                {key.key_prefix}...
              </TableCell>
              <TableCell className="text-muted-foreground">
                {formatDate(key.last_used_at)}
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-0.5">
                  <Button
                    variant="ghost"
                    size="icon-xs"
                    title="Copy prefix"
                    onClick={() => handleCopyPrefix(key.key_prefix)}
                  >
                    <Copy className="size-3" />
                  </Button>
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
                    >
                      <Pencil className="size-3" />
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
                      className="text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="size-3" />
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
