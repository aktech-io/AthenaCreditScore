import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { mockSystemConfigs } from "@/lib/mock-data-extended";
import { Settings, Save, RotateCcw, Cpu, ShieldCheck, Database, Bell } from "lucide-react";

const categoryIcons: Record<string, JSX.Element> = {
  "Scoring Engine": <Cpu className="h-5 w-5 text-primary" />,
  "Risk Thresholds": <ShieldCheck className="h-5 w-5 text-amber-600" />,
  "Data & Privacy": <Database className="h-5 w-5 text-emerald-600" />,
  "Notifications": <Bell className="h-5 w-5 text-blue-600" />,
};

export default function SystemConfiguration() {
  const [configs, setConfigs] = useState(mockSystemConfigs);
  const [hasChanges, setHasChanges] = useState(false);

  const updateSetting = (catIndex: number, settingIndex: number, newValue: string | number | boolean) => {
    const updated = [...configs];
    updated[catIndex].settings[settingIndex].value = newValue;
    setConfigs(updated);
    setHasChanges(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">System Configuration</h1>
          <p className="text-sm text-muted-foreground">Configure scoring engine, risk thresholds, data policies, and notification rules.</p>
        </div>
        <div className="flex items-center gap-2">
          {hasChanges && <Badge variant="outline" className="bg-amber-500/10 text-amber-600 border-amber-500/20">Unsaved Changes</Badge>}
          <Button variant="outline" disabled={!hasChanges} onClick={() => { setConfigs(mockSystemConfigs); setHasChanges(false); }}><RotateCcw className="h-4 w-4 mr-2" /> Reset</Button>
          <Button disabled={!hasChanges} onClick={() => setHasChanges(false)}><Save className="h-4 w-4 mr-2" /> Save Changes</Button>
        </div>
      </div>

      <div className="grid gap-6">
        {configs.map((cat, catIndex) => (
          <Card key={cat.category} className="border-border/50">
            <CardHeader className="pb-4">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-lg bg-muted flex items-center justify-center">
                  {categoryIcons[cat.category] || <Settings className="h-5 w-5" />}
                </div>
                <div>
                  <CardTitle className="text-base">{cat.category}</CardTitle>
                  <CardDescription className="text-xs">Configure {cat.category.toLowerCase()} parameters</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-5">
                {cat.settings.map((setting, settingIndex) => (
                  <div key={setting.key}>
                    <div className="flex items-center justify-between gap-8">
                      <div className="flex-1 min-w-0">
                        <Label className="text-sm font-medium">{setting.label}</Label>
                        <p className="text-xs text-muted-foreground mt-0.5">{setting.description}</p>
                      </div>
                      <div className="w-48 shrink-0">
                        {setting.type === "toggle" ? (
                          <Switch
                            checked={setting.value as boolean}
                            onCheckedChange={(v) => updateSetting(catIndex, settingIndex, v)}
                          />
                        ) : setting.type === "select" ? (
                          <Select value={setting.value as string} onValueChange={(v) => updateSetting(catIndex, settingIndex, v)}>
                            <SelectTrigger className="h-9"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              {setting.options?.map((o) => (<SelectItem key={o} value={o} className="capitalize">{o}</SelectItem>))}
                            </SelectContent>
                          </Select>
                        ) : (
                          <Input
                            type={setting.type}
                            value={setting.value as string | number}
                            onChange={(e) => updateSetting(catIndex, settingIndex, setting.type === "number" ? Number(e.target.value) : e.target.value)}
                            className="h-9"
                          />
                        )}
                      </div>
                    </div>
                    {settingIndex < cat.settings.length - 1 && <Separator className="mt-5" />}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
