"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

interface RevokeKeyDialogProps {
  keyName: string;
  keyId: string;
  onRevoked: () => void;
  children: React.ReactNode;
}

export function RevokeKeyDialog({
  keyName,
  keyId,
  onRevoked,
  children,
}: RevokeKeyDialogProps) {
  const [open, setOpen] = useState(false);
  const [isRevoking, setIsRevoking] = useState(false);

  const handleRevoke = async (e: React.MouseEvent) => {
    e.preventDefault();
    setIsRevoking(true);
    try {
      await api.keys.revoke(keyId);
      toast.success("API key revoked");
      setOpen(false);
      onRevoked();
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Failed to revoke API key"
      );
    } finally {
      setIsRevoking(false);
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger asChild>{children}</AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Revoke API Key</AlertDialogTitle>
          <AlertDialogDescription>
            Are you sure you want to revoke &ldquo;{keyName}&rdquo;? This key
            will stop working immediately.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isRevoking}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            onClick={handleRevoke}
            disabled={isRevoking}
          >
            {isRevoking && <Loader2 className="animate-spin" />}
            Revoke
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
