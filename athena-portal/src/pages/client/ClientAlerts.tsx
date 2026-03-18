import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Bell, TrendingUp, CreditCard, AlertTriangle, ShieldAlert, Search } from "lucide-react";
import { mockAlerts, getAlertSeverityColor } from "@/lib/mock-data-extended";

const iconMap: Record<string, typeof Bell> = {
  score_change: TrendingUp,
  new_inquiry: Search,
  new_account: CreditCard,
  delinquency: AlertTriangle,
  identity_alert: ShieldAlert,
  fraud_alert: ShieldAlert,
};

export default function ClientAlerts() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Credit Alerts</h1>
        <p className="text-sm text-muted-foreground">Stay informed about changes to your credit profile.</p>
      </div>

      <div className="space-y-3">
        {mockAlerts.map((alert) => {
          const Icon = iconMap[alert.type] || Bell;
          return (
            <Card key={alert.id} className={`border ${getAlertSeverityColor(alert.severity)} ${!alert.read ? "" : "opacity-60"}`}>
              <CardContent className="p-4 flex items-start gap-4">
                <div className={`h-9 w-9 rounded-lg flex items-center justify-center shrink-0 ${
                  alert.severity === "critical" ? "bg-red-500/10" : alert.severity === "warning" ? "bg-amber-500/10" : "bg-blue-500/10"
                }`}>
                  <Icon className={`h-4 w-4 ${
                    alert.severity === "critical" ? "text-red-500" : alert.severity === "warning" ? "text-amber-500" : "text-blue-500"
                  }`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{alert.title}</span>
                    {!alert.read && <Badge className="h-4 text-[9px] px-1.5">New</Badge>}
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">{alert.message}</p>
                  <span className="text-[11px] text-muted-foreground mt-2 block">
                    {new Date(alert.createdAt).toLocaleDateString("en-KE", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
