import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { mockNPLSummary, mockLoanPortfolio, formatLargeNumber } from "@/lib/mock-data-extended";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, AreaChart, Area, Cell, PieChart, Pie } from "recharts";
import { AlertTriangle, TrendingDown, DollarSign, PieChart as PieIcon, Activity, Landmark } from "lucide-react";
import { formatCurrency } from "@/lib/mock-data";

const tooltipStyle = { background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" };

const sectorColors = ["hsl(217, 91%, 50%)", "hsl(160, 60%, 45%)", "hsl(38, 92%, 50%)", "hsl(0, 72%, 51%)", "hsl(270, 60%, 55%)"];

export default function NPLAnalytics() {
  const npl = mockNPLSummary;
  const portfolio = mockLoanPortfolio;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">NPL & Portfolio Analytics</h1>
        <p className="text-sm text-muted-foreground">Non-performing loans analysis, portfolio health, and risk monitoring.</p>
      </div>

      {/* KPI Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-4">
        {[
          { label: "NPL Ratio", value: `${npl.nplRatio}%`, icon: <AlertTriangle className="h-4 w-4 text-red-500" />, change: "-0.8%", positive: true },
          { label: "Total NPLs", value: npl.totalNPLs.toLocaleString(), icon: <TrendingDown className="h-4 w-4 text-amber-500" />, change: "-86", positive: true },
          { label: "NPL Exposure", value: `KES ${formatLargeNumber(npl.totalExposure)}`, icon: <DollarSign className="h-4 w-4 text-red-500" />, change: "-2.1%", positive: true },
          { label: "Active Loans", value: portfolio.activeLoans.toLocaleString(), icon: <Landmark className="h-4 w-4 text-primary" />, change: "+340", positive: true },
          { label: "Default Rate", value: `${portfolio.defaultRate}%`, icon: <Activity className="h-4 w-4 text-emerald-500" />, change: "-0.3%", positive: true },
          { label: "Provision Req.", value: `KES ${formatLargeNumber(npl.provisionRequired)}`, icon: <PieIcon className="h-4 w-4 text-amber-500" />, change: "-1.5%", positive: true },
        ].map((s) => (
          <Card key={s.label} className="border-border/50">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-3">
                {s.icon}
                <span className={`text-[11px] font-medium ${s.positive ? "text-emerald-600" : "text-red-500"}`}>{s.change}</span>
              </div>
              <div className="text-xl font-bold">{s.value}</div>
              <div className="text-[11px] text-muted-foreground mt-0.5">{s.label}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="npl">
        <TabsList>
          <TabsTrigger value="npl">NPL Analysis</TabsTrigger>
          <TabsTrigger value="portfolio">Loan Portfolio</TabsTrigger>
          <TabsTrigger value="risk">Risk by Score Band</TabsTrigger>
        </TabsList>

        <TabsContent value="npl" className="space-y-6 mt-4">
          <div className="grid lg:grid-cols-2 gap-6">
            {/* NPL Trend */}
            <Card className="border-border/50">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">NPL Ratio Trend</CardTitle>
                <CardDescription>6-month trend of non-performing loan ratio</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={260}>
                  <AreaChart data={npl.trend}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="month" className="text-xs" />
                    <YAxis domain={[7, 10]} className="text-xs" />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Area type="monotone" dataKey="nplRatio" stroke="hsl(0, 72%, 51%)" fill="hsl(0, 72%, 51%, 0.1)" strokeWidth={2} name="NPL Ratio %" />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* NPL by Sector */}
            <Card className="border-border/50">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">NPL by Sector</CardTitle>
                <CardDescription>Non-performing loans distribution across sectors</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={npl.bySector} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis type="number" className="text-xs" />
                    <YAxis type="category" dataKey="sector" className="text-xs" width={110} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Bar dataKey="nplRate" fill="hsl(0, 72%, 51%)" radius={[0, 4, 4, 0]} name="NPL Rate %" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Ageing Analysis */}
            <Card className="lg:col-span-2 border-border/50">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">NPL Ageing Analysis</CardTitle>
                <CardDescription>Breakdown of NPLs by days in arrears</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow><TableHead>Ageing Bucket</TableHead><TableHead className="text-right">Count</TableHead><TableHead className="text-right">Exposure (KES)</TableHead><TableHead className="text-right">% of Total</TableHead></TableRow>
                  </TableHeader>
                  <TableBody>
                    {npl.ageing.map((a) => (
                      <TableRow key={a.bucket}>
                        <TableCell className="font-medium">{a.bucket}</TableCell>
                        <TableCell className="text-right font-mono">{a.count.toLocaleString()}</TableCell>
                        <TableCell className="text-right font-mono">{formatLargeNumber(a.amount)}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <div className="w-16 h-2 bg-muted rounded-full overflow-hidden">
                              <div className="h-full bg-destructive rounded-full" style={{ width: `${(a.count / npl.totalNPLs) * 100}%` }} />
                            </div>
                            <span className="text-xs">{((a.count / npl.totalNPLs) * 100).toFixed(1)}%</span>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="portfolio" className="space-y-6 mt-4">
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Monthly Disbursements */}
            <Card className="border-border/50">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Monthly Loan Disbursements</CardTitle>
                <CardDescription>Loans disbursed and defaults per month</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={portfolio.monthlyDisbursements}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="month" className="text-xs" />
                    <YAxis className="text-xs" />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Bar dataKey="count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} name="Loans" />
                    <Bar dataKey="defaults" fill="hsl(var(--destructive))" radius={[4, 4, 0, 0]} name="Defaults" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Portfolio Status */}
            <Card className="border-border/50">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Portfolio by Status</CardTitle>
                <CardDescription>Loan status distribution</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {portfolio.byStatus.map((s, i) => {
                    const pct = (s.count / portfolio.totalLoans) * 100;
                    const colors = ["hsl(var(--primary))", "hsl(142, 71%, 45%)", "hsl(0, 72%, 51%)", "hsl(38, 92%, 50%)"];
                    return (
                      <div key={s.status}>
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-sm font-medium">{s.status}</span>
                          <div className="flex items-center gap-3">
                            <span className="text-xs text-muted-foreground">{s.count.toLocaleString()} loans</span>
                            <span className="text-sm font-bold">{pct.toFixed(1)}%</span>
                          </div>
                        </div>
                        <div className="h-3 bg-muted rounded-full overflow-hidden">
                          <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: colors[i] }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="risk" className="space-y-6 mt-4">
          <Card className="border-border/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Default Rate by Score Band</CardTitle>
              <CardDescription>How the Athena score predicts default probability — validating the hybrid model</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid lg:grid-cols-2 gap-6">
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={portfolio.byScoreBand}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="band" className="text-xs" />
                    <YAxis className="text-xs" />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Bar dataKey="defaultRate" fill="hsl(var(--destructive))" radius={[4, 4, 0, 0]} name="Default Rate %" />
                  </BarChart>
                </ResponsiveContainer>

                <Table>
                  <TableHeader>
                    <TableRow><TableHead>Score Band</TableHead><TableHead className="text-right">Approved</TableHead><TableHead className="text-right">Defaulted</TableHead><TableHead className="text-right">Default Rate</TableHead></TableRow>
                  </TableHeader>
                  <TableBody>
                    {portfolio.byScoreBand.map((b) => (
                      <TableRow key={b.band}>
                        <TableCell className="font-medium font-mono">{b.band}</TableCell>
                        <TableCell className="text-right font-mono">{b.approved.toLocaleString()}</TableCell>
                        <TableCell className="text-right font-mono">{b.defaulted}</TableCell>
                        <TableCell className="text-right">
                          <Badge variant="outline" className={`text-[11px] ${b.defaultRate > 10 ? "bg-red-500/10 text-red-600 border-red-500/20" : b.defaultRate > 5 ? "bg-amber-500/10 text-amber-600 border-amber-500/20" : "bg-emerald-500/10 text-emerald-600 border-emerald-500/20"}`}>
                            {b.defaultRate}%
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
