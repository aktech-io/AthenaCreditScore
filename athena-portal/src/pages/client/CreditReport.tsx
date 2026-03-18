import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Download, Printer } from "lucide-react";
import { formatCurrency, getScoreColor } from "@/lib/mock-data";
import { ScoreGauge } from "@/components/ScoreGauge";
import { useQuery } from "@tanstack/react-query";
import { fetchCreditReport } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Skeleton } from "@/components/ui/skeleton";

export default function CreditReport() {
  const { customerId } = useAuth();
  const cid = customerId ?? 1;

  const { data: report, isLoading } = useQuery({
    queryKey: ["client-report", cid],
    queryFn: () => fetchCreditReport(cid),
  });

  const score = report?.final_score ?? 0;
  const scoreBand = report?.score_band ?? "—";
  const pd = report?.pd_probability ?? 0;
  const customerName = report?.customer_name ?? "—";
  const llmReasoning = report?.llm_reasoning ?? "";
  const crbScore = report?.crb_bureau_score ?? 0;
  const npaCount = report?.crb_npa_count ?? 0;
  const activeDefault = report?.crb_active_default ?? false;
  const baseScore = report?.base_score ?? 0;
  const crbContrib = report?.crb_contribution ?? 0;
  const llmAdj = report?.llm_adjustment ?? 0;
  const breakdown = report?.score_breakdown;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Credit Report</h1>
          <p className="text-sm text-muted-foreground">
            Full credit report for {customerName} — Source: Athena
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm"><Printer className="mr-2 h-4 w-4" /> Print</Button>
          <Button size="sm"><Download className="mr-2 h-4 w-4" /> Download PDF</Button>
        </div>
      </div>

      {isLoading ? (
        <div className="grid md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="border-border/50">
              <CardContent className="p-4"><Skeleton className="h-16 w-full" /></CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <>
          {/* Summary */}
          <div className="grid md:grid-cols-4 gap-4">
            <Card className="border-border/50">
              <CardContent className="p-4 flex items-center gap-4">
                <ScoreGauge score={score} size="sm" showLabel={false} />
                <div>
                  <div className="text-xs text-muted-foreground">Final Score</div>
                  <div className={`text-xl font-bold ${getScoreColor(score)}`}>{score}</div>
                  <div className="text-xs text-muted-foreground">{scoreBand}</div>
                </div>
              </CardContent>
            </Card>
            <Card className="border-border/50">
              <CardContent className="p-4">
                <div className="text-xs text-muted-foreground">PD Probability</div>
                <div className="text-xl font-bold font-mono mt-1">{(pd * 100).toFixed(2)}%</div>
              </CardContent>
            </Card>
            <Card className="border-border/50">
              <CardContent className="p-4">
                <div className="text-xs text-muted-foreground">CRB Bureau Score</div>
                <div className="text-xl font-bold font-mono mt-1">{crbScore || "—"}</div>
              </CardContent>
            </Card>
            <Card className="border-border/50">
              <CardContent className="p-4">
                <div className="text-xs text-muted-foreground">NPA Count</div>
                <div className="text-xl font-bold font-mono mt-1">{npaCount}</div>
                {activeDefault && <Badge variant="destructive" className="mt-1 text-[10px]">Active Default</Badge>}
              </CardContent>
            </Card>
          </div>

          {/* Score Breakdown */}
          <Card className="border-border/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Score Composition</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4 text-center">
                <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                  <div className="text-2xl font-bold text-emerald-600">{baseScore ? Math.round(baseScore) : "—"}</div>
                  <div className="text-xs text-muted-foreground">Base Score</div>
                </div>
                <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                  <div className="text-2xl font-bold text-blue-600">{crbContrib ? Math.round(crbContrib) : "—"}</div>
                  <div className="text-xs text-muted-foreground">CRB Contribution</div>
                </div>
                <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                  <div className="text-2xl font-bold text-amber-600">{llmAdj ?? "—"}</div>
                  <div className="text-xs text-muted-foreground">LLM Adjustment</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Dimension Breakdown */}
          {breakdown && (
            <Card className="border-border/50">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Dimension Breakdown</CardTitle>
                <CardDescription>Individual scoring dimensions from the base scorecard</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {[
                    { label: "Income Stability", value: breakdown.income_stability_score },
                    { label: "Income Level", value: breakdown.income_level_score },
                    { label: "Savings Rate", value: breakdown.savings_rate_score },
                    { label: "Low Balance Frequency", value: breakdown.low_balance_score },
                    { label: "Transaction Diversity", value: breakdown.transaction_diversity },
                  ].filter((d) => d.value !== undefined).map((dim) => (
                    <div key={dim.label} className="flex items-center gap-4">
                      <span className="text-sm w-44">{dim.label}</span>
                      <div className="flex-1 h-3 bg-muted rounded-full overflow-hidden">
                        <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${Math.min(100, Math.max(0, (dim.value || 0)))}%` }} />
                      </div>
                      <span className="text-sm font-mono font-medium w-12 text-right">{dim.value?.toFixed(1)}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* LLM Reasoning */}
          {llmReasoning && (
            <Card className="border-border/50">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">AI Analysis Reasoning</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground leading-relaxed">{llmReasoning}</p>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
