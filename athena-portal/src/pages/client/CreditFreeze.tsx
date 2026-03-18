import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Lock, Unlock, ShieldAlert, Info } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export default function CreditFreeze() {
  const [frozen, setFrozen] = useState(false);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Credit Freeze</h1>
        <p className="text-sm text-muted-foreground">Control access to your credit file.</p>
      </div>

      <Alert className="border-primary/20 bg-primary/5">
        <Info className="h-4 w-4" />
        <AlertTitle>What is a Credit Freeze?</AlertTitle>
        <AlertDescription className="text-sm">
          A credit freeze restricts access to your credit report, making it harder for identity thieves to open new accounts in your name. You can lift the freeze temporarily when you need to apply for credit.
        </AlertDescription>
      </Alert>

      <Card className="border-border/50">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                {frozen ? <Lock className="h-5 w-5 text-red-500" /> : <Unlock className="h-5 w-5 text-emerald-600" />}
                Credit File Status
              </CardTitle>
              <CardDescription className="mt-1">
                {frozen ? "Your credit file is currently frozen." : "Your credit file is currently accessible."}
              </CardDescription>
            </div>
            <Badge variant="outline" className={frozen ? "bg-red-500/10 text-red-500 border-red-500/20" : "bg-emerald-500/10 text-emerald-600 border-emerald-500/20"}>
              {frozen ? "Frozen" : "Unfrozen"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between p-4 rounded-lg border">
            <div>
              <div className="font-medium text-sm">{frozen ? "Unfreeze Credit File" : "Freeze Credit File"}</div>
              <div className="text-xs text-muted-foreground mt-0.5">
                {frozen ? "Allow lenders to access your credit report" : "Prevent new credit inquiries on your file"}
              </div>
            </div>
            <Switch checked={frozen} onCheckedChange={setFrozen} />
          </div>

          {frozen && (
            <div className="mt-4 p-4 rounded-lg bg-amber-500/5 border border-amber-500/20">
              <div className="flex items-start gap-3">
                <ShieldAlert className="h-5 w-5 text-amber-500 mt-0.5" />
                <div>
                  <div className="text-sm font-medium">Freeze Active Since: {new Date().toLocaleDateString()}</div>
                  <p className="text-xs text-muted-foreground mt-1">
                    While your credit file is frozen, no new credit applications can be processed. Existing accounts are not affected.
                  </p>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="text-base">Freeze History</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[
              { action: "Freeze activated", date: "2025-01-15", reason: "Suspected unauthorized inquiry" },
              { action: "Freeze lifted", date: "2025-01-28", reason: "Mortgage application with KCB Bank" },
              { action: "Freeze activated", date: "2024-11-10", reason: "Precautionary measure" },
              { action: "Freeze lifted", date: "2024-12-01", reason: "Personal loan application" },
            ].map((h, i) => (
              <div key={i} className="flex items-center justify-between p-3 rounded-lg border text-sm">
                <div className="flex items-center gap-3">
                  {h.action.includes("activated") ? <Lock className="h-4 w-4 text-red-500" /> : <Unlock className="h-4 w-4 text-emerald-600" />}
                  <div>
                    <div className="font-medium">{h.action}</div>
                    <div className="text-xs text-muted-foreground">{h.reason}</div>
                  </div>
                </div>
                <span className="text-xs text-muted-foreground">{h.date}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
