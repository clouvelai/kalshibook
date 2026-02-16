"use client";

import { SidebarProvider, SidebarInset, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/sidebar/app-sidebar";

interface DashboardShellProps {
  userEmail: string;
  children: React.ReactNode;
}

export function DashboardShell({ userEmail, children }: DashboardShellProps) {
  return (
    <SidebarProvider>
      <AppSidebar userEmail={userEmail} />
      <SidebarInset>
        <header className="flex h-14 items-center border-b px-6 md:hidden">
          <SidebarTrigger />
        </header>
        <main className="flex-1 overflow-auto p-6 md:p-8">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  );
}
