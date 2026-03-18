import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Beaker, Crown, Archive, Settings, Play, Loader2 } from "lucide-react";
import { mockModels } from "@/lib/mock-data-extended";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchModelCompare, fetchRoutingConfig, updateRoutingConfig, promoteModel } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";

const statusConfig = {
  champion: { icon: Crown, color: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20", label: "Champion" },
  challenger: { icon: Beaker, color: "bg-amber-500/10 text-amber-600 border-amber-500/20", label: "Challenger" },
  retired: { icon: Archive, color: "bg-muted text-muted-foreground border-border", label: "Retired" },
};

interface ModelDisplay {
  id: string;
  name: string;
  version: string;
  status: "champion" | "challenger" | "retired";
  accuracy: number;
  giniCoefficient: number;
  ksStatistic: number;
  lastTrained: string;
  features: number;
  description: string;
}

export default function ModelConfig() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: compareData, isLoading: compareLoading, isError: compareError } = useQuery({
    queryKey: ["model-compare"],
    queryFn: fetchModelCompare,
  });

  const { data: routingData } = useQuery({
    queryKey: ["routing-config"],
    queryFn: fetchRoutingConfig,
  });

  const promoteMutation = useMutation({
    mutationFn: promoteModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["model-compare"] });
      toast({ title: "Model promoted" });
    },
  });

  // Transform API data to display format, or fall back to mock
  let models: ModelDisplay[];
  if (compareError || !compareData) {
    models = mockModels;
  } else {
    models = [];
    const c = compareData.champion;
    if (c) {
      models.push({
        id: String(c.id || "MDL-C"),
        name: String(c.name || c.model_name || "Champion Model"),
        version: String(c.version || "—"),
        status: "champion",
        accuracy: Number(c.accuracy || c.auc || 0) * (Number(c.accuracy || 0) > 1 ? 1 : 100),
        giniCoefficient: Number(c.gini || c.giniCoefficient || 0),
        ksStatistic: Number(c.ks || c.ksStatistic || 0),
        lastTrained: String(c.lastTrained || c.last_trained || "—"),
        features: Number(c.features || c.feature_count || 0),
        description: String(c.description || "Current production model"),
      });
    }
    const ch = compareData.challenger;
    if (ch) {
      models.push({
        id: String(ch.id || "MDL-CH"),
        name: String(ch.name || ch.model_name || "Challenger Model"),
        version: String(ch.version || "—"),
        status: "challenger",
        accuracy: Number(ch.accuracy || ch.auc || 0) * (Number(ch.accuracy || 0) > 1 ? 1 : 100),
        giniCoefficient: Number(ch.gini || ch.giniCoefficient || 0),
        ksStatistic: Number(ch.ks || ch.ksStatistic || 0),
        lastTrained: String(ch.lastTrained || ch.last_trained || "—"),
        features: Number(ch.features || ch.feature_count || 0),
        description: String(ch.description || "Challenger model under evaluation"),
      });
    }
    // If API returned empty, use mock
    if (models.length === 0) models = mockModels;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Model Configuration</h1>
          <p className="text-sm text-muted-foreground">
            Manage scoring models — champion/challenger framework.
            {routingData && ` Challenger traffic: ${((routingData.challenger_traffic_pct || 0) * 100).toFixed(0)}%`}
          </p>
        </div>
        <Button onClick={() => promoteMutation.mutate()} disabled={promoteMutation.isPending}>
          {promoteMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
          Promote Challenger
        </Button>
      </div>

      <div className="grid gap-6">
        {compareLoading ? (
          Array.from({ length: 2 }).map((_, i) => (
            <Card key={i} className="border-border/50">
              <CardContent className="p-6 space-y-4">
                <Skeleton className="h-6 w-48" />
                <div className="grid grid-cols-5 gap-6">
                  {Array.from({ length: 5 }).map((_, j) => (
                    <Skeleton key={j} className="h-16 w-full" />
                  ))}
                </div>
              </CardContent>
            </Card>
          ))
        ) : (
          models.map((model) => {
            const cfg = statusConfig[model.status];
            return (
              <Card key={model.id} className="border-border/50">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-3">
                        <CardTitle className="text-lg">{model.name}</CardTitle>
                        <Badge variant="outline" className={cfg.color}>
                          <cfg.icon className="h-3 w-3 mr-1" />{cfg.label}
                        </Badge>
                      </div>
                      <CardDescription className="mt-1">{model.description}</CardDescription>
                    </div>
                    <Button variant="outline" size="sm"><Settings className="h-3.5 w-3.5 mr-1" /> Configure</Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-6">
                    <div>
                      <div className="text-xs text-muted-foreground mb-1">Accuracy</div>
                      <div className="text-xl font-bold">{model.accuracy.toFixed(1)}%</div>
                      <Progress value={model.accuracy} className="mt-2 h-1.5" />
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground mb-1">Gini Coefficient</div>
                      <div className="text-xl font-bold">{model.giniCoefficient.toFixed(2)}</div>
                      <Progress value={model.giniCoefficient * 100} className="mt-2 h-1.5" />
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground mb-1">KS Statistic</div>
                      <div className="text-xl font-bold">{model.ksStatistic.toFixed(2)}</div>
                      <Progress value={model.ksStatistic * 100} className="mt-2 h-1.5" />
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground mb-1">Features</div>
                      <div className="text-xl font-bold">{model.features}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground mb-1">Last Trained</div>
                      <div className="text-xl font-bold">{model.lastTrained}</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
}
