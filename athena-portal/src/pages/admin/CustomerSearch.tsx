import { useState } from "react";
import { Search, Eye, RefreshCw, Download, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { getScoreColor, getStatusColor, formatCurrency } from "@/lib/mock-data";
import { ScoreGauge } from "@/components/ScoreGauge";
import { useQuery } from "@tanstack/react-query";
import { fetchCustomers, searchCustomers, fetchCreditScore, triggerScoring, type CustomerRecord } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";

function customerName(c: CustomerRecord): string {
  if (c.name) return c.name;
  return [c.first_name || c.firstName || "", c.last_name || c.lastName || ""].filter(Boolean).join(" ") || `Customer ${c.id}`;
}

function customerNationalId(c: CustomerRecord): string {
  return c.national_id || c.nationalId || "—";
}

function customerPhone(c: CustomerRecord): string {
  return c.phone || c.mobile_number || "—";
}

function customerScore(c: CustomerRecord): number {
  return c.score ?? c.credit_score ?? 0;
}

function customerScoreBand(c: CustomerRecord): string {
  return c.score_band || c.scoreBand || "—";
}

export default function CustomerSearch() {
  const [search, setSearch] = useState("");
  const [triggeringId, setTriggeringId] = useState<number | null>(null);
  const { toast } = useToast();

  const { data: listData, isLoading: listLoading } = useQuery({
    queryKey: ["customers-list"],
    queryFn: () => fetchCustomers(0, 50),
  });

  const { data: searchData, isLoading: searchLoading } = useQuery({
    queryKey: ["customers-search", search],
    queryFn: () => searchCustomers(search),
    enabled: search.length >= 2,
  });

  const isLoading = search.length >= 2 ? searchLoading : listLoading;

  // Use search results when query >= 2 chars, otherwise paginated list
  const customers: CustomerRecord[] = search.length >= 2
    ? (searchData || [])
    : (listData?.content || []);

  const handleRescore = async (id: number) => {
    setTriggeringId(id);
    try {
      await triggerScoring(id);
      toast({ title: "Scoring triggered", description: `Re-scoring started for customer ${id}` });
    } catch {
      toast({ variant: "destructive", title: "Failed", description: "Could not trigger scoring" });
    } finally {
      setTriggeringId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Customer Search</h1>
        <p className="text-sm text-muted-foreground">Search and view client credit profiles.</p>
      </div>

      <Card className="border-border/50">
        <CardHeader className="pb-4">
          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
            <CardTitle className="text-base">Client Database</CardTitle>
            <div className="relative w-full sm:w-80">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Search by name or phone..." className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Client</TableHead>
                <TableHead>National ID</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Grade</TableHead>
                <TableHead>Phone</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 7 }).map((_, j) => (
                      <TableCell key={j}><Skeleton className="h-4 w-20" /></TableCell>
                    ))}
                  </TableRow>
                ))
              ) : customers.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                    {search.length >= 2 ? "No results found." : "No customers loaded."}
                  </TableCell>
                </TableRow>
              ) : (
                customers.map((client) => (
                  <TableRow key={client.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium text-sm">{customerName(client)}</div>
                        <div className="text-xs text-muted-foreground">{client.email || "—"}</div>
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-sm">{customerNationalId(client)}</TableCell>
                    <TableCell className={`font-bold font-mono ${getScoreColor(customerScore(client))}`}>
                      {customerScore(client) || "—"}
                    </TableCell>
                    <TableCell><span className="text-sm">{customerScoreBand(client)}</span></TableCell>
                    <TableCell className="text-sm">{customerPhone(client)}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={getStatusColor(client.status || "active")}>{client.status || "active"}</Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-1 justify-end">
                        <Dialog>
                          <DialogTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-8 w-8"><Eye className="h-3.5 w-3.5" /></Button>
                          </DialogTrigger>
                          <DialogContent className="max-w-2xl">
                            <DialogHeader><DialogTitle>Credit Profile — {customerName(client)}</DialogTitle></DialogHeader>
                            <CustomerProfileDialog customerId={client.id} client={client} />
                          </DialogContent>
                        </Dialog>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          disabled={triggeringId === client.id}
                          onClick={() => handleRescore(client.id)}
                        >
                          {triggeringId === client.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8"><Download className="h-3.5 w-3.5" /></Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function CustomerProfileDialog({ customerId, client }: { customerId: number; client: CustomerRecord }) {
  const { data: scoreData, isLoading } = useQuery({
    queryKey: ["credit-score", customerId],
    queryFn: () => fetchCreditScore(customerId),
  });

  const score = scoreData?.final_score ?? customerScore(client);

  return (
    <div className="grid grid-cols-2 gap-6 py-4">
      <div className="flex justify-center">
        {isLoading ? <Skeleton className="h-40 w-40 rounded-full" /> : <ScoreGauge score={score} size="md" />}
      </div>
      <div className="space-y-3 text-sm">
        <div className="flex justify-between"><span className="text-muted-foreground">National ID</span><span className="font-mono">{customerNationalId(client)}</span></div>
        <div className="flex justify-between"><span className="text-muted-foreground">Phone</span><span>{customerPhone(client)}</span></div>
        <div className="flex justify-between"><span className="text-muted-foreground">Email</span><span>{client.email || "—"}</span></div>
        <div className="flex justify-between"><span className="text-muted-foreground">Score Band</span><span>{scoreData?.score_band || customerScoreBand(client)}</span></div>
        <div className="flex justify-between"><span className="text-muted-foreground">PD</span><span className="font-mono">{scoreData?.pd_probability ? (scoreData.pd_probability * 100).toFixed(2) + "%" : "—"}</span></div>
        <div className="flex justify-between"><span className="text-muted-foreground">Base Score</span><span className="font-mono">{scoreData?.base_score ?? "—"}</span></div>
        <div className="flex justify-between"><span className="text-muted-foreground">CRB Contribution</span><span className="font-mono">{scoreData?.crb_contribution ?? "—"}</span></div>
        <div className="flex justify-between"><span className="text-muted-foreground">LLM Adjustment</span><span className="font-mono">{scoreData?.llm_adjustment ?? "—"}</span></div>
      </div>
    </div>
  );
}
