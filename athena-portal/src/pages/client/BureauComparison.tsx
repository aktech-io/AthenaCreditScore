import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScoreGauge } from "@/components/ScoreGauge";
import { mockBureauScores } from "@/lib/mock-data-extended";
import { getScoreColor, getScoreLabel } from "@/lib/mock-data";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { ArrowUp, ArrowDown, Minus, Brain, Calculator, Info } from "lucide-react";

const tooltipStyle = { background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: "8px", fontSize: "12px" };

const impactIcons = {
  positive: <ArrowUp className="h-3.5 w-3.5 text-emerald-500" />,
  negative: <ArrowDown className="h-3.5 w-3.5 text-red-500" />,
  neutral: <Minus className="h-3.5 w-3.5 text-muted-foreground" />,
};

const comparisonData = mockBureauScores.map((b) => ({
  bureau: b.bureau,
  score: b.score,
  baseScore: b.baseScore,
  aiInsight: b.aiInsight,
}));

export default function BureauComparison() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Bureau Score Comparison</h1>
        <p className="text-sm text-muted-foreground">Compare your scores across multiple credit bureaus with detailed factor breakdowns.</p>
      </div>

      {/* Score Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {mockBureauScores.map((bureau) => (
          <Card key={bureau.bureau} className={`border-border/50 ${bureau.bureau === "Athena" ? "ring-2 ring-primary/20" : ""}`}>
            <CardHeader className="text-center pb-2">
              <div className="flex items-center justify-center gap-2">
                <CardTitle className="text-base">{bureau.bureau}</CardTitle>
                {bureau.bureau === "Athena" && <Badge className="bg-primary/10 text-primary border-primary/20 text-[10px]">AI-Enhanced</Badge>}
              </div>
              <CardDescription>Updated {bureau.lastUpdated}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center gap-3">
              <ScoreGauge score={bureau.score} size="md" />
              <div className="grid grid-cols-2 gap-3 w-full mt-2">
                <div className="text-center p-2 rounded-lg bg-muted/50">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <Calculator className="h-3 w-3 text-muted-foreground" />
                    <span className="text-[10px] text-muted-foreground">Base Score</span>
                  </div>
                  <div className="text-lg font-bold font-mono">{bureau.baseScore}</div>
                </div>
                <div className="text-center p-2 rounded-lg bg-muted/50">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <Brain className="h-3 w-3 text-muted-foreground" />
                    <span className="text-[10px] text-muted-foreground">AI Insight</span>
                  </div>
                  <div className={`text-lg font-bold font-mono ${bureau.aiInsight > 0 ? "text-emerald-600" : bureau.aiInsight < 0 ? "text-red-500" : "text-muted-foreground"}`}>
                    {bureau.aiInsight > 0 ? "+" : ""}{bureau.aiInsight}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Comparison Chart */}
      <Card className="border-border/50">
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Score Comparison</CardTitle>
          <CardDescription>Base Score vs AI Insight across bureaus</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={comparisonData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="bureau" className="text-xs" />
              <YAxis className="text-xs" />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="baseScore" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} name="Base Score" stackId="score" />
              <Bar dataKey="aiInsight" fill="hsl(142, 71%, 45%)" radius={[4, 4, 0, 0]} name="AI Insight" stackId="score" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Athena Score Breakdown - detailed */}
      <Card className="border-border/50">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <CardTitle className="text-base">Athena Score Breakdown</CardTitle>
            <Badge className="bg-primary/10 text-primary border-primary/20 text-[10px]">Hybrid AI Model</Badge>
          </div>
          <CardDescription>
            Your Athena score uses a hybrid model: 70% quantitative base score + 30% AI qualitative analysis. 
            The AI analyzes your transaction patterns for behavioral signals.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4 p-3 rounded-lg bg-accent/30 border border-accent flex items-start gap-3">
            <Info className="h-4 w-4 text-accent-foreground mt-0.5 shrink-0" />
            <p className="text-xs text-accent-foreground">
              <strong>How it works:</strong> The Base Score ({mockBureauScores[0].baseScore}) is calculated from your income stability, savings patterns, 
              and payment history. The AI Insight ({mockBureauScores[0].aiInsight > 0 ? "+" : ""}{mockBureauScores[0].aiInsight}) is determined by 
              AI analysis of your transaction descriptions, identifying positive signals (educational spending, business investments) and negative signals 
              (risky spending patterns).
            </p>
          </div>

          <Tabs defaultValue="athena">
            <TabsList>
              {mockBureauScores.map((b) => (
                <TabsTrigger key={b.bureau} value={b.bureau.toLowerCase()}>{b.bureau}</TabsTrigger>
              ))}
            </TabsList>
            {mockBureauScores.map((bureau) => (
              <TabsContent key={bureau.bureau} value={bureau.bureau.toLowerCase()} className="mt-4">
                <div className="space-y-3">
                  {bureau.factors.map((factor, i) => (
                    <div key={i} className="flex items-start gap-3 p-3 rounded-lg border bg-card">
                      <div className="mt-0.5">{impactIcons[factor.impact]}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">{factor.factor}</span>
                          <span className={`text-sm font-bold font-mono ${factor.points > 0 ? "text-emerald-600" : factor.points < 0 ? "text-red-500" : "text-muted-foreground"}`}>
                            {factor.points > 0 ? "+" : ""}{factor.points} pts
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5">{factor.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </TabsContent>
            ))}
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
