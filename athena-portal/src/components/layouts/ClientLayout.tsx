import { Outlet, useNavigate } from "react-router-dom";
import { NavLink } from "@/components/NavLink";
import {
  LayoutDashboard, FileText, AlertTriangle, ShieldCheck,
  Bell, Calculator, GraduationCap, Settings, LogOut, Lock, User, GitCompareArrows
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
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth";

const navItems = [
  { title: "Dashboard", url: "/client", icon: LayoutDashboard },
  { title: "Credit Report", url: "/client/report", icon: FileText },
  { title: "Bureau Scores", url: "/client/bureau", icon: GitCompareArrows },
  { title: "Disputes", url: "/client/disputes", icon: AlertTriangle },
  { title: "Alerts", url: "/client/alerts", icon: Bell, badge: 3 },
  { title: "Score Simulator", url: "/client/simulator", icon: Calculator },
  { title: "Credit Freeze", url: "/client/freeze", icon: Lock },
  { title: "Consent", url: "/client/consent", icon: ShieldCheck },
  { title: "Education", url: "/client/education", icon: GraduationCap },
  { title: "Settings", url: "/client/settings", icon: Settings },
];

export default function ClientLayout() {
  const { logout, customerId } = useAuth();
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
                <User className="h-5 w-5 text-primary-foreground" />
              </div>
              <div className="flex flex-col">
                <span className="font-bold text-sm text-sidebar-primary-foreground">Athena CRB</span>
                <span className="text-[11px] text-sidebar-foreground">My Credit</span>
              </div>
            </div>
          </SidebarHeader>

          <Separator className="bg-sidebar-border" />

          <SidebarContent className="px-2 py-4">
            <SidebarGroup>
              <SidebarGroupLabel className="text-sidebar-foreground/50 text-[10px] uppercase tracking-widest mb-2">
                Menu
              </SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {navItems.map((item) => (
                    <SidebarMenuItem key={item.title}>
                      <SidebarMenuButton asChild>
                        <NavLink
                          to={item.url}
                          end={item.url === "/client"}
                          className="flex items-center gap-3 px-3 py-2 rounded-md text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors text-sm"
                          activeClassName="bg-sidebar-accent text-sidebar-primary font-medium"
                        >
                          <item.icon className="h-4 w-4 shrink-0" />
                          <span className="flex-1">{item.title}</span>
                          {item.badge && (
                            <Badge variant="destructive" className="h-5 min-w-5 text-[10px] px-1.5">
                              {item.badge}
                            </Badge>
                          )}
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
                <AvatarFallback className="bg-sidebar-accent text-sidebar-accent-foreground text-xs">
                  {customerId ? `C${customerId}` : "CL"}
                </AvatarFallback>
              </Avatar>
              <div className="flex flex-col flex-1 min-w-0">
                <span className="text-xs font-medium text-sidebar-accent-foreground truncate">Customer</span>
                <span className="text-[10px] text-sidebar-foreground truncate">ID: {customerId ?? "—"}</span>
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
            <span className="text-xs text-muted-foreground">Athena Credit Bureau</span>
          </header>
          <main className="flex-1 p-6">
            <Outlet />
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}
