import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { mockSystemNotifications } from "@/lib/mock-data-extended";
import { Bell, Plus, Send, Clock, FileText, Mail, Smartphone, Globe, CheckCircle, XCircle } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchNotificationConfig } from "@/lib/api";

const channelIcons: Record<string, JSX.Element> = {
  email: <Mail className="h-3.5 w-3.5" />,
  sms: <Smartphone className="h-3.5 w-3.5" />,
  in_app: <Bell className="h-3.5 w-3.5" />,
  all: <Globe className="h-3.5 w-3.5" />,
};

const statusConfig: Record<string, { color: string; icon: JSX.Element }> = {
  sent: { color: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20", icon: <CheckCircle className="h-3 w-3" /> },
  scheduled: { color: "bg-blue-500/10 text-blue-600 border-blue-500/20", icon: <Clock className="h-3 w-3" /> },
  draft: { color: "bg-muted text-muted-foreground border-border", icon: <FileText className="h-3 w-3" /> },
  failed: { color: "bg-red-500/10 text-red-600 border-red-500/20", icon: <XCircle className="h-3 w-3" /> },
};

export default function NotificationManagement() {
  const [tab, setTab] = useState("all");

  // Fetch notification config from API for display
  const { data: emailConfig } = useQuery({
    queryKey: ["notification-config", "EMAIL"],
    queryFn: () => fetchNotificationConfig("EMAIL"),
  });
  const { data: smsConfig } = useQuery({
    queryKey: ["notification-config", "SMS"],
    queryFn: () => fetchNotificationConfig("SMS"),
  });

  // Keep using mock notifications for the list since no list endpoint exists
  const filtered = tab === "all" ? mockSystemNotifications : mockSystemNotifications.filter((n) => n.status === tab);

  const stats = {
    sent: mockSystemNotifications.filter((n) => n.status === "sent").length,
    scheduled: mockSystemNotifications.filter((n) => n.status === "scheduled").length,
    drafts: mockSystemNotifications.filter((n) => n.status === "draft").length,
    avgOpenRate: mockSystemNotifications.filter((n) => n.openRate).reduce((sum, n) => sum + (n.openRate || 0), 0) / mockSystemNotifications.filter((n) => n.openRate).length,
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Notifications</h1>
          <p className="text-sm text-muted-foreground">
            Manage system notifications, alerts, and communications.
            {emailConfig && ` Email: ${emailConfig.enabled ? "Enabled" : "Disabled"}`}
            {smsConfig && ` | SMS: ${smsConfig.enabled ? "Enabled" : "Disabled"}`}
          </p>
        </div>
        <Dialog>
          <DialogTrigger asChild>
            <Button><Plus className="h-4 w-4 mr-2" /> New Notification</Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>Create Notification</DialogTitle>
              <DialogDescription>Compose and schedule a new notification.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 pt-4">
              <div className="space-y-2"><Label>Title</Label><Input placeholder="Notification title" /></div>
              <div className="space-y-2"><Label>Message</Label><Textarea placeholder="Write your message..." rows={4} /></div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Channel</Label>
                  <Select><SelectTrigger><SelectValue placeholder="Select channel" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="email">Email</SelectItem>
                      <SelectItem value="sms">SMS</SelectItem>
                      <SelectItem value="in_app">In-App</SelectItem>
                      <SelectItem value="all">All Channels</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Audience</Label>
                  <Select><SelectTrigger><SelectValue placeholder="Select audience" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all_clients">All Clients</SelectItem>
                      <SelectItem value="all_admins">All Admins</SelectItem>
                      <SelectItem value="segment">Segment</SelectItem>
                      <SelectItem value="specific">Specific Users</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" className="flex-1"><Clock className="h-4 w-4 mr-2" /> Schedule</Button>
                <Button className="flex-1"><Send className="h-4 w-4 mr-2" /> Send Now</Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Sent", value: stats.sent, icon: <Send className="h-4 w-4 text-emerald-600" />, bg: "bg-emerald-500/10" },
          { label: "Scheduled", value: stats.scheduled, icon: <Clock className="h-4 w-4 text-blue-600" />, bg: "bg-blue-500/10" },
          { label: "Drafts", value: stats.drafts, icon: <FileText className="h-4 w-4 text-muted-foreground" />, bg: "bg-muted" },
          { label: "Avg Open Rate", value: `${stats.avgOpenRate.toFixed(1)}%`, icon: <Mail className="h-4 w-4 text-primary" />, bg: "bg-primary/10" },
        ].map((s) => (
          <Card key={s.label} className="border-border/50">
            <CardContent className="p-4 flex items-center gap-3">
              <div className={`h-10 w-10 rounded-lg ${s.bg} flex items-center justify-center`}>{s.icon}</div>
              <div><div className="text-2xl font-bold">{s.value}</div><div className="text-xs text-muted-foreground">{s.label}</div></div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Table */}
      <Card className="border-border/50">
        <CardHeader className="pb-3">
          <Tabs value={tab} onValueChange={setTab}>
            <TabsList>
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="sent">Sent</TabsTrigger>
              <TabsTrigger value="scheduled">Scheduled</TabsTrigger>
              <TabsTrigger value="draft">Drafts</TabsTrigger>
            </TabsList>
          </Tabs>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow><TableHead>Notification</TableHead><TableHead>Channel</TableHead><TableHead>Audience</TableHead><TableHead>Status</TableHead><TableHead>Recipients</TableHead><TableHead>Open Rate</TableHead></TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((n) => {
                const sc = statusConfig[n.status];
                return (
                  <TableRow key={n.id}>
                    <TableCell>
                      <div><div className="font-medium text-sm">{n.title}</div><div className="text-xs text-muted-foreground line-clamp-1 max-w-xs">{n.message}</div></div>
                    </TableCell>
                    <TableCell><div className="flex items-center gap-1.5 text-sm capitalize">{channelIcons[n.channel]}{n.channel.replace("_", " ")}</div></TableCell>
                    <TableCell className="text-sm capitalize">{n.targetAudience.replace("_", " ")}</TableCell>
                    <TableCell><Badge variant="outline" className={`${sc.color} text-[11px]`}>{sc.icon}<span className="ml-1 capitalize">{n.status}</span></Badge></TableCell>
                    <TableCell className="text-sm font-mono">{n.recipients.toLocaleString()}</TableCell>
                    <TableCell className="text-sm">{n.openRate ? `${n.openRate}%` : "—"}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
