import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScoreGauge } from "@/components/ScoreGauge";
import { formatCurrency } from "@/lib/mock-data";
import { mockAlerts } from "@/lib/mock-data-extended";
import { Bell, TrendingUp, AlertTriangle, FileText, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { useQuery } from "@tanstack/react-query";
import { fetchCreditScore, fetchScoreHistory } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Skeleton } from "@/components/ui/skeleton";

const unreadAlerts = mockAlerts.filter((a) => !a.read);

export default function ClientDashboard() {
  const { customerId } = useAuth();
  const cid = customerId ?? 1;

  const { data: scoreData, isLoading: scoreLoading } = useQuery({
    queryKey: ["client-score", cid],
    queryFn: () => fetchCreditScore(cid),
  });

  const { data: historyData } = useQuery({
    queryKey: ["client-score-history", cid],
    queryFn: () => fetchScoreHistory(cid, 12),
  });

  const score = scoreData?.final_score ?? 0;
  const scoreBand = scoreData?.score_band ?? "—";
  const pd = scoreData?.pd_probability ?? 0;
  const baseScore = scoreData?.base_score ?? 0;

  const scoreTrend = (historyData?.data || []).map((entry) => ({
    month: new Date(entry.scored_at).toLocaleDateString("en-KE", { month: "short" }),
    score: entry.final_score,
  }));

  // Fallback if no history data
  const trendData = scoreTrend.length > 0 ? scoreTrend : [{ month: "Now", score }];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Welcome back</h1>
        <p className="text-sm text-muted-foreground">Here's your credit overview.</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Score Card */}
        <Card className="lg:row-span-2 border-border/50">
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-base">Your Credit Score</CardTitle>
            <CardDescription>Source: Athena</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-4">
            {scoreLoading ? (
              <Skeleton className="h-40 w-40 rounded-full" />
            ) : (
              <ScoreGauge score={score} size="lg" />
            )}
            <div className="flex gap-4 text-center mt-2">
              <div>
                <div className="text-xs text-muted-foreground">Score Band</div>
                <div className="font-bold">{scoreBand}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">PD</div>
                <div className="font-bold">{(pd * 100).toFixed(2)}%</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground">Base Score</div>
                <div className="font-bold">{baseScore ? Math.round(baseScore) : "—"}</div>
              </div>
            </div>
            <Button variant="outline" className="w-full mt-2" asChild>
              <Link to="/client/report">View Full Report <ArrowRight className="ml-2 h-4 w-4" /></Link>
            </Button>
          </CardContent>
        </Card>

        {/* Summary Cards */}
        <Card className="border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">CRB Contribution</span>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="text-3xl font-bold">{scoreData?.crb_contribution ?? "—"}</div>
            <div className="text-xs text-muted-foreground mt-1">
              Points from bureau data
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-muted-foreground">LLM Adjustment</span>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="text-2xl font-bold font-mono">{scoreData?.llm_adjustment ?? "—"}</div>
            <div className="text-xs text-muted-foreground mt-1">
              AI qualitative analysis points
            </div>
          </CardContent>
        </Card>

        {/* Score Trend */}
        <Card className="lg:col-span-2 border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Score Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="month" className="text-xs" />
                <YAxis domain={[0, 900]} className="text-xs" />
                <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }} />
                <Line type="monotone" dataKey="score" stroke="hsl(var(--primary))" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Recent Alerts */}
      {unreadAlerts.length > 0 && (
        <Card className="border-border/50">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Bell className="h-4 w-4" /> Recent Alerts
              </CardTitle>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/client/alerts">View All</Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {unreadAlerts.slice(0, 3).map((alert) => (
              <div key={alert.id} className="flex items-start gap-3 p-3 rounded-lg border">
                <AlertTriangle className={`h-4 w-4 mt-0.5 shrink-0 ${alert.severity === "critical" ? "text-red-500" : alert.severity === "warning" ? "text-amber-500" : "text-blue-500"}`} />
                <div>
                  <div className="text-sm font-medium">{alert.title}</div>
                  <div className="text-xs text-muted-foreground">{alert.message}</div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
