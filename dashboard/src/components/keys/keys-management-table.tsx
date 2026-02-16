"use client";

import { Copy, MoreHorizontal, Trash2 } from "lucide-react";
import { toast } from "sonner";
import type { KeyUsageItem } from "@/types/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RevokeKeyDialog } from "@/components/keys/revoke-key-dialog";

interface KeysManagementTableProps {
  keys: KeyUsageItem[];
  onRefresh: () => void;
}

export function KeysManagementTable({
  keys,
  onRefresh,
}: KeysManagementTableProps) {
  // Sort by created_at descending (newest first)
  const sortedKeys = [...keys].sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  const handleCopyPrefix = async (prefix: string) => {
    try {
      await navigator.clipboard.writeText(prefix);
      toast.success("Key prefix copied to clipboard");
    } catch {
      toast.error("Failed to copy to clipboard");
    }
  };

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Usage</TableHead>
          <TableHead>Key</TableHead>
          <TableHead className="w-[60px]">Options</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sortedKeys.map((key) => (
          <TableRow key={key.id}>
            <TableCell className="font-medium">{key.name}</TableCell>
            <TableCell>
              <Badge
                variant={key.key_type === "prod" ? "secondary" : "outline"}
              >
                {key.key_type}
              </Badge>
            </TableCell>
            <TableCell className="text-muted-foreground">
              {key.credits_used.toLocaleString()} credits
            </TableCell>
            <TableCell>
              <code className="rounded bg-muted px-2 py-1 font-mono text-sm">
                {key.key_prefix}...
              </code>
            </TableCell>
            <TableCell>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon-sm">
                    <MoreHorizontal className="size-4" />
                    <span className="sr-only">Options</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    onClick={() => handleCopyPrefix(key.key_prefix)}
                  >
                    <Copy className="size-4" />
                    Copy key prefix
                  </DropdownMenuItem>
                  <RevokeKeyDialog
                    keyName={key.name}
                    keyId={key.id}
                    onRevoked={onRefresh}
                  >
                    <DropdownMenuItem
                      variant="destructive"
                      onSelect={(e) => e.preventDefault()}
                    >
                      <Trash2 className="size-4" />
                      Revoke
                    </DropdownMenuItem>
                  </RevokeKeyDialog>
                </DropdownMenuContent>
              </DropdownMenu>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
