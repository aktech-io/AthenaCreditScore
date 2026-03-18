import { Outlet, useNavigate } from "react-router-dom";
import { NavLink } from "@/components/NavLink";
import {
  LayoutDashboard, Search, AlertTriangle, Settings, FileText,
  Users, LogOut, Shield, BarChart3,
  Bell, SlidersHorizontal, TrendingDown
} from "lucide-react";
import {
  SidebarProvider, Sidebar, SidebarContent, SidebarHeader,
  SidebarMenu, SidebarMenuItem, SidebarMenuButton,
  SidebarGroup, SidebarGroupLabel, SidebarGroupContent,
  SidebarFooter, SidebarTrigger, SidebarInset,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/lib/auth";

const navItems = [
  { title: "Dashboard", url: "/admin", icon: LayoutDashboard },
  { title: "Customer Search", url: "/admin/customers", icon: Search },
  { title: "Credit Reports", url: "/admin/reports", icon: FileText },
  { title: "Disputes", url: "/admin/disputes", icon: AlertTriangle },
  { title: "NPL & Portfolio", url: "/admin/npl", icon: TrendingDown },
  { title: "Analytics", url: "/admin/analytics", icon: BarChart3 },
  { title: "Model Config", url: "/admin/models", icon: Settings },
  { title: "User Management", url: "/admin/users", icon: Users },
  { title: "Notifications", url: "/admin/notifications", icon: Bell },
  { title: "Configuration", url: "/admin/config", icon: SlidersHorizontal },
  { title: "Audit Logs", url: "/admin/audit", icon: Shield },
];

export default function AdminLayout() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full">
        <Sidebar className="border-r-0">
          <SidebarHeader className="p-4">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-lg bg-primary flex items-center justify-center">
                <Shield className="h-5 w-5 text-primary-foreground" />
              </div>
              <div className="flex flex-col">
                <span className="font-bold text-sm text-sidebar-primary-foreground">Athena CRB</span>
                <span className="text-[11px] text-sidebar-foreground">Admin Portal</span>
              </div>
            </div>
          </SidebarHeader>

          <Separator className="bg-sidebar-border" />

          <SidebarContent className="px-2 py-4">
            <SidebarGroup>
              <SidebarGroupLabel className="text-sidebar-foreground/50 text-[10px] uppercase tracking-widest mb-2">
                Navigation
              </SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {navItems.map((item) => (
                    <SidebarMenuItem key={item.title}>
                      <SidebarMenuButton asChild>
                        <NavLink
                          to={item.url}
                          end={item.url === "/admin"}
                          className="flex items-center gap-3 px-3 py-2 rounded-md text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors text-sm"
                          activeClassName="bg-sidebar-accent text-sidebar-primary font-medium"
                        >
                          <item.icon className="h-4 w-4 shrink-0" />
                          <span>{item.title}</span>
                        </NavLink>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>

          <SidebarFooter className="p-4">
            <Separator className="bg-sidebar-border mb-4" />
            <div className="flex items-center gap-3">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-sidebar-accent text-sidebar-accent-foreground text-xs">AD</AvatarFallback>
              </Avatar>
              <div className="flex flex-col flex-1 min-w-0">
                <span className="text-xs font-medium text-sidebar-accent-foreground truncate">Admin</span>
                <span className="text-[10px] text-sidebar-foreground truncate">admin@athena.co.ke</span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-sidebar-foreground hover:text-sidebar-accent-foreground"
                onClick={handleLogout}
              >
                <LogOut className="h-3.5 w-3.5" />
              </Button>
            </div>
          </SidebarFooter>
        </Sidebar>

        <SidebarInset className="flex-1">
          <header className="h-14 border-b flex items-center gap-4 px-6 bg-background/80 backdrop-blur-sm sticky top-0 z-10">
            <SidebarTrigger />
            <Separator orientation="vertical" className="h-6" />
            <div className="flex-1" />
            <span className="text-xs text-muted-foreground">Athena Credit Bureau System</span>
          </header>
          <main className="flex-1 p-6">
            <Outlet />
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}
