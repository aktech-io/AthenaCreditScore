import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ScoreGauge } from "@/components/ScoreGauge";
import { mockReport } from "@/lib/mock-data";
import { simulatorScenarios } from "@/lib/mock-data-extended";
import { Calculator, ArrowUp, ArrowDown, RotateCcw } from "lucide-react";

export default function ScoreSimulator() {
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const baseScore = mockReport.bureauScore;

  const toggle = (i: number) => {
    const next = new Set(selected);
    next.has(i) ? next.delete(i) : next.add(i);
    setSelected(next);
  };

  const totalImpact = Array.from(selected).reduce((sum, i) => sum + simulatorScenarios[i].impact, 0);
  const projectedScore = Math.max(0, Math.min(900, baseScore + totalImpact));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Score Simulator</h1>
        <p className="text-sm text-muted-foreground">See how different actions could impact your credit score.</p>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Projected Score */}
        <Card className="border-border/50 text-center">
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Projected Score</CardTitle>
            <CardDescription>Based on selected actions</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-2">
            <ScoreGauge score={projectedScore} size="lg" />
            {totalImpact !== 0 && (
              <div className={`flex items-center gap-1 text-sm font-medium ${totalImpact > 0 ? "text-emerald-600" : "text-red-500"}`}>
                {totalImpact > 0 ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />}
                {totalImpact > 0 ? "+" : ""}{totalImpact} points
              </div>
            )}
            <Button variant="ghost" size="sm" className="mt-2" onClick={() => setSelected(new Set())}>
              <RotateCcw className="h-3.5 w-3.5 mr-1" /> Reset
            </Button>
          </CardContent>
        </Card>

        {/* Scenarios */}
        <Card className="lg:col-span-2 border-border/50">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2"><Calculator className="h-4 w-4" /> What-If Scenarios</CardTitle>
            <CardDescription>Select actions to see their estimated impact on your score.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {simulatorScenarios.map((scenario, i) => (
              <div
                key={i}
                className={`p-4 rounded-lg border cursor-pointer transition-colors ${selected.has(i) ? "border-primary bg-primary/5" : "border-border hover:border-primary/30"}`}
                onClick={() => toggle(i)}
              >
                <div className="flex items-start gap-3">
                  <Checkbox checked={selected.has(i)} className="mt-0.5" />
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{scenario.action}</span>
                      <span className={`text-sm font-bold font-mono ${scenario.impact > 0 ? "text-emerald-600" : "text-red-500"}`}>
                        {scenario.impact > 0 ? "+" : ""}{scenario.impact} pts
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{scenario.description}</p>
                    <span className="text-[11px] text-muted-foreground">Timeframe: {scenario.timeframe}</span>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
