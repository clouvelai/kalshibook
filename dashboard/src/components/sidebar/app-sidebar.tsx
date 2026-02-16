"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Key,
  CreditCard,
  ExternalLink,
  LogOut,
} from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";

const navItems = [
  {
    title: "Overview",
    href: "/",
    icon: LayoutDashboard,
    external: false,
  },
  {
    title: "API Keys",
    href: "/keys",
    icon: Key,
    external: false,
  },
  {
    title: "Billing",
    href: "/billing",
    icon: CreditCard,
    external: false,
  },
  {
    title: "Documentation",
    href: "/api/llms-full.txt",
    icon: ExternalLink,
    external: true,
  },
];

interface AppSidebarProps {
  userEmail: string;
}

export function AppSidebar({ userEmail }: AppSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const supabase = createClient();

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.push("/login");
  };

  return (
    <Sidebar>
      <SidebarHeader className="px-4 py-5">
        <div className="flex items-center gap-2">
          <span className="text-lg font-semibold tracking-tight">
            KalshiBook
          </span>
        </div>
        <span className="text-xs text-muted-foreground">Dashboard</span>
      </SidebarHeader>

      <SidebarSeparator />

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => {
                const isActive =
                  !item.external &&
                  (item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href));

                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      asChild
                      isActive={isActive}
                      tooltip={item.title}
                    >
                      {item.external ? (
                        <a
                          href={item.href}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <item.icon className="size-4" />
                          <span>{item.title}</span>
                        </a>
                      ) : (
                        <Link href={item.href}>
                          <item.icon className="size-4" />
                          <span>{item.title}</span>
                        </Link>
                      )}
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="px-4 py-4">
        <SidebarSeparator className="mx-0 mb-3" />
        <div className="flex flex-col gap-3">
          <p className="truncate text-sm text-muted-foreground">{userEmail}</p>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground"
            onClick={handleSignOut}
          >
            <LogOut className="size-4" />
            Sign out
          </Button>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
