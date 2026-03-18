import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { educationTopics } from "@/lib/mock-data-extended";
import { GraduationCap, TrendingUp, FileText, AlertTriangle, Shield, Search, Wallet, HelpCircle, ArrowRight } from "lucide-react";

const iconMap: Record<string, typeof GraduationCap> = {
  GraduationCap, TrendingUp, FileText, AlertTriangle, Shield, Search, Wallet, HelpCircle,
};

const categoryColors: Record<string, string> = {
  Basics: "bg-blue-500/10 text-blue-600 border-blue-500/20",
  Tips: "bg-emerald-500/10 text-emerald-600 border-emerald-500/20",
  Actions: "bg-amber-500/10 text-amber-600 border-amber-500/20",
  Security: "bg-red-500/10 text-red-500 border-red-500/20",
};

export default function CreditEducation() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Credit Education</h1>
        <p className="text-sm text-muted-foreground">Learn how to manage and improve your credit health.</p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {educationTopics.map((topic) => {
          const Icon = iconMap[topic.icon] || GraduationCap;
          return (
            <Card key={topic.id} className="border-border/50 hover:shadow-md transition-shadow cursor-pointer group">
              <CardContent className="p-5">
                <div className="flex items-start gap-4">
                  <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                    <Icon className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="outline" className={`text-[10px] ${categoryColors[topic.category] || ""}`}>{topic.category}</Badge>
                      <span className="text-[11px] text-muted-foreground">{topic.readTime}</span>
                    </div>
                    <h3 className="font-medium text-sm mb-1">{topic.title}</h3>
                    <p className="text-xs text-muted-foreground">{topic.description}</p>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity mt-1" />
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
