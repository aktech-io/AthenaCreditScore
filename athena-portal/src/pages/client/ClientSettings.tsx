import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { mockClients } from "@/lib/mock-data";
import { User, Bell, Shield, Key } from "lucide-react";

const client = mockClients[0];

export default function ClientSettings() {
  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Account Settings</h1>
        <p className="text-sm text-muted-foreground">Manage your profile and preferences.</p>
      </div>

      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2"><User className="h-4 w-4" /> Personal Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2"><Label>Full Name</Label><Input defaultValue={client.name} /></div>
            <div className="space-y-2"><Label>National ID</Label><Input defaultValue={client.nationalId} disabled /></div>
            <div className="space-y-2"><Label>Email</Label><Input type="email" defaultValue={client.email} /></div>
            <div className="space-y-2"><Label>Phone</Label><Input defaultValue={client.phone} /></div>
          </div>
          <Button>Save Changes</Button>
        </CardContent>
      </Card>

      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2"><Bell className="h-4 w-4" /> Notification Preferences</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {[
            { label: "Score changes", desc: "Get notified when your credit score changes" },
            { label: "New inquiries", desc: "Alert when someone checks your credit" },
            { label: "Account updates", desc: "Notifications about account status changes" },
            { label: "Fraud alerts", desc: "Immediate alerts for suspicious activity" },
          ].map((n) => (
            <div key={n.label} className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">{n.label}</div>
                <div className="text-xs text-muted-foreground">{n.desc}</div>
              </div>
              <Switch defaultChecked />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2"><Key className="h-4 w-4" /> Security</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2"><Label>Current Password</Label><Input type="password" /></div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2"><Label>New Password</Label><Input type="password" /></div>
            <div className="space-y-2"><Label>Confirm Password</Label><Input type="password" /></div>
          </div>
          <Button variant="outline">Update Password</Button>
        </CardContent>
      </Card>
    </div>
  );
}
