import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, FileText, AlertTriangle, TrendingUp, BarChart3, Activity } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { useQuery } from "@tanstack/react-query";
import { fetchDashboardStats } from "@/lib/api";
import { adminStats } from "@/lib/mock-data";
import { Skeleton } from "@/components/ui/skeleton";

const monthlyData = [
  { month: "Oct", reports: 645, disputes: 23, revenue: 3200000 },
  { month: "Nov", reports: 720, disputes: 31, revenue: 3600000 },
  { month: "Dec", reports: 580, disputes: 18, revenue: 2900000 },
  { month: "Jan", reports: 810, disputes: 28, revenue: 4050000 },
  { month: "Feb", reports: 856, disputes: 35, revenue: 4280000 },
  { month: "Mar", reports: 892, disputes: 42, revenue: 4560000 },
];

const scoreDistribution = [
  { name: "Excellent (750+)", value: 15, color: "hsl(142, 71%, 45%)" },
  { name: "Good (650-749)", value: 28, color: "hsl(160, 60%, 45%)" },
  { name: "Satisfactory (500-649)", value: 30, color: "hsl(38, 92%, 50%)" },
  { name: "Fair (350-499)", value: 18, color: "hsl(25, 95%, 53%)" },
  { name: "Poor (<350)", value: 9, color: "hsl(0, 72%, 51%)" },
];

export default function AdminDashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: fetchDashboardStats,
  });

  const statCards = [
    {
      title: "Total Scored",
      value: stats ? stats.totalScored.toLocaleString() : adminStats.totalClients.toLocaleString(),
      icon: Users,
      change: "+12.5%",
      positive: true,
    },
    {
      title: "Avg. Credit Score",
      value: stats ? Math.round(stats.avgScore).toString() : adminStats.avgCreditScore.toString(),
      icon: BarChart3,
      change: "+8pts",
      positive: true,
    },
    {
      title: "Approval Rate",
      value: stats ? `${(stats.approvalRate * 100).toFixed(1)}%` : "72.1%",
      icon: TrendingUp,
      change: "+4.2%",
      positive: true,
    },
    {
      title: "Default Rate",
      value: stats ? `${(stats.defaultRate * 100).toFixed(1)}%` : `${adminStats.npaRate}%`,
      icon: Activity,
      change: "-0.4%",
      positive: true,
    },
    {
      title: "Open Disputes",
      value: stats ? stats.openDisputes.toString() : adminStats.pendingRequests.toString(),
      icon: AlertTriangle,
      change: "+12",
      positive: false,
    },
    {
      title: "KS Statistic",
      value: stats ? stats.ksStatistic.toFixed(3) : "0.650",
      icon: FileText,
      change: "+0.01",
      positive: true,
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">Bureau performance overview and key metrics.</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {statCards.map((s) => (
          <Card key={s.title} className="border-border/50">
            <CardContent className="p-4">
              {isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-4" />
                  <Skeleton className="h-8 w-20" />
                  <Skeleton className="h-3 w-16" />
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between mb-3">
                    <s.icon className="h-4 w-4 text-muted-foreground" />
                    <span className={`text-[11px] font-medium ${s.positive ? "text-emerald-600" : "text-red-500"}`}>
                      {s.change}
                    </span>
                  </div>
                  <div className="text-2xl font-bold">{s.value}</div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">{s.title}</div>
                </>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Monthly Reports Chart */}
        <Card className="lg:col-span-2 border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Monthly Reports & Revenue</CardTitle>
            <CardDescription>Reports generated and revenue trend</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={monthlyData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis dataKey="month" className="text-xs" />
                <YAxis className="text-xs" />
                <Tooltip
                  contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }}
                />
                <Bar dataKey="reports" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                <Bar dataKey="disputes" fill="hsl(var(--destructive))" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Score Distribution */}
        <Card className="border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Score Distribution</CardTitle>
            <CardDescription>Client credit score breakdown</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={scoreDistribution} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                  {scoreDistribution.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-1 mt-2">
              {scoreDistribution.map((s) => (
                <div key={s.name} className="flex items-center gap-2 text-[11px]">
                  <div className="h-2 w-2 rounded-full" style={{ background: s.color }} />
                  <span className="text-muted-foreground flex-1">{s.name}</span>
                  <span className="font-medium">{s.value}%</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
