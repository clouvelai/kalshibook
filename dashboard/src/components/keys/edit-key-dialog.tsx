"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
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

interface EditKeyDialogProps {
  keyId: string;
  currentName: string;
  currentType: string;
  onUpdated: () => void;
  children: React.ReactNode;
}

export function EditKeyDialog({
  keyId,
  currentName,
  currentType,
  onUpdated,
  children,
}: EditKeyDialogProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(currentName);
  const [keyType, setKeyType] = useState(currentType);
  const [isSaving, setIsSaving] = useState(false);

  // Reset form state when dialog opens
  useEffect(() => {
    if (open) {
      setName(currentName);
      setKeyType(currentType);
    }
  }, [open, currentName, currentType]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await api.keys.update(keyId, { name, key_type: keyType });
      toast.success("API key updated");
      setOpen(false);
      onUpdated();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to update API key"
      );
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit API Key</DialogTitle>
          <DialogDescription>
            Update the name or type for this API key.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="key-name">Name</Label>
            <Input
              id="key-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="key-type">Type</Label>
            <Select value={keyType} onValueChange={setKeyType}>
              <SelectTrigger id="key-type">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="dev">dev</SelectItem>
                <SelectItem value="prod">prod</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={isSaving}
          >
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving && <Loader2 className="animate-spin" />}
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
