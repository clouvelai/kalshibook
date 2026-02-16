"use client";

import { useState } from "react";
import { Copy, Check, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface CreateKeyDialogProps {
  onKeyCreated: () => void;
  children: React.ReactNode;
}

export function CreateKeyDialog({
  onKeyCreated,
  children,
}: CreateKeyDialogProps) {
  const [open, setOpen] = useState(false);
  const [phase, setPhase] = useState<"form" | "show-key">("form");
  const [name, setName] = useState("");
  const [keyType, setKeyType] = useState("dev");
  const [rawKey, setRawKey] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [copied, setCopied] = useState(false);

  const resetForm = () => {
    setPhase("form");
    setName("");
    setKeyType("dev");
    setRawKey("");
    setIsCreating(false);
    setCopied(false);
  };

  const handleCreate = async () => {
    if (!name.trim()) return;
    setIsCreating(true);
    try {
      const response = await api.keys.create(name.trim(), keyType);
      setRawKey(response.data.key);
      setPhase("show-key");
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to create API key"
      );
    } finally {
      setIsCreating(false);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(rawKey);
      setCopied(true);
      toast.success("API key copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Failed to copy to clipboard");
    }
  };

  const handleClose = (isOpen: boolean) => {
    if (!isOpen) {
      if (phase === "show-key") {
        onKeyCreated();
      }
      resetForm();
    }
    setOpen(isOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent showCloseButton={phase === "form"}>
        {phase === "form" ? (
          <>
            <DialogHeader>
              <DialogTitle>Create API Key</DialogTitle>
              <DialogDescription>
                Create a new API key for accessing KalshiBook data endpoints.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label htmlFor="key-name">Name</Label>
                <Input
                  id="key-name"
                  placeholder="e.g., production, testing"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && name.trim()) handleCreate();
                  }}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="key-type">Type</Label>
                <Select value={keyType} onValueChange={setKeyType}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="dev">Development</SelectItem>
                    <SelectItem value="prod">Production</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button
                onClick={handleCreate}
                disabled={!name.trim() || isCreating}
              >
                {isCreating && <Loader2 className="animate-spin" />}
                Create Key
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>API Key Created</DialogTitle>
              <DialogDescription>
                Your API key has been created. Copy it now — you won&apos;t be
                able to see it again.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-3 py-2">
              <div className="flex items-center gap-2 rounded-md border bg-muted/50 p-3">
                <code className="flex-1 break-all font-mono text-sm">
                  {rawKey}
                </code>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleCopy}
                  className="shrink-0"
                >
                  {copied ? (
                    <Check className="size-4 text-green-600" />
                  ) : (
                    <Copy className="size-4" />
                  )}
                </Button>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={handleCopy}>
                {copied ? (
                  <Check className="size-4 text-green-600" />
                ) : (
                  <Copy className="size-4" />
                )}
                {copied ? "Copied" : "Copy"}
              </Button>
              <Button onClick={() => handleClose(false)}>Done</Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
