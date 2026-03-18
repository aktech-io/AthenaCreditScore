import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { mockAdminUsers, getRoleColor } from "@/lib/mock-data-extended";
import { Users, Plus, Search, Shield, MoreHorizontal, UserCog, Lock, Unlock, Mail } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchAdminUsers, inviteUser, type AdminUser } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";

const roleLabels: Record<string, string> = {
  super_admin: "Super Admin",
  admin: "Admin",
  analyst: "Analyst",
  auditor: "Auditor",
  viewer: "Viewer",
  ADMIN: "Admin",
  ROLE_ADMIN: "Admin",
};

const statusIcons: Record<string, JSX.Element> = {
  active: <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block" />,
  inactive: <span className="h-2 w-2 rounded-full bg-muted-foreground inline-block" />,
  locked: <span className="h-2 w-2 rounded-full bg-red-500 inline-block" />,
  ACTIVE: <span className="h-2 w-2 rounded-full bg-emerald-500 inline-block" />,
  INACTIVE: <span className="h-2 w-2 rounded-full bg-muted-foreground inline-block" />,
  LOCKED: <span className="h-2 w-2 rounded-full bg-red-500 inline-block" />,
};

interface UserDisplay {
  id: string;
  name: string;
  email: string;
  role: string;
  department: string;
  status: string;
  lastLogin: string;
}

function mapApiUser(u: AdminUser): UserDisplay {
  const name = u.name || u.username || "—";
  const roles = u.roles || [];
  const role = roles.length > 0 ? roles[0] : "viewer";
  return {
    id: String(u.id),
    name,
    email: u.email || "—",
    role: role.toLowerCase(),
    department: u.department || (u.groups && u.groups.length > 0 ? u.groups[0] : "—"),
    status: (u.status || "active").toLowerCase(),
    lastLogin: u.lastLogin || "—",
  };
}

export default function UserManagement() {
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const { toast } = useToast();

  const { data: apiUsers, isLoading, isError } = useQuery({
    queryKey: ["admin-users"],
    queryFn: fetchAdminUsers,
  });

  const useMock = isError || !apiUsers || apiUsers.length === 0;
  const allUsers: UserDisplay[] = useMock
    ? mockAdminUsers.map((u) => ({ id: u.id, name: u.name, email: u.email, role: u.role, department: u.department, status: u.status, lastLogin: u.lastLogin }))
    : apiUsers!.map(mapApiUser);

  const filtered = allUsers.filter((u) => {
    const matchSearch = u.name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase());
    const matchRole = roleFilter === "all" || u.role === roleFilter;
    return matchSearch && matchRole;
  });

  const stats = {
    total: allUsers.length,
    active: allUsers.filter((u) => u.status === "active").length,
    locked: allUsers.filter((u) => u.status === "locked").length,
  };

  const [invName, setInvName] = useState("");
  const [invEmail, setInvEmail] = useState("");

  const handleInvite = async () => {
    try {
      await inviteUser({ name: invName, email: invEmail });
      toast({ title: "Invitation sent", description: `Invited ${invEmail}` });
      setInvName("");
      setInvEmail("");
    } catch {
      toast({ variant: "destructive", title: "Failed to send invitation" });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">User Management</h1>
          <p className="text-sm text-muted-foreground">Manage admin users, roles, and permissions.</p>
        </div>
        <Dialog>
          <DialogTrigger asChild>
            <Button><Plus className="h-4 w-4 mr-2" /> Add User</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add New User</DialogTitle>
              <DialogDescription>Create a new admin user with role-based access.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 pt-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Full Name</Label><Input placeholder="Enter full name" value={invName} onChange={(e) => setInvName(e.target.value)} /></div>
                <div className="space-y-2"><Label>Email</Label><Input type="email" placeholder="email@athena.co.ke" value={invEmail} onChange={(e) => setInvEmail(e.target.value)} /></div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Role</Label>
                  <Select><SelectTrigger><SelectValue placeholder="Select role" /></SelectTrigger>
                    <SelectContent>
                      {Object.entries(roleLabels).filter(([k]) => !k.startsWith("ROLE_")).map(([k, v]) => (<SelectItem key={k} value={k}>{v}</SelectItem>))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2"><Label>Department</Label><Input placeholder="e.g. Operations" /></div>
              </div>
              <Button className="w-full" onClick={handleInvite}><Mail className="h-4 w-4 mr-2" /> Send Invitation</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="border-border/50">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center"><Users className="h-5 w-5 text-primary" /></div>
            <div><div className="text-2xl font-bold">{stats.total}</div><div className="text-xs text-muted-foreground">Total Users</div></div>
          </CardContent>
        </Card>
        <Card className="border-border/50">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-emerald-500/10 flex items-center justify-center"><UserCog className="h-5 w-5 text-emerald-600" /></div>
            <div><div className="text-2xl font-bold">{stats.active}</div><div className="text-xs text-muted-foreground">Active Users</div></div>
          </CardContent>
        </Card>
        <Card className="border-border/50">
          <CardContent className="p-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-red-500/10 flex items-center justify-center"><Lock className="h-5 w-5 text-red-600" /></div>
            <div><div className="text-2xl font-bold">{stats.locked}</div><div className="text-xs text-muted-foreground">Locked Accounts</div></div>
          </CardContent>
        </Card>
      </div>

      {/* Filters & Table */}
      <Card className="border-border/50">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Search users..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" />
            </div>
            <Select value={roleFilter} onValueChange={setRoleFilter}>
              <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Roles</SelectItem>
                {Object.entries(roleLabels).filter(([k]) => !k.startsWith("ROLE_")).map(([k, v]) => (<SelectItem key={k} value={k}>{v}</SelectItem>))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow><TableHead>User</TableHead><TableHead>Role</TableHead><TableHead>Department</TableHead><TableHead>Status</TableHead><TableHead>Last Login</TableHead><TableHead className="text-right">Actions</TableHead></TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 6 }).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-20" /></TableCell>
                    ))}
                  </TableRow>
                ))
              ) : (
                filtered.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-xs font-medium text-primary">{user.name.split(" ").map((n) => n[0]).join("").slice(0, 2)}</div>
                        <div><div className="font-medium text-sm">{user.name}</div><div className="text-xs text-muted-foreground">{user.email}</div></div>
                      </div>
                    </TableCell>
                    <TableCell><Badge variant="outline" className={`${getRoleColor(user.role as any)} text-[11px]`}><Shield className="h-3 w-3 mr-1" />{roleLabels[user.role] || user.role}</Badge></TableCell>
                    <TableCell className="text-sm">{user.department}</TableCell>
                    <TableCell><div className="flex items-center gap-2 text-sm capitalize">{statusIcons[user.status] || statusIcons["active"]}{user.status}</div></TableCell>
                    <TableCell className="text-xs text-muted-foreground">{user.lastLogin !== "—" ? new Date(user.lastLogin).toLocaleDateString() : "—"}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        {user.status === "locked" ? (
                          <Button variant="ghost" size="icon" className="h-7 w-7"><Unlock className="h-3.5 w-3.5" /></Button>
                        ) : (
                          <Button variant="ghost" size="icon" className="h-7 w-7"><Lock className="h-3.5 w-3.5" /></Button>
                        )}
                        <Button variant="ghost" size="icon" className="h-7 w-7"><MoreHorizontal className="h-3.5 w-3.5" /></Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
