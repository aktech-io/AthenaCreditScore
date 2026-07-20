import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { Bell, TrendingUp, TrendingDown, ArrowRightLeft } from "lucide-react";
import { fetchScoreAlerts, fetchAlertPreferences, updateAlertPreferences, type ScoreAlert } from "@/lib/api";
import { useAuth } from "@/lib/auth";

function alertTitle(a: ScoreAlert): string {
  if (a.reason === "BAND_CHANGE") {
    return `Score band changed: ${a.previous_band ?? "—"} → ${a.new_band ?? "—"}`;
  }
  return a.delta >= 0 ? "Your credit score went up" : "Your credit score went down";
}

function alertMessage(a: ScoreAlert): string {
  const dir = a.delta >= 0 ? "increased" : "decreased";
  return `Your credit score ${dir} by ${Math.abs(a.delta)} points, from ${a.previous_score} to ${a.new_score}.`;
}

function alertStyle(a: ScoreAlert): { border: string; iconBg: string; iconColor: string; Icon: typeof Bell } {
  if (a.delta < 0) {
    return { border: "border-amber-500/30", iconBg: "bg-amber-500/10", iconColor: "text-amber-500", Icon: TrendingDown };
  }
  if (a.reason === "BAND_CHANGE") {
    return { border: "border-blue-500/30", iconBg: "bg-blue-500/10", iconColor: "text-blue-500", Icon: ArrowRightLeft };
  }
  return { border: "border-emerald-500/30", iconBg: "bg-emerald-500/10", iconColor: "text-emerald-500", Icon: TrendingUp };
}

export default function ClientAlerts() {
  const { customerId } = useAuth();
  const cid = customerId ?? 0;
  const queryClient = useQueryClient();

  const { data: alertsData, isLoading } = useQuery({
    queryKey: ["client-alerts", cid],
    queryFn: () => fetchScoreAlerts(cid),
    enabled: cid > 0,
  });

  const { data: prefs } = useQuery({
    queryKey: ["client-alert-prefs", cid],
    queryFn: () => fetchAlertPreferences(cid),
    enabled: cid > 0,
  });

  const prefsMutation = useMutation({
    mutationFn: (enabled: boolean) =>
      updateAlertPreferences(cid, { score_change_enabled: enabled, min_delta: prefs?.min_delta ?? null }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["client-alert-prefs", cid] }),
  });

  const alerts = alertsData?.alerts ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Credit Alerts</h1>
        <p className="text-sm text-muted-foreground">Stay informed about changes to your credit profile.</p>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Score-change alerts</CardTitle>
          <CardDescription>
            Get notified when your score moves bands or changes by{" "}
            {prefs?.effective_min_delta ?? 10}+ points.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex items-center justify-between">
          <span className="text-sm">{prefs?.score_change_enabled === false ? "Alerts are off" : "Alerts are on"}</span>
          <Switch
            checked={prefs?.score_change_enabled !== false}
            disabled={!prefs || prefsMutation.isPending}
            onCheckedChange={(checked) => prefsMutation.mutate(checked)}
          />
        </CardContent>
      </Card>

      {isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      )}

      {!isLoading && alerts.length === 0 && (
        <Card>
          <CardContent className="p-8 text-center text-sm text-muted-foreground">
            <Bell className="h-6 w-6 mx-auto mb-2 opacity-50" />
            No alerts yet. When your credit score changes meaningfully, you'll see it here.
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {alerts.map((alert) => {
          const { border, iconBg, iconColor, Icon } = alertStyle(alert);
          return (
            <Card key={alert.alert_id} className={`border ${border}`}>
              <CardContent className="p-4 flex items-start gap-4">
                <div className={`h-9 w-9 rounded-lg flex items-center justify-center shrink-0 ${iconBg}`}>
                  <Icon className={`h-4 w-4 ${iconColor}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{alertTitle(alert)}</span>
                    <Badge variant="outline" className="h-4 text-[9px] px-1.5">
                      {alert.delta >= 0 ? `+${alert.delta}` : alert.delta}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">{alertMessage(alert)}</p>
                  <span className="text-[11px] text-muted-foreground mt-2 block">
                    {new Date(alert.created_at).toLocaleDateString("en-KE", {
                      day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
                    })}
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
