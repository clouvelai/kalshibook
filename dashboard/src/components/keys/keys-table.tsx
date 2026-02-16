"use client";

import Link from "next/link";
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

interface KeysTableProps {
  keys: KeyUsageItem[];
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

export function KeysTable({ keys }: KeysTableProps) {
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
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
